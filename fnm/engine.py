"""Standard-library-only, transactional file patch manager (MIT)."""
from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile

STATE_DIR = ".forgeneomodification"


class Conflict(RuntimeError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return data.replace(b"\r\n", b"\n")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def path_in(root, relative, *, internal=False):
    """Reject traversal, Windows device names, links/junctions and hardlinked files."""
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise Conflict(f"Invalid path: {relative!r}")
    parts = PurePosixPath(relative).parts
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}
    if not parts or PurePosixPath(relative).is_absolute() or any(
        p.lower() in (".", "..", ".git") or p.endswith((" ", ".")) or p.split(".")[0].upper() in reserved
        or (p.lower() == STATE_DIR and not internal) for p in parts
    ) or relative != "/".join(parts):
        raise Conflict(f"Unsafe path: {relative!r}")
    current = root
    for part in parts:
        current = current / part
        if current.exists() or current.is_symlink():
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise Conflict(f"Link/reparse point is not a patch target: {relative}")
            if current.is_file() and info.st_nlink > 1:
                raise Conflict(f"Hardlinked file is not a patch target: {relative}")
    return current


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".fnm-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def stopped_guard(root):
    """Conservatively reject running Forge Python processes. Never stop processes."""
    if os.name != "nt":
        raise Conflict("Applying changes is supported on Windows only. Tests can inject a process probe.")
    command = "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|uvicorn).*' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise Conflict("Could not check running Python processes. Close Forge and retry.")
    rows = json.loads(result.stdout or "null") or []
    if isinstance(rows, dict):
        rows = [rows]
    for row in rows:
        if row["ProcessId"] == os.getpid():
            continue
        line = row.get("CommandLine")
        if not line:
            raise Conflict("A Python process could not be inspected. Close Forge/Python tasks and retry.")
        if any(name in line.lower() for name in ("launch.py", "webui.py", "uvicorn")):
            raise Conflict(f"Forge/server may be running (PID {row['ProcessId']}). Close it before changing files.")


class Package:
    def __init__(self, folder):
        self.root = Path(folder).resolve()
        sums = read_json(self.root / "SHA256SUMS.json")
        for name, expected in sums.items():
            path = path_in(self.root, name)
            if not path.is_file() or digest(path.read_bytes()) != expected:
                raise Conflict(f"Package checksum mismatch: {name}")
        if "manifest.json" not in sums:
            raise Conflict("Manifest is missing from checksums")
        self.manifest = read_json(self.root / "manifest.json")
        if self.manifest.get("schema") != 1:
            raise Conflict("Unsupported package schema")
        self.components = {c["id"]: c for c in self.manifest["components"]}
        if len(self.components) != len(self.manifest["components"]):
            raise Conflict("Duplicate component ID")
        for component in self.components.values():
            for operation in component["files"]:
                path_in(self.root, operation["path"])
                payload = operation.get("payload")
                if payload and payload not in sums:
                    raise Conflict(f"Unchecked payload: {payload}")

    def transform(self, operation, before):
        if operation["kind"] in ("add", "replace"):
            if operation["kind"] == "add" and before is not None:
                raise Conflict(f"Existing unmanaged file: {operation['path']}")
            if operation["kind"] == "replace" and (before is None or digest(canonical(before)) != operation["before"]):
                raise Conflict(f"Unsupported/local edits (not overwritten): {operation['path']}")
            content = path_in(self.root, operation["payload"]).read_bytes()
            if operation.get("compressed"):
                import io
                with gzip.GzipFile(fileobj=io.BytesIO(content)) as stream:
                    content = stream.read(64 * 1024 * 1024 + 1)
                if len(content) > 64 * 1024 * 1024:
                    raise Conflict("Expanded payload exceeds size limit")
        elif operation["kind"] == "patch":
            if before is None or digest(canonical(before)) != operation["before"]:
                raise Conflict(f"Unsupported/local edits (not overwritten): {operation['path']}")
            text = canonical(before).decode("utf-8")
            for edit in reversed(operation["edits"]):
                start, end = edit["start"], edit["end"]
                if text[start:end] != edit["old"]:
                    raise Conflict(f"Patch context mismatch: {operation['path']}")
                text = text[:start] + edit["new"] + text[end:]
            content = text.encode("utf-8")
            if b"\r\n" in before:
                content = content.replace(b"\n", b"\r\n")
        else:
            raise Conflict("Unknown operation kind")
        if digest(canonical(content)) != operation["after"]:
            raise Conflict(f"Patch result checksum mismatch: {operation['path']}")
        if operation["path"].endswith(".py"):
            compile(content, operation["path"], "exec")
        return content


class Engine:
    def __init__(self, root, package=None, process_probe=stopped_guard):
        given = Path(root).absolute()
        if given.is_symlink() or (given.exists() and getattr(given.lstat(), "st_file_attributes", 0) & 0x400):
            raise Conflict("Select the real Forge directory, not a link")
        self.root = given.resolve()
        if not (self.root / "webui.py").is_file() or not (self.root / "modules").is_dir():
            raise Conflict("Select the Forge folder containing webui.py and modules")
        self.package = package
        self.probe = process_probe
        self.store = path_in(self.root, STATE_DIR, internal=True)

    def internal(self, name):
        return path_in(self.root, f"{STATE_DIR}/{name}", internal=True)

    def read(self, relative):
        path = path_in(self.root, relative)
        if path.exists() and not path.is_file():
            raise Conflict(f"Target is not a regular file: {relative}")
        return path.read_bytes() if path.exists() else None

    def state(self):
        path = self.internal("state.json")
        state = read_json(path) if path.exists() else {"schema": 1, "components": [], "files": {}, "version": None}
        if state.get("schema") != 1:
            raise Conflict("Unsupported state schema")
        for relative in state["files"]:
            path_in(self.root, relative)
        return state

    def blob(self, key):
        if key is None:
            return None
        if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise Conflict("Invalid backup ID")
        path = self.internal(f"blobs/{key}")
        if not path.is_file():
            raise Conflict(f"Missing backup: {key}")
        content = path.read_bytes()
        if digest(content) != key:
            raise Conflict(f"Backup checksum mismatch: {key}")
        return content

    def save_blob(self, content):
        if content is None:
            return None
        key = digest(content)
        path = self.internal(f"blobs/{key}")
        if path.exists():
            self.blob(key)
        else:
            atomic_write(path, content)
        return key

    @contextlib.contextmanager
    def locked(self):
        self.store.mkdir(exist_ok=True)
        lock = self.internal("lock")
        with lock.open("a+b") as stream:
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise Conflict("Another operation is already running") from exc
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def verify_repo(self, repo):
        folder = self.root if repo["path"] == "." else path_in(self.root, repo["path"])
        # A child directory must not accidentally inherit the parent's .git.
        if not (folder / ".git").exists():
            raise Conflict(f"Required repository not installed: {repo['path']} ({repo['url']})")
        try:
            result = subprocess.run(["git", "-C", str(folder), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Conflict("Git is required for version checks") from exc
        if result.returncode or result.stdout.strip() != repo["commit"]:
            raise Conflict(f"Unsupported version: {repo['path']}; required {repo['commit']}")

    def plan(self, selected):
        """Read-only planning; old baselines are the input to a package update."""
        if self.internal("journal.json").exists():
            raise Conflict("Interrupted operation found. Run Recover first.")
        prior = self.state()
        original, current = {}, {}
        for relative, entry in prior["files"].items():
            value = self.read(relative)
            if value is None or digest(value) != entry["after"]:
                raise Conflict(f"Edited/missing managed file, retained: {relative}")
            current[relative] = value
            original[relative] = self.blob(entry["before"])
        desired = {}
        component_ids = list(dict.fromkeys(selected))
        if component_ids and self.package is None:
            raise Conflict("No package supplied")
        if component_ids:
            self.verify_repo(self.package.manifest["forge"])
        config = read_json(self.root / "config.json") if (self.root / "config.json").is_file() else {}
        disabled = set(config.get("disabled_extensions", []))
        disable_all = config.get("disable_all_extensions", "none") != "none"
        for component_id in component_ids:
            component = self.package.components.get(component_id)
            if not component:
                raise Conflict(f"Unknown component: {component_id}")
            for needed in component.get("requires", []):
                if needed not in component_ids:
                    raise Conflict(f"{component_id} requires selected component: {needed}")
            for conflict in component.get("conflicts", []):
                if not disable_all and conflict not in disabled and (self.root / "extensions" / conflict).is_dir():
                    raise Conflict(f"Disable conflicting extension first: {conflict}")
            for marker in component.get("forbid_markers", []):
                source = self.read(marker["path"])
                if source and marker["text"].encode() in source:
                    raise Conflict(f"Existing local implementation detected: {marker['path']}")
            for repo in component.get("repositories", []):
                self.verify_repo(repo)
            for operation in component["files"]:
                relative = operation["path"]
                if relative in desired:
                    raise Conflict(f"Overlapping components: {relative}")
                if relative not in original:
                    current[relative] = self.read(relative)
                    original[relative] = current[relative]
                desired[relative] = self.package.transform(operation, original[relative])
        changes = {name: (current[name], desired.get(name, original[name])) for name in current
                   if current[name] != desired.get(name, original[name])}
        return {"prior": prior, "selected": component_ids, "original": original, "desired": desired, "changes": changes}

    def write_target(self, relative, content):
        path = path_in(self.root, relative)
        if content is None:
            if path.exists():
                path.unlink()
        else:
            atomic_write(path, content)

    def _recover(self):
        path = self.internal("journal.json")
        if not path.exists():
            return False
        journal = read_json(path)
        # Validate every recovery input before modifying anything.
        data = []
        for change in journal["changes"]:
            before, after = self.blob(change["before"]), self.blob(change["after"])
            current = self.read(change["path"])
            if current not in (before, after):
                raise Conflict(f"Recovery conflict; edited file retained: {change['path']}")
            data.append((change["path"], before))
        for relative, before in reversed(data):
            self.write_target(relative, before)
        atomic_write(self.internal("state.json"), json_bytes(journal["prior"]))
        path.unlink()
        return True

    def recover(self):
        self.probe(self.root)
        with self.locked():
            return self._recover()

    def apply(self, selected):
        self.probe(self.root)
        with self.locked():
            plan = self.plan(selected)
            state = {"schema": 1, "version": self.package.manifest["version"] if selected else None,
                     "components": plan["selected"], "files": {}}
            for name, after in plan["desired"].items():
                state["files"][name] = {"before": self.save_blob(plan["original"][name]), "after": digest(after)}
            journal = {"schema": 1, "prior": plan["prior"], "changes": []}
            for name, (before, after) in plan["changes"].items():
                journal["changes"].append({"path": name, "before": self.save_blob(before), "after": self.save_blob(after)})
            # Recheck after backup/staging, in case an external process edited files.
            for name, (before, _) in plan["changes"].items():
                if self.read(name) != before:
                    raise Conflict(f"File changed during planning: {name}")
            atomic_write(self.internal("journal.json"), json_bytes(journal))
            try:
                for name, (_, after) in plan["changes"].items():
                    self.write_target(name, after)
                atomic_write(self.internal("state.json"), json_bytes(state))
                self.internal("journal.json").unlink()
            except Exception:
                self._recover()
                raise
            return {"changed_files": len(plan["changes"]), "components": state["components"], "version": state["version"]}
