# ForgeNeoModification

Forge Neoに加えた変更を、対応版の確認・バックアップ・復元付きで導入するWindows用ツールです。既存拡張の改修はそれぞれのフォークとして公開し、このツールはその固定版の変更を管理します。

**0.1.1は対象ファイルの内容で適用可否を判定するプレビュー版です。** インストーラとファイル復元のテスト済み範囲は [TESTING.md](TESTING.md) を参照してください。GPU生成・すべての拡張との併用を保証する版ではありません。

## 使い方

1. このリポジトリの **Code → Download ZIP** をダウンロードし、Forgeとは別のフォルダーへ展開します。
2. Forgeを終了し、`Install.cmd` をダブルクリックします。
3. `webui.py` があるForgeフォルダー（またはEasyForgeNeoの親フォルダー）を選択します。
4. 機能の番号を選び、表示される変更予定を確認して `y` を入力します。
5. Forgeを起動し直します。画面側の変更は必要に応じてCtrl+F5で再読み込みします。

既定で選択するのは「入力応答改善」「微細なフィルム粒状感」の2つです。**キューは選択しない限り導入されず、導入しても設定を自動でONにしません。** Windows 10/11、Python 3.10以上とGitが必要です。Forgeのvenvがある場合はそのPythonを使います。Forge自体のPython要件は別に満たしてください。

| 起動ファイル | 操作 |
|---|---|
| `Install.cmd` | 機能を選択して導入。既に管理中なら選択内容を更新 |
| `Update.cmd` | GitHubの最新版パッケージを取得し、既存の選択機能を更新 |
| `Uninstall.cmd` | このツールが管理する全機能を導入前へ戻す |
| `Recover.cmd` | 電源断などで中断した処理を、その処理の直前へ戻す |
| `Status.cmd` | 管理中の機能と版を表示（読み取り専用） |

バックアップはForge直下の `.forgeneomodification` に保存されます。復元後も残します。モデル・画像・個人設定・生成履歴は配布せず、設定ファイル全体を書き換えません。辞書はAutocompleteフォーク側へ収録しています。

## 対応版と既存拡張

Forge本体の検証基準HEADは `7d6fd36c58a0e861640bcfe421e4f990921d7f2a`（Haoming02/sd-webui-forge-classic）です。フォルダー名だけでは対応判定しません。

Autocompleteは `645f22f0d8ba5ad7f10f54aadcf292cf0499e9f8`、Prompt All-in-Oneは `c46e279f87f912e5e4ede37bfaa8230fe0222f1d`（2026-11-08確認時点の上流最新版）を基準に統合しました。古い基準版への差分は公開版から外しています。PAIOの上流サムネイル生成・入力整形を保持し、旧独自の画像エラー処理を統合整理しています。

既存拡張の改修を選択する場合は、拡張が指定名でインストール済みである必要があります。Forge本体・拡張とも、基準コミットとの差だけでは停止せず、注意を表示して対象ファイルを検証します。変更する既存ファイルの内容が基準と一致すれば適用できます。独立拡張（Anima Native Toolsなど）は追加先の競合を検査して導入できます。対象ファイルの変更・既存実装との競合・リポジトリの欠落は引き続き停止します。別バージョンでの実行時互換性を保証するものではありません。HEADやremoteは変更しません。

各フォークを直接インストールする方法もありますが、そのインストールはこの管理ツールのバックアップ対象にはなりません。同じ機能をフォーク直接導入と管理ツールの両方で適用しないでください。

| 機能 | 公開元 / 注意点 |
|---|---|
| Autocomplete | [sd-webui-tagcomplete-neo / 改修ブランチ](https://github.com/asugonomi/sd-webui-tagcomplete-neo/tree/forgeneo-modification)。Fullタグ辞書・Anima 2.9B用日本語翻訳を収録 |
| モデル一覧 | [NeoMerger](https://github.com/asugonomi/NeoMerger)。CC BY-NC 4.0、非商用条件あり |
| AnimaのADetailer引き継ぎ | [aadetailer-neoforge](https://github.com/asugonomi/aadetailer-neoforge)。Anima Native Toolsも選択 |
| サムネイル・リンク先 | [sd-webui-prompt-all-in-one-neo / 改修ブランチ](https://github.com/asugonomi/sd-webui-prompt-all-in-one-neo/tree/forgeneo-modification) |
| Civitaiモデル名一覧 | [Civitai Helper](https://github.com/asugonomi/Stable-Diffusion-Webui-Civitai-Helper-RED-UPDATE)。一覧の追加・削除を含む任意機能 |
| 生成キュー | [Forge-Neo-Generation-Queue](https://github.com/asugonomi/Forge-Neo-Generation-Queue)。本体パッチと同時に使用、既定OFF |

入力応答改善・粒状感・Anima Native Tools・ER SDEサンプラーは独立拡張として配置します。Anima Model ToolsやP-H3などの大型独立機能は再梱包しません。旧動画・プロンプト拡張、個人ランチャー、モデル移動処理も含めません。

AutocompleteとPrompt All-in-Oneの改修版は `forgeneo-modification` ブランチです。フォークの `main` は上流版を残しています。直接導入する場合はブランチを明示してください。対応する公開コミットは [FORKS.json](FORKS.json) に記録しています。

```text
git clone --branch forgeneo-modification https://github.com/asugonomi/sd-webui-tagcomplete-neo.git
git clone --branch forgeneo-modification https://github.com/asugonomi/sd-webui-prompt-all-in-one-neo.git
```

## 復元と更新の保護

- 対象HEADを確認し、基準版との差を表示し、適用前の内容ハッシュを検証します。既にローカル改変済みの環境は、同じ内容でも勝手に管理下へ取り込みません。
- パッチは検証済みの差分だけを適用し、原本の生バイトを保存します。CRLF/LFを区別して原本を復元します。
- 再ビルドしたJavaScript・ソースマップ・CSSは、適用前ハッシュが一致する場合だけ生成済みファイルを置換します。手書きソースは差分を適用します。
- 導入後に手動編集されたファイルや消えた管理ファイルがあると、更新・復元を中止します。ユーザーの編集を無条件で上書きしません。
- 複数ファイルは一括で原子的に変更できないため、処理記録とバックアップで途中障害から復旧します。復旧対象まで編集されている場合は停止し、記録を保持します。
- シンボリックリンク、junction、ハードリンクを通じた変更を拒否します。モデル用リンクへは触れません。
- 上流リポジトリの更新は別作業です。管理中に拡張のUpdate/git pullを重ねず、まず復元してから対応版へ更新してください。

`Update.cmd` はGitHub mainのコミットを確定してからそのZIPを取得し、同梱チェックサムを照合します。チェックサムは破損検出用で、署名ではありません。ダウンロードされた管理コードを自動実行せず、現在の管理エンジンでデータを適用します。将来、管理エンジン自体の更新が必要な版では新しいZIPを展開してください。

## キューと競合

キューは本体4ファイルへの差分・追加モジュール・専用拡張をまとめて導入します。既存の通常キューが有効なら停止します。Anima Native ToolsとHareSkip / Spectrum / 旧NegPiP、AutocompleteとMulti-CSVの同時有効化も検出対象です。既存設定を勝手に無効化しません。

## 辞書・関連タグ

Autocomplete設定で `danbooru_20260731.csv` と `danbooru_translations_jp_anima29.csv` を選択してください。設定の自動変更はしません。辞書は2026-07-31系の配布データで、常に最新版という意味ではありません。

約249MBの生成済みSQLiteや使用頻度DBは同梱しません。関連タグ検索を使う場合はAutocompleteフォークの `tools/build_related_index.py` で公開元のタグ・共起CSVから索引を生成できます。未作成の場合は関連タグ機能をOFFにし、通常補完・整形・翻訳を使用してください。関連タグの共起データは同梱辞書と更新日が異なります。

## コマンドライン

```powershell
python manager.py plan --root "D:\Forge Neo" --components prompt-sync,fine-grain
python manager.py install --root "D:\Forge Neo" --components prompt-sync,fine-grain
python manager.py update --root "D:\Forge Neo" --package "D:\NewPackage"
python manager.py uninstall --root "D:\Forge Neo"
```

非対話CLIのinstall/update/uninstallは確認プロンプト無しで実行します。事前確認にはplanを使ってください。

## ライセンス

管理ツールはMIT。各改変・追加コード・辞書はそれぞれの出典と条件を保持します。[THIRD_PARTY.md](THIRD_PARTY.md) と `licenses/` を参照してください。

## 0.1.0からの更新

今回の修正は管理エンジンの変更です。古い `Update.cmd` では管理コードが置き換わらないため、最新版ZIPを新しい別フォルダーへ展開して、その `Install.cmd` / `Update.cmd` を使ってください。Forge側の既存バックアップは引き続き利用します。
