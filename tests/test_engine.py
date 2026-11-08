import copy
import gzip
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from fnm.engine import Conflict, Engine, Package, canonical, digest, json_bytes, path_in
from fnm.updater import unpack


def checksums(folder):
    values = {f.relative_to(folder).as_posix(): digest(f.read_bytes()) for f in folder.rglob("*")
              if f.is_file() and f.name != "SHA256SUMS.json"}
    (folder / "SHA256SUMS.json").write_bytes(json_bytes(values))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "Forge 日本語 space"
        self.root.mkdir()
        (self.root / "modules").mkdir()
        (self.root / "webui.py").write_text("# fixture\n")
        (self.root / "modules/test.py").write_bytes(b"value = 1\r\n")
        (self.root / "config.json").write_text('{"private_key":"retain-me"}')
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Tests", "-c", "user.email=tests@example.invalid", "commit", "-qm", "fixture"], check=True)
        head = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()
        self.folder = self.base / "package"
        self.folder.mkdir()
        (self.folder / "payload").mkdir()
        (self.folder / "payload/new.py").write_bytes(b"new = True\n")
        self.manifest = {"schema":1,"version":"1","forge":{"path":".","commit":head,"url":"https://example.invalid/forge"},"components":[
            {"id":"test","default":True,"files":[
                {"path":"modules/test.py","kind":"patch","before":digest(b"value = 1\n"),"after":digest(b"value = 2\n"),"edits":[{"start":8,"end":9,"old":"1","new":"2"}]},
                {"path":"extensions/demo/new.py","kind":"add","payload":"payload/new.py","after":digest(b"new = True\n")}
            ]}]}
        self.package = self.make_package()
        self.engine = Engine(self.root, self.package, process_probe=lambda root: None)

    def make_package(self):
        (self.folder / "manifest.json").write_bytes(json_bytes(self.manifest))
        checksums(self.folder)
        return Package(self.folder)

    def test_apply_idempotent_uninstall_restores_raw_bytes(self):
        config = (self.root / "config.json").read_bytes()
        self.assertEqual(self.engine.apply(["test"])["changed_files"], 2)
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 2\r\n")
        self.assertEqual(self.engine.apply(["test"])["changed_files"], 0)
        self.engine.apply([])
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 1\r\n")
        self.assertFalse((self.root / "extensions/demo/new.py").exists())
        self.assertEqual((self.root / "config.json").read_bytes(), config)

    def test_plan_does_not_create_state(self):
        self.assertEqual(len(self.engine.plan(["test"])["changes"]), 2)
        self.assertFalse(self.engine.store.exists())

    def test_unknown_head_refused(self):
        self.manifest["forge"]["commit"] = "0" * 40
        self.engine.package = self.make_package()
        with self.assertRaisesRegex(Conflict, "Unsupported version"):
            self.engine.plan(["test"])

    def test_local_changes_refused_before_writing(self):
        (self.root / "modules/test.py").write_text("user edit\n")
        with self.assertRaises(Conflict):
            self.engine.apply(["test"])
        self.assertFalse((self.root / "extensions/demo/new.py").exists())

    def test_existing_unmanaged_addition_not_adopted(self):
        target = self.root / "extensions/demo/new.py"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"new = True\n")
        with self.assertRaisesRegex(Conflict, "Existing unmanaged"):
            self.engine.plan(["test"])

    def test_user_edit_blocks_uninstall_and_update(self):
        self.engine.apply(["test"])
        target = self.root / "extensions/demo/new.py"
        target.write_text("user edit")
        for selection in ([], ["test"]):
            with self.assertRaisesRegex(Conflict, "retained"):
                self.engine.apply(selection)
        self.assertEqual(target.read_text(), "user edit")
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 2\r\n")

    def test_missing_managed_file_blocks_changes(self):
        self.engine.apply(["test"])
        (self.root / "extensions/demo/new.py").unlink()
        with self.assertRaises(Conflict):
            self.engine.apply([])

    def test_update_uses_original_baseline_then_restores_original(self):
        self.engine.apply(["test"])
        operation = self.manifest["components"][0]["files"][0]
        operation["edits"][0]["new"] = "3"
        operation["after"] = digest(b"value = 3\n")
        self.manifest["version"] = "2"
        self.engine.package = self.make_package()
        self.engine.apply(["test"])
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 3\r\n")
        self.engine.apply([])
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 1\r\n")

    def test_update_removes_retired_file(self):
        self.engine.apply(["test"])
        self.manifest["components"][0]["files"].pop()
        self.engine.package = self.make_package()
        self.engine.apply(["test"])
        self.assertFalse((self.root / "extensions/demo/new.py").exists())

    def test_generated_asset_replacement_is_checked_and_reversible(self):
        op = self.manifest["components"][0]["files"][0]
        op.update(kind="replace", payload="payload/new.py", after=digest(b"new = True\n"))
        self.engine.package = self.make_package()
        self.engine.apply(["test"])
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"new = True\n")
        self.engine.apply([])
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 1\r\n")
        (self.root / "modules/test.py").write_text("user edit")
        with self.assertRaisesRegex(Conflict, "local edits"):
            self.engine.plan(["test"])

    def test_checksum_corruption_refused(self):
        (self.folder / "payload/new.py").write_text("bad")
        with self.assertRaisesRegex(Conflict, "checksum"):
            Package(self.folder)

    def test_corrupt_backup_refused_before_restore(self):
        self.engine.apply(["test"])
        key = self.engine.state()["files"]["modules/test.py"]["before"]
        self.engine.internal("blobs/" + key).write_bytes(b"bad")
        with self.assertRaisesRegex(Conflict, "Backup checksum"):
            self.engine.apply([])
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 2\r\n")

    def test_failure_rolls_back_all_files(self):
        original = self.engine.write_target
        calls = 0
        def fail_once(name, content):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated disk error")
            return original(name, content)
        with patch.object(self.engine, "write_target", side_effect=fail_once):
            with self.assertRaises(OSError):
                self.engine.apply(["test"])
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 1\r\n")
        self.assertFalse((self.root / "extensions/demo/new.py").exists())
        self.assertFalse(self.engine.internal("journal.json").exists())

    def test_crash_journal_recovered(self):
        original = self.engine.write_target
        def crash(name, content):
            original(name, content)
            raise KeyboardInterrupt("simulated power loss")
        with patch.object(self.engine, "write_target", side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                self.engine.apply(["test"])
        with self.assertRaisesRegex(Conflict, "Recover"):
            self.engine.plan(["test"])
        self.assertTrue(self.engine.recover())
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 1\r\n")

    def test_recovery_does_not_overwrite_post_crash_edit(self):
        with patch.object(self.engine, "write_target", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.engine.apply(["test"])
        (self.root / "modules/test.py").write_text("retain edit")
        with self.assertRaisesRegex(Conflict, "Recovery conflict"):
            self.engine.recover()
        self.assertEqual((self.root / "modules/test.py").read_text(), "retain edit")

    def test_running_process_probe_blocks_mutation(self):
        self.engine.probe = lambda root: (_ for _ in ()).throw(Conflict("running"))
        with self.assertRaisesRegex(Conflict, "running"):
            self.engine.apply(["test"])
        self.assertFalse(self.engine.store.exists())

    def test_path_traversal_and_windows_aliases_rejected(self):
        for name in ("../outside", "a/../b", "/absolute", "C:/path", "a\\b", ".git/config", ".Git/config", "con.txt", "a./b", "a /b", ".forgeneomodification/state.json", "a//b"):
            with self.subTest(name=name), self.assertRaises(Conflict):
                path_in(self.root, name)

    def test_hardlink_refused(self):
        os.link(self.root / "modules/test.py", self.base / "alias.py")
        with self.assertRaisesRegex(Conflict, "Hardlinked"):
            self.engine.plan(["test"])

    def test_symlink_or_junction_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.root / "extensions"
        if os.name == "nt":
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
            if result.returncode:
                self.skipTest("Junction creation unavailable")
        else:
            link.symlink_to(outside, target_is_directory=True)
        self.addCleanup(lambda: link.rmdir() if os.name == "nt" else link.unlink())
        with self.assertRaisesRegex(Conflict, "reparse"):
            self.engine.plan(["test"])

    def test_missing_dependency_and_conflict(self):
        self.manifest["components"][0]["requires"] = ["missing"]
        self.engine.package = self.make_package()
        with self.assertRaisesRegex(Conflict, "requires"):
            self.engine.plan(["test"])
        self.manifest["components"][0].pop("requires")
        self.manifest["components"][0]["conflicts"] = ["other"]
        (self.root / "extensions/other").mkdir(parents=True)
        self.engine.package = self.make_package()
        with self.assertRaisesRegex(Conflict, "conflicting"):
            self.engine.plan(["test"])

    def test_disabled_extension_not_a_conflict(self):
        self.manifest["components"][0]["conflicts"] = ["other"]
        (self.root / "extensions/other").mkdir(parents=True)
        (self.root / "config.json").write_text('{"disabled_extensions":["other"]}')
        self.engine.package = self.make_package()
        self.engine.plan(["test"])

    def test_bad_python_payload_refused_before_writes(self):
        content = b"this is invalid python ("
        (self.folder / "payload/new.py").write_bytes(content)
        self.manifest["components"][0]["files"][1]["after"] = digest(content)
        self.engine.package = self.make_package()
        with self.assertRaises(SyntaxError):
            self.engine.apply(["test"])
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 1\r\n")

    def test_gzip_payload(self):
        content = b"new = True\n"
        (self.folder / "payload/new.py").write_bytes(gzip.compress(content))
        self.manifest["components"][0]["files"][1]["compressed"] = True
        self.engine.package = self.make_package()
        self.engine.apply(["test"])
        self.assertEqual((self.root / "extensions/demo/new.py").read_bytes(), content)

    def test_overlapping_components_refused(self):
        duplicate = copy.deepcopy(self.manifest["components"][0])
        duplicate["id"] = "other"
        self.manifest["components"].append(duplicate)
        self.engine.package = self.make_package()
        with self.assertRaisesRegex(Conflict, "Overlapping"):
            self.engine.plan(["test", "other"])

    def test_update_archive_validated(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for file in self.folder.rglob("*"):
                if file.is_file():
                    archive.writestr("repo-sha/" + file.relative_to(self.folder).as_posix(), file.read_bytes())
        package = unpack(stream.getvalue(), self.base / "download")
        self.assertEqual(package.manifest["version"], "1")

    def test_zip_slip_refused(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("repo/../../escaped", b"bad")
        with self.assertRaises(Conflict):
            unpack(stream.getvalue(), self.base / "download")
        self.assertFalse((self.base / "escaped").exists())

    def test_nested_lock_is_refused(self):
        with self.engine.locked():
            with self.assertRaisesRegex(Conflict, "already running"):
                with self.engine.locked():
                    self.fail("lock entered")


if __name__ == "__main__":
    unittest.main()
