# Third-party sources and scope

This is an aggregate manager, not a blanket relicensing of its payloads. Changes are local Forge adaptations published in 2026; no upstream endorsement is implied. Exact upstream commits and file-level before/after checksums are in `manifest.json`.

| Component | Source | License / attribution |
|---|---|---|
| Forge patches / prompt synchronization adaptation | https://github.com/Haoming02/sd-webui-forge-classic | AGPL-3.0; AUTOMATIC1111, lllyasviel, Haoming02; `licenses/Forge-AGPL-3.0.txt` |
| Signed prompt weighting adaptation | https://github.com/pamparamm/ComfyUI-ppm | AGPL-3.0-or-later; `licenses/PPM-AGPL-3.0.txt` |
| Anima TeaCache coefficients / preset adaptation | https://github.com/CocyNoric/ComfyUI-Anima-TeaCache | Apache-2.0; `licenses/Anima-TeaCache-Apache-2.0.txt` |
| ER SDE adaptation | https://github.com/Comfy-Org/ComfyUI | GPL-3.0; commit and original SHA256 shipped with the extension |
| TagComplete Neo | https://github.com/eduardoabreu81/sd-webui-tagcomplete-neo | MIT, Dominik Reh / Neo maintainers; `licenses/sd-webui-tagcomplete-neo.txt` |
| Related tags / normalization helpers | https://github.com/newtextdoc1111/ComfyUI-Autocomplete-Plus | MIT, Copyright (c) 2025 newtextdoc1111; payload includes original license |
| NeoMerger | https://github.com/AkiumAI/NeoMerger | CC BY-NC 4.0, NeoMerger Contributors; **noncommercial**, see copied license |
| ADetailer Neo | https://github.com/abzaloff/aadetailer-neoforge | AGPL-3.0; original license retained |
| Prompt All-in-One Neo | https://github.com/eduardoabreu81/sd-webui-prompt-all-in-one-neo | MIT, Physton / Neo maintainers |
| Generation Queue | https://github.com/ukr8b3g-cmyk/Forge-Neo-Generation-Queue | MIT, Copyright (c) 2026 ukr8b3g-cmyk |
| Civitai Helper model-name list | https://github.com/Replactionap/Stable-Diffusion-Webui-Civitai-Helper-RED-UPDATE | No root license file found at the pinned local commit. Only model-name list changes are included; no license is invented for the upstream project. |
| Fine Film Grain | Local standalone image postprocessor | MIT, asugonomi |

The two additional autocomplete dictionaries are the user's public distribution data: Danbooru-style tag/category/count/alias data and Japanese translation data for Anima 2.9B. No usage-frequency DB, personal prompt history, API credentials, model files or model metadata are included. Code licenses do not claim ownership of the underlying tag names or third-party data. Data filenames, hashes and provenance notes are maintained in the autocomplete fork.

The package preserves modified source in patches and source payloads, including the Vue source corresponding to the shipped PAIO bundle. The manager does not combine the noncommercial NeoMerger code into its MIT engine; that optional component remains separately identified.
