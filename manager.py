"""Windows command-line wizard; Python >= 3.10, no pip dependencies."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

from fnm.engine import Conflict, Engine, Package


def wizard(engine, action):
    state = engine.state()
    if action in ("install", "update"):
        if action == "update" and not state["components"]:
            raise Conflict("管理中の機能がありません。先に Install.cmd を実行してください。")
        selected = state["components"] if action == "update" else [c["id"] for c in engine.package.components.values() if c.get("default")]
        print("\n導入する機能を選択します。既存設定やモデルは変更しません。")
        choices = list(engine.package.components.values())
        for i, component in enumerate(choices, 1):
            mark = "*" if component["id"] in selected else " "
            print(f"{i:2}. [{mark}] {component['label']}\n      {component['license']}")
        print("\nEnter: *の機能を使用 / 数字をカンマ区切り: 選び直し / q: 中止")
        answer = input("> ").strip()
        if answer.lower() == "q":
            return 0
        if answer:
            indices = [int(value.strip()) for value in answer.split(",")]
            if any(i < 1 or i > len(choices) for i in indices):
                raise Conflict("一覧にある番号を指定してください。")
            selected = [choices[i - 1]["id"] for i in indices]
    else:
        selected = []
    if action == "recover":
        print("中断した処理を直前の状態へ復元します。")
    else:
        plan = engine.plan(selected)
        print(f"\n対象: {engine.root}\n変更するファイル: {len(plan['changes'])} 件")
        for name in plan["changes"]:
            print("  " + name)
        if "queue" in selected:
            print("\nキューは任意機能です。本体4ファイルも変更します。設定のONはWebUIで手動操作してください。")
        if not plan["changes"] and state["components"] == selected:
            print("変更は不要です。")
            return 0
    if input("\nForgeを終了してから実行してください。実行する場合は y: ").strip().lower() != "y":
        print("中止しました。")
        return 0
    result = engine.recover() if action == "recover" else engine.apply(selected)
    print("完了: " + json.dumps(result, ensure_ascii=False))
    print("Forgeを起動し直してください。画面の変更にはCtrl+F5も使用してください。")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Version-checked, reversible Forge Neo modifications")
    parser.add_argument("action", choices=["status", "plan", "install", "update", "uninstall", "recover"])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--components", help="Comma-separated component IDs (queue is never selected automatically)")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--online", action="store_true", help="Download the latest package from the fixed GitHub repository")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory(prefix="fnm-package-") as temporary:
            if args.online:
                if args.action != "update":
                    raise Conflict("--online is only valid for update")
                from fnm.updater import latest
                package, commit = latest(Path(temporary))
                print(f"Update package commit: {commit}")
            else:
                package = Package(args.package)
            engine = Engine(args.root, package)
            if args.action == "status":
                print(json.dumps(engine.state(), ensure_ascii=False, indent=2))
                return 0
            if args.interactive:
                return wizard(engine, args.action)
            if args.action == "recover":
                print(json.dumps({"recovered": engine.recover()}))
                return 0
            selected = (args.components.split(",") if args.components else engine.state()["components"] if args.action == "update"
                        else [c["id"] for c in package.components.values() if c.get("default")])
            if args.action == "uninstall":
                selected = []
            if args.action == "plan":
                plan = engine.plan(selected)
                print(json.dumps({"components": selected, "files": list(plan["changes"])}, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(engine.apply(selected), ensure_ascii=False))
            return 0
    except (Conflict, OSError, ValueError, KeyError, SyntaxError) as exc:
        print(f"STOP / 変更を中止しました: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
