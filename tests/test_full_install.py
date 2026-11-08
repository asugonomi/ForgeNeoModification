import io
import json
import unittest
from unittest.mock import patch
import zipfile

import test_engine
from fnm.bundle import prepare, source_files
from fnm.engine import Conflict, digest
from manager import wizard


class FullInstallTests(unittest.TestCase):
    make_package = test_engine.LifecycleTests.make_package

    def setUp(self):
        test_engine.LifecycleTests.setUp(self)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("source/scripts/main.py", "original = True\n")
            z.writestr("source/LICENSE", "Test license\n")
        self.archive = buffer.getvalue()
        self.repo = {"path": "extensions/demo", "url": "https://github.com/example/demo", "commit": "a" * 40, "archive_sha256": digest(self.archive)}
        self.manifest["components"][0].update(repositories=[self.repo], label="Test", license="MIT")
        self.engine.package = self.make_package()
        self.base_package = self.engine.package
        self.count = 0

    def prepare(self):
        self.count += 1
        self.engine.package = self.base_package
        self.engine.package = prepare(self.engine, ["test"], self.base / ("prepared" + str(self.count)), lambda url: self.archive)

    def test_missing_extension_full_install_repeat_restore(self):
        self.prepare()
        self.engine.apply(["test"])
        self.assertTrue((self.root / "extensions/demo/scripts/main.py").is_file())
        self.prepare()
        self.assertEqual(self.engine.apply(["test"])["changed_files"], 0)
        self.engine.apply([])
        self.assertFalse((self.root / "extensions/demo/scripts/main.py").exists())
        self.assertEqual((self.root / "modules/test.py").read_bytes(), b"value = 1\r\n")

    def test_preserves_existing_unrelated_files_and_refuses_local_code(self):
        target = self.root / "extensions/demo/scripts/main.py"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"private = True\n")
        with self.assertRaises(Conflict):
            self.prepare()
        self.assertEqual(target.read_bytes(), b"private = True\n")
        self.assertFalse(self.engine.store.exists())

    def test_download_hash_failure_writes_no_target(self):
        with self.assertRaisesRegex(Conflict, "checksum"):
            prepare(self.engine, ["test"], self.base / "bad", lambda url: b"wrong")
        self.assertFalse((self.root / "extensions/demo").exists())

    def test_disable_restore_preserves_other_settings_edits(self):
        self.manifest["components"][0]["conflicts"] = ["spectrum"]
        (self.root / "extensions/spectrum").mkdir(parents=True)
        self.engine.package = self.base_package = self.make_package()
        self.prepare()
        self.engine.apply(["test"])
        path = self.root / "config.json"
        config = json.loads(path.read_text())
        self.assertIn("spectrum", config["disabled_extensions"])
        config["user_preference"] = "new choice"
        config["disabled_extensions"].append("user-disabled")
        path.write_text(json.dumps(config))
        self.prepare()
        self.engine.apply(["test"])
        self.engine.apply([])
        restored = json.loads(path.read_text())
        self.assertEqual(restored["user_preference"], "new choice")
        self.assertEqual(restored["disabled_extensions"], ["user-disabled"])
        self.assertEqual(restored["private_key"], "retain-me")

    def test_previously_disabled_extension_remains_disabled(self):
        self.manifest["components"][0]["conflicts"] = ["spectrum"]
        (self.root / "extensions/spectrum").mkdir(parents=True)
        config = self.root / "config.json"
        config.write_text('{"disabled_extensions":["spectrum"],"user":true}')
        original = config.read_bytes()
        self.engine.package = self.base_package = self.make_package()
        self.prepare()
        self.engine.apply(["test"])
        self.engine.apply([])
        self.assertEqual(config.read_bytes(), original)

    def test_patch_variant_checks_matching_baseline(self):
        operation = self.manifest["components"][0]["files"][0]
        operation["variants"] = [{"before": digest(b"v = 3\n"), "after": digest(b"v = 4\n"), "edits": [{"start":4,"end":5,"old":"3","new":"4"}]}]
        self.assertEqual(self.base_package.transform(operation, b"v = 3\n"), b"v = 4\n")
        with self.assertRaises(Conflict):
            self.base_package.transform(operation, b"v = 9\n")

    def test_external_disabled_settings_are_read_only_and_rechecked(self):
        self.manifest["components"][0]["conflicts"] = ["spectrum"]
        (self.root / "extensions/spectrum").mkdir(parents=True)
        settings = self.base / "external.json"
        settings.write_text('{"disabled_extensions":["spectrum"]}')
        original = settings.read_bytes()
        self.engine.settings_file = settings
        self.engine.package = self.base_package = self.make_package()
        self.prepare()
        self.engine.plan(["test"])
        self.assertEqual(settings.read_bytes(), original)
        settings.write_text('{}')
        with self.assertRaisesRegex(Conflict, "conflicting"):
            self.engine.apply(["test"])

    def test_install_has_no_number_selection_and_queue_is_optional(self):
        self.manifest["components"].append({"id":"queue","label":"Queue","license":"MIT","default":False,"files":[]})
        self.engine.package = self.make_package()
        # Existing lifecycle fixture needs no download in this UI test.
        self.engine.package.components["test"]["repositories"] = []
        with patch("builtins.input", side_effect=["", "y"]) as user_input, patch("builtins.print"):
            wizard(self.engine, "install")
        self.assertEqual(self.engine.state()["components"], ["test"])
        self.assertEqual(user_input.call_count, 2)
