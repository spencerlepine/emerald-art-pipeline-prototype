# Plan: creature sprites for Emerald with an image model

Research only (2026-10-31). Based on the owner's Black design
([prior-black/2D-SPRITE-LoRA-PIPELINE-DESIGN.md](prior-black/2D-SPRITE-LoRA-PIPELINE-DESIGN.md),
components C0-C12; read it first), the measurements in [vanilla-stats.json](vanilla-stats.json)
and the sources in [WEB-RESEARCH-2026-10-31.md](WEB-RESEARCH-2026-10-31.md).

## 1. What we are making

384 species folders in `graphics/pokemon/` (plus Unown's letter forms and Castform's weather
forms, category A5). Per species, five files the `creature` tool already writes, verifies and
installs: `anim_front.png` (front + second frame), `front.png`, `back.png`, `normal.pal`,
`shiny.pal` (see [../README.md](../README.md)). The replacements are listed in
[sw-creature-jobs.csv](sw-creature-jobs.csv):

| Group | Species | Example | Implication |
| --- | --- | --- | --- |
| `original` | 192 | BULBASAUR -> SPROUTLIZ "Lizard with a seed bulb on its back" | Designed after the Pokémon. The vanilla sprite is a good **init image / ControlNet** at medium denoise; the model changes the look, keeps the build |
| `canon` | 115 | RHYDON -> RANCOR, CAMERUPT -> BANTHA, ZUBAT -> MYNOCK | Real Star Wars creatures with their own shapes. Text + reference images (IP-Adapter) of the creature; no vanilla init |
| `databank` | 77 | MACHOP -> B1 DROID, METAGROSS -> R2 UNIT | Mostly droids from the official databank. Hard-surface; references matter most |

Vanilla size class (longest side of the front): 63 small (<40 px), 183 medium (40-55), 138
large (56+). Keep each replacement in its slot's size class so evolution lines still grow.

## 2. Facts measured on the 384 vanilla species

| Fact | Value | Design consequence |
| --- | --- | --- |
| Colours over front + frame 2 + back | median 13, p5 10, max 15 | Palette 15 + transparent, shared by all three frames (Black: same rule) |
| Front content box | median 48 x 47.5, p5-p95 28-64; area 566-2,346 | Size class drives the prompt and the finisher's placement |
| Front horizontal centre | median x 31.5 (p5-p95 30.5-33) | Centre at x = 31.5 |
| Front bottom row | median 55, p5-p95 45-63 | Not bottom-anchored; we keep the art's own bottom and write `y_offset` (tool does this) |
| Second frame vs front | median **72%** of pixels change (p5 34%, min 2%); never identical | A real second pose (mouth open, limbs moved), not a 1 px bob. Needs its own generation step (section 5) |
| Back vs front area | median 1.22x (p5 0.66, p95 1.93) | Backs are drawn closer/larger. Only 2.9% touch the bottom edge |
| Back colours | median 11 (front 13) | Back uses a subset of the front palette |
| Distinct colours in all palettes | 4,350 | Key colour must avoid them |
| Key colour distance (min RGB) | `#0000FF` 71.0, `#00FF00` 71.9, `#FF00FF` 0 (used), `#00FFFF` 46 | Use `#00FF00` or `#0000FF` (Black chose blue at 81) |

## 3. Reuse from the Black design, and what changes

| Black component | For Emerald |
| --- | --- |
| C0 still extractor (Rust, NDS decode) | **Not needed.** PNGs are already flat 64x64 in `graphics/pokemon/`; `creature.read_species()` reads them |
| C1 catalog | Rows = species x {front, front2, back}. Drop Unown/Castform extra forms (keep one). Holdout ~16 species stratified by egg group x size class |
| C2 captions | Data is already joined: `emerald-sw-db` entities have types, body colour, egg groups, dex category, height/weight (see the jobs CSV columns). VLM adds 3-8 visual features. Never put species names in captions |
| C3 prep | Scale **16** (64 x 16 = 1024, no margin) or 12 (768, 128 px margin, SD 1.5-friendly 768). Fixed phase. Key colour per section 2 |
| C4 train | Rows: ~384 x 3 = ~1,150 images (front, front2, back), or ~770 without frame 2. Black recipe for Creatures (rank 32/16, AdamW8bit 1e-4, ~8 epochs) |
| C5 eval | Baselines: nerijs/pixel-art-xl and the CivitAI "Pokemon Sprite PixelArt 768" LoRA (has `backside`), plus PixelLab |
| C6 concept prep | Concepts: Star Wars reference images per canon creature (owner supplies or we collect); `original` creatures use the vanilla sprite as the init |
| C7 generate | Front: img2img (vanilla init for `original`, pre-pixelated concept for canon) + LoRA + IP-Adapter. Back and frame 2: section 5 |
| C8 finisher | Build in `creature_sprite` (a new `finish` command): grid fit, per-cell vote, palette <= 15, back/frame 2 mapped onto the front palette, orphan cleanup, optional selective outline, centre x 31.5 |
| C9 scorer | Add our lint metrics (dark outline, orphans, colours, symmetry vs `corpus/creature64.json`) |
| C10 pick, C11 export | **Already exists:** the picked PNGs become a `creature64` spec (frames as grids), then `build`, `verify`, `install` (writes `y_offset`) |
| Shiny | Black's draft (hue shift +40 degrees in LCh, skip greys and outline), then owner tweak |

## 4. Model and hosting choice

- **Base: SDXL 1.0 + our LoRA** (the Black decision). Mature tooling (kohya, IP-Adapter Plus,
  ControlNet-Union), permissive licence, and the Black recipe is already written.
  Benchmark against a FLUX-family LoRA (fal trainer, ~$2) and Qwen-Image only if SDXL's eval
  fails; FLUX.1-dev weights are non-commercial (fine for this personal project).
- **Hardware:** the owner has an M1 Mac (32 GB), no NVIDIA GPU. Train on a rented GPU
  (RunPod 4090 ~$0.34/h or A100 ~$1.19/h; a 1,150-image SDXL LoRA is a few hours), run the
  batch there too, review sheets anywhere. The M1 can run single generations for picking
  (slow, ~1 min/image, unverified).
- **Batch cost estimate:** 384 species x (8 front + 8 back + 4 frame-2) = ~7,700 generations.
  Rented 4090 at ~5 s/image: ~11 h, ~$4. fal per-image API: ~$540. Use rented GPUs.
- **Zero-GPU first test (one evening, < $20):** PixelLab API on 10 creatures: native 64x64,
  palette lock, rotate for backs, animate for frame 2. If it reaches ~80% it may replace
  the LoRA for some groups; if not, it is a baseline.

## 5. The three hard problems

1. **Back view consistent with the front.** Options to test, in order: (a) Black's IP-Adapter
   with the picked front + LoRA `back view` caption; (b) Qwen-Image-Edit "turn around, view from
   behind" on the 16x upscaled front (Apache-2.0; the card shows 180-degree view changes);
   (c) FLUX Kontext; (d) Black's Plan B paired front|back LoRA (two 64s at 12x side by side =
   1536x768, a standard SDXL bucket). Score on the 16 holdouts, whose real backs we have.
2. **Second frame.** Vanilla changes ~72% of pixels. Options: (a) img2img from the picked front at
   denoise ~0.3 with an action word (`mouth open`, `arms raised`) and the same seed; (b) image-edit
   model "open its mouth, raise its claws"; (c) train frame 2 as a paired LoRA (front|front2,
   ~384 pairs); (d) PixelLab animate. The finisher maps it onto the front palette.
3. **Keeping it Emerald, not generic pixel art.** The LoRA must be trained on Emerald's own 64x64
   sprites at a fixed grid. Gen 4/5 models (96x96) have a different look; Emerald's sprites
   have darker selective outlines and fewer colours (median 13).

## 6. Build phases (when a GPU is available)

| Phase | Builds | Done when |
| --- | --- | --- |
| 0. Zero-GPU | `finish` command + roundtrip test on degraded vanilla sprites (Black C8 acceptance: >= 99% index match); PixelLab test on 10 creatures | Roundtrip passes; PixelLab sheet reviewed |
| 1. Data | catalog + captions (DB fields + VLM) for 384 x 3, holdouts frozen | Every row captioned and reviewed |
| 2. Baseline | nerijs + CivitAI Pokémon 768 + PixelLab through the finisher | Baseline sheets saved |
| 3. Train | SDXL LoRA (front+back+front2), checkpoint eval | Blind 1x test at <= 60% (Black criterion) |
| 4. Fronts | 10 creatures (5 original, 3 canon, 2 droids), 8 candidates each | Owner picks >= 1 good front for 8/10 |
| 5. Backs + frame 2 | options from section 5 | Holdout backs match fronts in >= 1 of 8 |
| 6. Production | batch by evolution line, owner review by sheet | Lines installed, checklist counts move |

## 7. Open questions for the owner

- GPU: rent (RunPod/Vast) or buy? Who runs it: the owner, or a Claude session with an API key
  for a hosted GPU?
- Reference images for canon creatures: collect from Wookieepedia per creature, or will the
  owner supply concept art?
- Shiny palettes: automatic hue shift, or hand-picked per creature?
- Is PixelLab (a paid third-party API) acceptable for the zero-GPU test?
