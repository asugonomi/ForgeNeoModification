import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fnm.engine import ExtensionConflict
from fnm.settings import SettingsError
from manager import wizard
import test_engine


class SettingsTests(unittest.TestCase):
    make_package = test_engine.LifecycleTests.make_package

    def setUp(self):
        test_engine.LifecycleTests.setUp(self)
        self.environment = patch.dict(os.environ, {"COMMANDLINE_ARGS": ""})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.manifest["components"][0].update(conflicts=["other"], label="test", license="MIT")
        (self.root / "extensions/other").mkdir(parents=True)
        self.engine.package = self.make_package()

    def config(self, relative, **values):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(values), encoding="utf-8-sig")
        return path

    def test_standard_bom_case_variation(self):
        self.config("config.json", disabled_extensions=["OTHER"])
        self.assertEqual(self.engine.plan(["test"])["settings_file"], str(self.root / "config.json"))

    def test_custom_settings_argument_with_spaces(self):
        target = self.config("profile space/custom.json", disabled_extensions=["other"])
        (self.root / "webui-user.bat").write_text('set COMMANDLINE_ARGS=--ui-settings-file "profile space/custom.json"\n')
        self.assertEqual(self.engine.plan(["test"])["settings_file"], str(target))

    def test_data_dir_quoted_assignment(self):
        target = self.config("profile space/config.json", disabled_extensions=["other"])
        (self.root / "webui-user.bat").write_text('set "COMMANDLINE_ARGS=--data-dir=\"profile space\""\n')
        self.assertEqual(self.engine.plan(["test"])["settings_file"], str(target))

    def test_explicit_path_overrides_launcher_and_ignores_other_configs(self):
        active = self.config("actual.json", disabled_extensions=[])
        self.config("config.json", disabled_extensions=["other"])
        self.engine.settings_file = active
        with self.assertRaises(ExtensionConflict) as caught:
            self.engine.plan(["test"])
        self.assertIn(str(active), str(caught.exception))
        self.config("actual.json", disabled_extensions=["other"])
        self.engine.plan(["test"])

    def test_missing_or_invalid_settings_never_bypass(self):
        self.engine.settings_file = self.root / "missing.json"
        with self.assertRaises(SettingsError):
            self.engine.plan(["test"])
        self.engine.settings_file = self.config("bad.json", disabled_extensions="other")
        with self.assertRaises(SettingsError):
            self.engine.plan(["test"])

    def test_extra_does_not_disable_builtin(self):
        (self.root / "extensions-builtin/other").mkdir(parents=True)
        self.config("config.json", disable_all_extensions="extra")
        with self.assertRaises(ExtensionConflict):
            self.engine.plan(["test"])
        self.config("config.json", disable_all_extensions="all")
        self.engine.plan(["test"])

    def test_environment_settings_path(self):
        target = self.config("env.json", disabled_extensions=["other"])
        with patch.dict(os.environ, {"COMMANDLINE_ARGS": '--ui-settings-file="env.json"'}):
            self.assertEqual(self.engine.plan(["test"])["settings_file"], str(target))

    def test_unresolved_batch_variable_requires_explicit_file(self):
        (self.root / "webui-user.bat").write_text('set COMMANDLINE_ARGS=--data-dir "%PROFILE%"\n')
        with self.assertRaises(SettingsError):
            self.engine.plan(["test"])

    def test_interactive_retry_uses_chosen_config_without_editing_it(self):
        target = self.config("actual.json", disabled_extensions=["other"])
        before = target.read_bytes()
        with patch("builtins.input", side_effect=["", str(target), "y"]), patch("builtins.print"):
            self.assertEqual(wizard(self.engine, "install"), 0)
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(self.engine.state()["components"], ["test"])
        self.engine.apply([])

    def test_settings_rechecked_at_apply(self):
        self.config("config.json", disabled_extensions=["other"])
        self.engine.plan(["test"])
        self.config("config.json", disabled_extensions=[])
        with self.assertRaises(ExtensionConflict):
            self.engine.apply(["test"])
        self.assertFalse((self.root / "extensions/demo/new.py").exists())
