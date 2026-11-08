"""Read Forge settings without executing its launcher or modifying configuration."""
import json
import os
from pathlib import Path
import re


class SettingsError(RuntimeError):
    pass


def settings_path(root, explicit=None):
    if explicit:
        path = Path(str(explicit).strip().strip('"'))
        return path if path.is_absolute() else root / path
    args = os.environ.get("COMMANDLINE_ARGS", "")
    launcher = root / "webui-user.bat"
    if launcher.is_file():
        # Only literal SET assignments are supported; never execute batch files.
        for line in launcher.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            match = re.fullmatch(r'\s*@?set\s+(.*)', line, re.I)
            if match:
                assignment = match.group(1).strip()
                if assignment.startswith('"') and assignment.endswith('"'):
                    assignment = assignment[1:-1]
                if assignment.upper().startswith("COMMANDLINE_ARGS="):
                    args = assignment.split("=", 1)[1]
    values = {}
    for match in re.finditer(r'(?<!\S)--(ui-settings-file|data-dir)(?:=|\s+)("[^"]*"|\S+)', args):
        value = match.group(2).strip('"')
        if any(char in value for char in "%!&|<>^"):
            raise SettingsError("起動設定のパスを自動解決できません。実際に使用している設定JSONを指定してください。")
        values[match.group(1)] = value
    if "ui-settings-file" in values:
        path = Path(values["ui-settings-file"])
    elif "data-dir" in values:
        path = Path(values["data-dir"]) / "config.json"
    else:
        path = Path("config.json")
    return path if path.is_absolute() else root / path


def load_settings(root, explicit=None):
    path = settings_path(root, explicit).resolve()
    if not path.is_file():
        raise SettingsError(f"設定ファイルが見つかりません: {path}。実際の設定JSONを指定してください。")
    try:
        config = json.loads(path.read_text(encoding="utf-8-sig"))
        disabled = config.get("disabled_extensions", [])
        mode = config.get("disable_all_extensions", "none")
        if not isinstance(disabled, list) or not all(isinstance(x, str) for x in disabled) or mode not in ("none", "extra", "all"):
            raise ValueError("invalid extension settings")
    except (ValueError, AttributeError, OSError) as exc:
        raise SettingsError(f"Forgeの設定を読み取れません: {path}") from exc
    return path, {name.casefold() for name in disabled}, mode
