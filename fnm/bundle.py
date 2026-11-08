"""Prepare a full installation in scratch storage before changing Forge."""
import copy
import io
import json
from pathlib import Path
import shutil
import stat
import zipfile

from .engine import Package, Conflict, canonical, digest, json_bytes, path_in
from .settings import load_settings, settings_path
from .updater import fetch


def source_files(repo, downloader=fetch):
    url = repo["url"]
    if not url.startswith("https://github.com/") or len(url.removeprefix("https://github.com/").split("/")) != 2:
        raise Conflict("Invalid source repository URL")
    data = downloader(f"https://codeload.github.com/{url.removeprefix('https://github.com/')}/zip/{repo['commit']}")
    if digest(data) != repo["archive_sha256"]:
        raise Conflict("Extension download checksum mismatch: " + url)
    result = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if not entries or len(entries) > 10000 or sum(e.file_size for e in entries) > 256 * 1024 * 1024:
            raise Conflict("Oversized extension archive")
        top = entries[0].filename.split("/")[0] + "/"
        seen = set()
        for entry in entries:
            if not entry.filename.startswith(top) or stat.S_ISLNK(entry.external_attr >> 16):
                raise Conflict("Unsafe extension archive")
            name = entry.filename[len(top):].rstrip("/")
            if not name:
                continue
            path_in(Path("."), name)
            if name.casefold() in seen:
                raise Conflict("Duplicate extension archive path")
            seen.add(name.casefold())
            if not entry.is_dir():
                result[name] = archive.read(entry)
    return result


def prepare(engine, selected, destination, downloader=fetch):
    """Missing extensions become owned files; existing repositories keep their data."""
    package = engine.package
    manifest = copy.deepcopy(package.manifest)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package.root / "payload", destination / "payload", dirs_exist_ok=True)
    state = engine.state()
    conflicts = set()
    for component in manifest["components"]:
        if component["id"] not in selected:
            continue
        conflicts.update(component.pop("conflicts", []))
        remaining = []
        for repo in component.get("repositories", []):
            folder = path_in(engine.root, repo["path"])
            if (folder / ".git").exists():
                remaining.append(repo)
                continue
            print("拡張を準備中: " + repo["path"])
            files = source_files(repo, downloader)
            prefix = repo["path"] + "/"
            modifications = {o["path"][len(prefix):]: o for o in component["files"] if o["path"].startswith(prefix)}
            generated = []
            for name in sorted(set(files) | set(modifications)):
                original = files.get(name)
                data = package.transform(modifications[name], original) if name in modifications else original
                relative = prefix + name
                prior = state["files"].get(relative)
                existing = engine.blob(prior["before"]) if prior else engine.read(relative)
                # Do not replace unrelated or locally edited files without a known baseline.
                if existing is not None and canonical(existing) not in (canonical(data), canonical(original) if original is not None else None):
                    raise Conflict("既存ファイルに独自の変更があります。保持して停止: " + relative)
                key = digest(data)
                payload = "payload/full/" + key
                target = destination / payload
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                operation = {"path": relative, "kind": "add" if existing is None else "replace", "payload": payload, "after": digest(canonical(data))}
                if existing is not None:
                    operation["before"] = digest(canonical(existing))
                generated.append(operation)
            component["files"] = [o for o in component["files"] if not o["path"].startswith(prefix)] + generated
        component["repositories"] = remaining
    if conflicts:
        settings = settings_path(engine.root, engine.settings_file).resolve()
        if settings.exists():
            load_settings(engine.root, engine.settings_file)  # validate before changing it
        elif engine.settings_file or settings != engine.root / "config.json":
            raise Conflict("設定ファイルがありません: " + str(settings))
        try:
            relative = settings.relative_to(engine.root).as_posix()
        except ValueError:
            # Keep normal conflict validation for external settings, including
            # its second check at apply time. Never silently edit outside Forge.
            for component in manifest["components"]:
                if component["id"] in selected:
                    component["conflicts"] = package.components[component["id"]].get("conflicts", [])
            relative = None
        names = sorted(n for n in conflicts if any((engine.root / d / n).is_dir() for d in ("extensions", "extensions-builtin")))
        # Keep ownership of earlier disable entries across updates even if folders moved.
        entry = state["files"].get(relative, {})
        names = sorted(set(names) | set(entry.get("config_added", [])))
        if names and relative is not None:
            component = next(c for c in manifest["components"] if c["id"] in selected)
            component["files"].append({"path": relative, "kind": "disable_extensions", "names": names})
            print("併用を避けるため無効化します（復元可能）: " + ", ".join(names))
            print("使用する設定: " + str(settings))
    (destination / "manifest.json").write_bytes(json_bytes(manifest))
    sums = {p.relative_to(destination).as_posix(): digest(p.read_bytes()) for p in destination.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"}
    (destination / "SHA256SUMS.json").write_bytes(json_bytes(sums))
    return Package(destination)
