# ForgeNeoModification 0.2.0

EasyForgeNeo / Forge Neo向けの一括導入・更新・復元ツールです。番号を選ぶ操作をなくし、対象の全機能と不足している拡張をまとめて導入します。生成キューだけは任意です。

## 導入

1. **Code → Download ZIP** を取得し、Forgeとは別の新しいフォルダーへ展開します。
2. Forgeを終了して `Install.cmd` をダブルクリックします。
3. Forgeフォルダー、またはEasyForgeNeoの親フォルダーを選びます。
4. キューが必要な場合だけ `y`、不要ならEnterを押します。
5. 拡張の取得と検証が終わったら、変更概要を確認して `y` を入力します。
6. Forgeを起動し直します。拡張の依存ライブラリは通常のForge起動時に準備されます。必要に応じてCtrl+F5で画面を再読み込みしてください。

**0.1.xのUpdate.cmdだけでは管理コードが更新されません。必ず0.2.0のZIPを新しいフォルダーへ展開してください。** 既存のバックアップは引き続き使用します。

Windows 10/11、Python 3.10以上、Git、インターネット接続が必要です。Forgeのvenv内Pythonを優先します。モデルや個人設定は配布しません。

## まとめて導入するもの

| 機能 | 内容 |
|---|---|
| 入力応答改善 | プロンプト入力の同期 |
| Fine Film Grain | 微細なフィルム粒状感 |
| Anima Native Tools | 符号付き重み、TeaCache、層の再実行 |
| ER SDE | サンプラー追加 |
| Autocomplete | 改修版、Fullタグ辞書・日本語辞書を同梱 |
| NeoMerger | モデル一覧の改修版 |
| AADetailer | Anima Native Toolsの引き継ぎ改修 |
| Prompt All-in-One | サムネイル・リンク先などの改修 |
| Civitai Helper | モデル名一覧の改修 |
| Anima Model Tools | 量子化・LoRA焼き込み・層移植。0.2.0で追加 |
| 生成キュー（任意） | 専用拡張と本体パッチ。生成設定のONは手動 |

不足している対象拡張は、検証済みの公開コミットのソースを自動取得して配置します。既存Gitリポジトリがある場合は、そのデータやremoteを保持して改修差分だけを適用します。新規追加する拡張はGitチェックアウトではなく、この管理ツールが更新・復元するファイルとして導入します。モデルは取得しません。

## 競合拡張と設定

Spectrum、旧NegPiP、HareSkip、Multi-CSV、旧生成キューなど、選択機能と競合する拡張があっても手作業で無効化する必要はありません。検出した拡張を実際の設定JSONの `disabled_extensions` に追加し、既存の無効化指定やほかの設定は保持します。元の拡張フォルダーは削除しません。

復元時は、このツールが追加した無効化指定だけを取り除きます。導入後に変更したその他の設定・追加の無効化指定は保持します。生成画面での機能OFFと拡張全体の無効化は別です。

標準config.jsonに加え、webui-user.batの単純なCOMMANDLINE_ARGSにある `--ui-settings-file` / `--data-dir` に対応します。複雑なランチャーや別設定を使う場合は、表示される参照先を確認し、実際の設定JSONを指定してください。CLIは `--settings-file` に対応します。Forgeフォルダー外の設定は自動編集せず、競合拡張の手動無効化が必要です。

独自改変のある既存ファイルは無条件に上書きしません。対象ファイルの不一致や、管理中のコードへの手編集があれば理由を表示して停止します。「一括導入」は未知の改変を消して強制導入する意味ではありません。

## 更新・復元

| ファイル | 操作 |
|---|---|
| Install.cmd | 全機能を一括導入。キューのみ任意 |
| Update.cmd | 最新パッケージを取得し全機能を更新・追加。キューは以前の選択を保持 |
| Uninstall.cmd | 管理ファイルを元に戻し、新規追加ファイルと自動無効化指定を取り除く |
| Recover.cmd | 中断した処理を直前の状態へ戻す |
| Status.cmd | 管理中の版と機能を表示 |

`.forgeneomodification` に元ファイルと処理記録を保存します。処理途中の失敗はロールバックします。復元後もバックアップを残します。空のフォルダーが残る場合があります。

管理中にEasyForgeNeoのUpdate.batや拡張画面の更新を重ねないでください。EasyForgeNeo側を更新する場合は、先にこのツールで復元し、EasyForgeNeoを更新してから再導入します。Forge本体を勝手に更新・ダウングレードする機能はありません。

## 検証対象

2026-11-08に公式の最新コミットを確認しました。

- EasyForgeNeo main: `4fa851def666d0ba120179b2fd3752d661936c53`
- Forge Neo neo: `4f4284b02a5c814b81c328c64ed7e99a139f21ef`

このForge版向けにキューパッチを更新し、旧基準版用の差分も保持しています。別HEADというだけでは拒否せず、実際の対象ファイルを検証します。将来の上流変更への無条件対応ではありません。

[TESTING.md](TESTING.md) に検証範囲を記載しています。インストーラの適用・復元は隔離コピーで検証していますが、GPU生成・各拡張の実画面・全組み合わせは未検証です。

## 公開フォークとライセンス

既存の改修は拡張ごとのフォークです。固定コミットは [FORKS.json](FORKS.json) と [manifest.json](manifest.json) を参照してください。

- [Autocomplete](https://github.com/asugonomi/sd-webui-tagcomplete-neo/tree/forgeneo-modification)
- [NeoMerger](https://github.com/asugonomi/NeoMerger) — CC BY-NC 4.0、非商用条件あり
- [AADetailer](https://github.com/asugonomi/aadetailer-neoforge)
- [Prompt All-in-One](https://github.com/asugonomi/sd-webui-prompt-all-in-one-neo/tree/forgeneo-modification)
- [Civitai Helper](https://github.com/asugonomi/Stable-Diffusion-Webui-Civitai-Helper-RED-UPDATE)
- [生成キュー](https://github.com/asugonomi/Forge-Neo-Generation-Queue)
- [Anima Model Tools](https://github.com/asugonomi/anima-model-tools)

AutocompleteとPrompt All-in-Oneの改修は `forgeneo-modification` ブランチです。直接フォークを導入する方法と、この管理ツールによる適用を同じ機能へ重ねないでください。

管理ツールはMITです。配布内容には各上流のライセンスが適用されます。詳細は [THIRD_PARTY.md](THIRD_PARTY.md)、licensesフォルダー、取得した拡張のLICENSEを参照してください。
