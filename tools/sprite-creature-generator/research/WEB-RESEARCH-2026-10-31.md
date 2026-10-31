# Web research, 2026-10-31

Facts gathered from the pages listed under each section, read on 2026-10-31. Prices and
download counts move; re-check before spending money. "Unverified" means it comes from a model
card or search snippet, not a page we read in full.

## 1. Existing Pokémon-sprite models

None is trained on Gen 3 (Ruby/Sapphire/Emerald) sprites specifically. All use 96x96 sprites
(Gen 4/5 size) upscaled 8x, with BLIP captions.

| Model | Base | Data and tags | Licence | Notes |
| --- | --- | --- | --- | --- |
| [Pokemon Sprite PixelArt 768](https://civitai.com/models/161280/pokemon-sprite-pixelart-768) (v2.1-beta, Dec 2023) | SD 1.5 | 96x96 sprites at 768 px, BLIP captions. No trigger. Tags `gen1`..`gen5` (style), `backside`, `shiny`, type tags (`grasstype`...), `gmax`, `mega` | not shown | The only one with back and shiny sprites. Generate at 768, downscale 8x. **Best free baseline** for our eval (generate at 512 and downscale 8x to 64) |
| [Pokemon Trainer Sprite PixelArt XL](https://civitai.com/models/159333/pokemon-trainer-sprite-pixelart) / [HF](https://huggingface.co/sWizad/pokemon-trainer-sprite-pixelart) | SDXL | Same author (sWizad), same 96x96 + BLIP recipe; trainers. Also Flux, 768 and 512 versions | bespoke | ~69K downloads. People, not creatures |
| [sWizad/pokemon-trainer-sprites-pixelart-flux](https://huggingface.co/sWizad/pokemon-trainer-sprites-pixelart-flux) | FLUX.1-dev | Same recipe; prompts "a pixel image of ..., on white background" | bespoke | |
| [sr5434/sd-pokemon-model-lora](https://huggingface.co/sr5434/sd-pokemon-model-lora) | SD 1.4 | lambda/pokemon-blip-captions (Sugimori-style artwork, not sprites) | not stated | Not useful |
| [lambda/pokemon-blip-captions](https://huggingface.co/datasets/lambda/pokemon-blip-captions) | dataset | <1K images | cc-by-nc-sa-4.0 | **Taken down after a DMCA notice from The Pokémon Company.** Lesson: keep our dataset and LoRA private (the Black design already says models and outputs stay inside the personal project) |

Generic pixel-art models (style baselines, not Pokémon):

- [nerijs/pixel-art-xl](https://huggingface.co/nerijs/pixel-art-xl): SDXL LoRA, no trigger,
  "downscale 8 times ... nearest neighbours", use the fp16-fix VAE; LCM LoRA at 8 steps, CFG
  1.5, strength 1.2 for speed. CreativeML OpenRAIL-M. The Black design's baseline (C5
  `--baseline`).
- [Limbicnation/pixel-art-lora](https://huggingface.co/Limbicnation/pixel-art-lora): FLUX.2-klein-4B
  (Apache-2.0), 1,010 CC0 + synthetic images, rank 64 / alpha 128, 1000 steps, LR 1e-4, 4-step
  inference at CFG 1. Shows a small modern base can be trained cheaply; generic fantasy subjects.
- Others found but not read: [Pixel Art Style LoRA](https://civitai.com/models/2233307/pixel-art-style-lora),
  [Pixel Art Redmond (SDXL)](https://artificialguy.com/blog/pixel-art-redmond-lora/),
  [Retro Diffusion desktop](https://astropulse.gumroad.com/l/RetroDiffusion),
  overview lists ([aiarty](https://www.aiarty.com/stable-diffusion-guide/best-stable-diffusion-models.htm),
  [gamedevaihub](https://gamedevaihub.com/best-ai-pixel-art-generators-for-2d-indie-games/),
  [mage.space](https://blog.mage.space/article/best-ai-pixel-art-generators-2026/83330b2b-607d-4ef3-bca0-19e8ef307e2e)).

## 2. Hosted pixel-art generators (no GPU needed)

**PixelLab** ([API](https://www.pixellab.ai/pixellab-api), [rotate](https://www.pixellab.ai/docs/tools/rotate),
[animate](https://www.pixellab.ai/docs/tools/animate-with-text-pro)):

- Native pixel sizes. Rotate accepts 16, 32, 64 and 128 square; Pixflux up to 400x400 area.
- Views: rotate (camera view, direction, projection) and "8 rotations v3"
  (`POST /v2/generate-8-rotations-v3`, south-facing input, up to 256x256). Candidate for
  front -> back.
- Animation: "animate with text (Pro)" from a reference + action; 64x64 gives 16 frames.
  Candidate for the second frame.
- Inpainting: `/v2/inpaint`, `inpaint-v3` (mask + prompt).
- **Palette lock**: "your image is put on the palette first, then every frame uses only these
  colours" (Lospec palettes importable). Exactly our shared-palette rule.
- Price per call (estimates): Pixflux 64x64 $0.008, rotate 64x64 $0.011, 8 rotations 64x64
  $0.034. Pro animation needs a subscription tier.
- Unknown: style control. It is not trained on Emerald, so it may need our own reference images
  as style input; test before relying on it.

**Retro Diffusion** ([site](https://www.retrodiffusion.ai/), [API](https://www.retrodiffusion.ai/api)):
"From $0.03 an image", $0.50 starting credit, credits never expire, "real, grid-aligned,
palette-controlled pixel art from the start". Model names, sizes and API parameters were not
readable (JS pages); unverified.

## 3. Cleanup: AI image -> true pixel grid

Our finisher (Black C8) does this; these are prior art to borrow from.

| Tool | Grid detection | Colour per cell | Licence |
| --- | --- | --- | --- |
| [Retro-Diffusion/pixel-art-fixer](https://github.com/Retro-Diffusion/pixel-art-fixer) | Three detectors vote (autocorrelation, run lengths, self-similarity); sub-pixel step | k-means (K 16-48) decides *which* cluster wins a cell; the colour is the mean of original pixels with that label; alpha by majority | MIT (Python + Rust) |
| [Danamir/pixelart-cleaner](https://github.com/Danamir/pixelart-cleaner) | Luma-diff edges, percentile threshold, peak spacing, regular or irregular spans | centre / centre region / mode | GPL-3.0 (don't copy code) |
| [alvincrespo/pxl-cleanup](https://github.com/alvincrespo/pxl-cleanup) (uses `unfake`) | auto or fixed pixel size | k-means over *distinct* colours so small accents survive; `--colors 15`; edge flood-fill background removal | MIT |
| [unfake.js](https://github.com/jenissimo/unfake.js) ([write-up](https://dev.to/jenissimo/how-to-tame-your-ai-pixel-art-3pk5)) | Sobel profiles, histogram of peak gaps, phase search | dominant colour if it beats the runner-up by 5%, else mean; Wu quantisation first | unverified |
| [PixelRefiner](https://github.com/HappyOnigiri/PixelRefiner) | auto with confidence | Oklab k-means, fixed palettes, dithering | MIT (TS, browser) |
| [Sprite Fusion Pixel Snapper](https://www.spritefusion.com/pixel-snapper/how-to-fix-ai-pixel-art) | quantise first, then edge profiles and "walked cuts" | per-cell vote | unverified |

Takeaways: (1) we don't need grid detection if we train on a fixed grid (16 px per sprite
pixel, fixed phase, as Black's C3 does) but it rescues off-grid output; (2) vote per cell,
never average blindly; (3) cluster over distinct colours, not pixel counts, so 1-px highlights
(9-21% of vanilla pixels) survive; (4) none of these shares one palette across front, frame 2
and back. We do that ourselves (palette from the picked front, nearest-colour map for the rest).

## 4. Image-edit models for back views and the second frame

- [FLUX.1 Kontext [dev]](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev): 12B,
  instruction editing, "character, style and object reference without any finetuning",
  "minimal visual drift" over successive edits; ~246 LoRAs on the Hub. No claim about turning a
  character around. Licence: FLUX.1 [dev] Non-Commercial (card says outputs may be used for
  personal, scientific and commercial purposes).
- [Qwen-Image-Edit](https://huggingface.co/Qwen/Qwen-Image-Edit): 20B, Qwen2.5-VL + VAE
  conditioning; the card shows 90 and 180 degree **viewpoint changes** (on objects) and
  character consistency (a mascot); ~49 LoRAs; diffusers `QwenImageEditPipeline`;
  Apache-2.0.
- Neither is tested on pixel sprites. Plan: test both on 20 vanilla fronts -> backs (we have
  the true backs to score against) before committing to the Black design's IP-Adapter or
  paired-LoRA route.

## 5. Training and inference cost

| Option | Price | Source |
| --- | --- | --- |
| fal `flux-lora-fast-training` | $2 per run (scales with steps; default 1000) | [fal](https://fal.ai/models/fal-ai/flux-lora-fast-training) |
| fal `turbo-flux-trainer` | $2.40 per 1000 steps | [fal](https://fal.ai/models/fal-ai/turbo-flux-trainer) |
| fal `flux-lora` inference | $0.035 per megapixel, rounded up: ~$0.07 per 1024 px image | [fal](https://fal.ai/models/fal-ai/flux-lora) |
| fal Flux 3 Klein edit + LoRA | $0.012/MP (base $0.035/MP); a Klein trainer exists | [fal](https://fal.ai/models/blackforestlabs/flux-3/klein/edit-image/lora) |
| fal raw GPUs | H100 $2.49-4.50/h, RTX PRO 6000 96GB $1.99-4.00/h | [fal pricing](https://fal.ai/pricing) |
| RunPod community (via cost guide) | RTX 3090 $0.22/h, **RTX 4090 $0.34/h**, A40 $0.39, A100 80GB $1.19, H100 $2.49 | [aiofm guide](https://aiofm.info/en/guides/cost-to-train-lora-cloud-gpu) (referral links; vendor-adjacent) |
| Flux LoRA, 20 imgs, 1500 steps | 4090 60-90 min; A100 25-35 min; ~$1.60 for a tuned LoRA incl. iterations | same guide |
| kohya_ss on RunPod | install guide exists | [digitalcreativeai](https://www.digitalcreativeai.net/en/post/installation-guide-kohya-ss_gui-using-gpu-cloud-runpod) |

Not verified (search results only, pages not read): Replicate per-second prices, Vast.ai,
Modal; M1 inference speed ([insiderllm Mac guide](https://insiderllm.com/guides/stable-diffusion-mac-mlx/),
[localaimaster Mac guide](https://localaimaster.com/blog/local-image-generation-mac)). From
general knowledge (unverified): SDXL at 1024 px on an M1 32 GB takes on the order of a minute
per image in diffusers/MPS, faster in Draw Things; fine for picking, slow for a 7,000-image batch.

## 6. Licences (check the model cards before the build)

- SDXL 1.0: CreativeML OpenRAIL++-M (permissive, use restrictions only).
- FLUX.1 [dev] and Kontext [dev]: non-commercial weights licence
  ([text](https://open.windriver.com/info/uni-license-list/licenses/flux-1-nc.html),
  [guide](https://www.promptzone.com/zuzanna_choi/flux-ai-license-key-insights-2g8d.md)).
  FLUX.1 [schnell]: Apache-2.0.
- Qwen-Image / Qwen-Image-Edit: Apache-2.0.
- Overview: [license matrix (Aug 2026)](https://invideo.io/blog/open-source-image-models-licenses/),
  [localaimaster](https://localaimaster.com/blog/local-image-model-licenses-commercial-use).
- Our training data is Nintendo / Game Freak art. This is a personal fan project; keep the
  dataset and LoRA private (see the lambda dataset takedown above).
