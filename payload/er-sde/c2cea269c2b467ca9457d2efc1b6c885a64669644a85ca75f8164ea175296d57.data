# ER SDE (ComfyUI) for Forge Neo

独立したサンプラー **`er sde (comfyui)`** を追加します。既存の `ER SDE` とその別名 `er_sde` は変更しません。

Forge Neo の Sampling Method で `er sde (comfyui)` を選択してください。Scheduler は通常どおり別に選択します。txt2img / img2img / Hires.fix は Forge の既存処理を使います。

## 実装元

- [ComfyUI公式 sampling.py / 固定コミット](https://github.com/Comfy-Org/ComfyUI/blob/63e5bf594339f676b4b15e072529873e3448409e/comfy/k_diffusion/sampling.py)
- 通常KSamplerの `er_sde` の既定値：`s_noise=1.0`、`max_stage=3`、積分点200、公式の既定noise_scaler。
- SamplerER_SDEノードも同じ関数を利用します。ノード既定のER-SDE / eta=1は通常KSamplerと同じ設定です。ノードの別solver_typeやeta変更用UIは追加しません。
- コード由来・元ファイルのSHA256は `UPSTREAM.json`、ライセンスは `LICENSE` に収録しています。

## 接続部分の変更

演算式・計算順序・Seed付き追加ノイズ生成は公式実装を保持します。ComfyUIのmodel_sampling取得をForgeのpredictor取得に、CONST判定をForgeの `prediction_type == "const"` に接続しました。進捗表示はForgeの既存callbackとtqdmを使用します。

追加ノイズは専用のTorch Generatorを使います。画像の初期ノイズ、プロンプト処理、モデルロード、CFG、Shift、LoRA、VAEはForgeに任せます。初期ノイズをComfyUIに寄せる場合はForgeのRNGをCPUに指定できますが、この拡張から設定を変更することはありません。

バッチではComfyUIの1回のKSampler呼び出し同様、バッチ先頭のSeedで1個の追加ノイズGeneratorを初期化します。バッチサイズを変更した場合に各画像が単独生成と一致する仕様ではありません。

## 導入と元に戻す方法

このフォルダーをForgeの `extensions/sd-webui-er-sde-comfy` に配置してForgeを再起動します。追加の共有依存関係はありません。

元に戻すにはExtensions画面でこの拡張を無効にし、Forgeを再起動します。またはForge終了中にフォルダーをextensionsの外へ移動します。既存 `ER SDE` は常に残ります。本体ファイルや既存サンプラーの復元作業は不要です。

## 検証

ForgeのPythonで `tests/test_parity.py` を実行すると、同梱した固定コミットの未改変関数と、各ステップ・ノイズ・最終latentを比較します。CUDAが利用可能ならCPUとGPUで実行します。

実モデル検証の結果は作業記録を参照してください。異なるWebUI全体のピクセル一致を保証する拡張ではありません。

通常利用では診断JSONやlatentを保存しません。開発テストに限り、拡張直下に `validation.json` を置き、`enabled: true` と記録先の絶対パス `directory` を指定すると診断記録が有効になります。テスト終了後はこのファイルを除去してください。
