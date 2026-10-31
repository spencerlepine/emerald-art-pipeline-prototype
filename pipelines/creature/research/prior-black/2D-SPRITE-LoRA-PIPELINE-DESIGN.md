# 2D Sprite LoRA Pipeline: Technical Design

Oct 19, 2026 · @spencer · Status: design final, ready to build

Hardware is out of scope; this document covers components, software, data contracts, and build order.

## 1. Summary

`spritegen` is a pipeline that turns 1 to N concept images and a line of text into game-ready 16-colour battle sprites and item icons in Pokémon Black's style. It has three trained style add-ons (LoRAs) on one SDXL base model, and a deterministic finisher that guarantees exact size and palette. It ends in an exporter that writes the same `PNG + .atlas.ron` format the Rust game already loads.

The pipeline runs in two halves:

- **Once per LoRA (training):** ROM stills → catalog → captions → 1024 px dataset → LoRA checkpoints → checkpoint evaluation.
- **Once per new character (production):** concept images → pre-pixelated init + IP-Adapter refs → SDXL + LoRA → finisher → scorer → contact sheet → human pick → export.

### Locked decisions

| Decision | Choice |
| --- | --- |
| Base model | SDXL 1.0 base |
| LoRAs in scope | **Creatures** (96×96, front + back), **People** (80×80, front only), **Items** (32×32) |
| Out of scope | Overworld walkers, menu icons (derived later by shrink mode), player back sprites, battle animation (Rigger) |
| Training data | Curated ROM sprites (not a 100-character subset) |
| Captions | ROM game data + a local vision-language model (VLM), merged into `captions.csv` and reviewed by a human |
| Palette | Each new character gets its own palette: 15 colours + index 0 transparent, shared by front and back. The finisher also emits an automatic draft shiny palette |
| Interface | Python CLI (diffusers) is the source of truth; ComfyUI workflows reuse the same LoRAs and finisher code |
| Location / integration | `black-rust/tools/spritegen/` (Python). The exporter writes `assets/sprites/<category>/` in the `black extract-sprites` format |

### Corrections to the drafts (verified against the ROM)

| Draft said | Actually true | Effect on design |
| --- | --- | --- |
| People are 64×64 | Trainer battle stills are **80×80** (all 107 sets in ARC 072/064/073) | People canvas 80×80, scale 8 → 640 px |
| People have front + back | Trainers are **front only**. Only the 2 player characters have backs (ARC 064/073: 12 tall multi-part throw sets, up to 128 px) | People LoRA is front-only; no back generation for People |
| 100 characters × 2 views | 712 creature blocks with front + back, 96 of them with female variants; 95 trainer sets; 496 unique item icons | Training sets are about 7× larger; settings below are re-derived |
| `black extract-sprites` gives the sprite | It writes **part atlases** (cells + multi-cells), not the flat still. The flat 96×96 / 80×80 still sits in a separate member with a non-trivial tile order | New Rust command `black extract-sprites stills` (component C0) |
| Key colour `#FF00FF` | Magenta **exactly matches** at least one ROM colour | Key colour `#0000FF`, which is ≥81 RGB units from all 6,646 colours used by ROM sprites and icons |
| Upscale 8× everywhere / 32× | Scale must be a whole multiple of 8 per art pixel (SDXL latent cell = 8 px) and fit 1024 | Creatures 8× (768), People 8× (640), Items 32× (1024) |

## 2. Source assets (verified)

All numbers below come from running the extractor and a probe over `black-rom/files/a/` on Oct 19, 2026.

| Category | ROM source | Still size | Count | Colours / sprite (median, range) | Content box (median) | Placement | In scope |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Creature front | ARC 004, block member 0 | 96×96 4bpp | 712 blocks (+96 female) | 13 (3–15) | 52×52 | Centre x ≈ 47.5; feet y: p10 64, median 72, p90 82 | Yes |
| Creature back | ARC 004, block member 9 | 96×96 4bpp | 712 (+96 female) | 11 (3–15) | 52×52 | same | Yes |
| Shiny palette | ARC 004, block member 19 | 16 colours | 1 per block | n/a | n/a | n/a | Generated as a draft |
| Trainer front | ARC 072, set member 0 (8 members per set) | 80×80 4bpp | 95 sets | 15 (12–15) | 48×72 | Centre x ≈ 39.5; feet y 77–79 (bottom-anchored) | Yes |
| Player back | ARC 064 / 073 | multi-part, up to 72×128 | 6 + 6 sets | 14 | n/a | n/a | No |
| Item icon | ARC 025 (item → icon table in ARM9 at `0x0209EB6C`) | 32×32 4bpp | 627 items → **496 unique** | 9 (2–15) | 20×20 | Centred | Yes |
| Walkers | ARC 049 BTX0 | 32×32 (5,206 frames) / 64×64 (315) | 758 sets (~573 Pokémon, ~185 people) | 16-colour | n/a | n/a | No |
| Menu icons | ARC 007 | 32×32, 2 frames | 715 | n/a | n/a | n/a | No (derived later) |

Palette facts: every sprite is 4bpp, index 0 is transparent, and there are at most 15 visible colours. Creature normal palette = block member 18, shiny = member 19, both shared by the front and back of a block. This is exactly the "one palette per character, shared by both views" rule this pipeline enforces.

### Flat-still decode rules (needed by C0)

The flat still is stored as 1D-mapped 8×8 tiles in DS OAM chunk order. Concatenate the chunks in this order:

| Sprite | Chunk order (x, y, w×h in px) | Tiles | Verified |
| --- | --- | --- | --- |
| Creature 96×96 | (0,0 64×64) → (64,0 32×64) → (0,64 64×32) → (64,64 32×32) | 144 | Visually, 6 species incl. female form |
| Trainer 80×80 | (0,0 64×64) → (64,0 16×32) → (64,32 16×32) → (0,64 32×16) → (32,64 32×16) → (64,64 16×16) | 100 | Visually on 8 sets; best seam score of all 120 legal orders |
| Item 32×32 | single 32×32 cell | 16 | Already handled by `items.rs` |

Also verified: the extractor's **trainer multi-cell compose is broken** (1 cell, fragments; frame 0 = 80×80 garbage). Fix it separately; the pipeline does not depend on it.

### Game data available for captions and grouping

| Data | Source | Notes |
| --- | --- | --- |
| Species name | text bank 70 (ARC 002) | **Never** put into captions (prevents "redraw Pikachu"); used for catalog and novelty reports only |
| Classification ("Seed Pokémon") | bank 260 | Used in captions |
| Pokédex entry | bank 235 (Black), 236 (White) | VLM prompt context only; describes behaviour, not visuals |
| Types, Pokédex colour, egg groups, form index | `black-data` personal (ARC 016) | `color` = low 6 bits of byte 0x21; form-sprite index is a guess (UNVERIFIED) |
| Evolution stage | `black-data` evolution | Derived: basic / stage 1 / stage 2 |
| Trainer class names | bank 191 (105 entries) | Class → sprite set = u8 table at ARM9 `0x020A023C` (106 entries; identity for 0–46, then shifted with duplicates, e.g. 51 Black Belt → 50, 89 Champion → 88; read by `0x0202D5D8`). C0 writes the class name(s) per set from it |
| Item names / descriptions | bank 54 / bank 53 | Bag pocket = ARC 024 `packed` bits 7–10 (0 Items, 1 Medicine, 2 TMs & HMs, 3 Berries, 4 Key Items); in-battle category = bits 11–15 |

## 3. Groups and categorisation

There is one LoRA per group. Inside each LoRA, the **tags** below are the steering vocabulary. They appear in captions at training time and are the knobs in prompts at generation time. Every tag has a deterministic source (ROM data or measured) or a VLM source, written to `catalog.csv` and reviewed once.

### 3.1 Creatures LoRA (`pkbwmon`)

**Inclusion:**

- Blocks 1–711, both views.
- Exclude block 0 (placeholder, 3 colours) and the 2 trailing special sets (egg-like).
- Exclude the 96 female variants: they are near-duplicates. Keep them as an extra eval set for "small variation" prompts.
- Exclude silhouette-identical forms: 2 groups, 7 extra copies per view. Keep one representative.
- Hold out 24 species (both views), stratified by egg group and size class.
- Result: about 680 species × 2 views ≈ **1,360 images**.

| Tag axis | Values | Source |
| --- | --- | --- |
| View | `front view`, `back view` | ROM member |
| Size class | `small` (max side < 40 px), `medium` (40–64), `large` (> 64) | Measured opaque box |
| Body shape | 14 Pokédex shapes: head-only, head+legs, fins, insectoid, quadruped, two wings, multiple bodies, tentacles, head+base, bipedal-tailed, bipedal-tailless, two pairs of wings, serpentine, head+arms | VLM classification, reviewed |
| Body colour | 10 Pokédex colours: red, blue, yellow, green, black, brown, purple, gray, white, pink | ROM personal `color` |
| Type | 17 types (one or two) | ROM personal `types` |
| Archetype | 15 egg groups (Monster, Water 1/2/3, Bug, Flying, Field, Fairy, Grass, Human-Like, Mineral, Amorphous, Dragon, Ditto, Undiscovered) | ROM personal `egg_groups` |
| Stage | `basic`, `stage 1`, `stage 2`, `legendary-like` (Undiscovered egg group + not a baby) | ROM evolution + egg group |
| Visual features | 3 to 8 short noun phrases (e.g. `flame-tipped tail`, `leaf crown`, `armoured shell`) | VLM |
| Classification | e.g. `seed creature` (the word "Pokémon" replaced by "creature") | bank 260 |

### 3.2 People LoRA (`pkbwtrnr`)

**Inclusion:**

- ARC 072 sets 0–94, front only.
- Hold out 6.
- Result: about **89 images**.

This set is small, so tags matter more here.

| Tag axis | Values | Source |
| --- | --- | --- |
| Role group | `story` (leaders, Elite Four, champion, rivals, Team Plasma, protagonists) / `civilian` | Class name (bank 191) via catalog mapping |
| Archetype | sport, martial, academic, worker, outdoors, performer, wealthy, service, youth, villain | Catalog mapping, reviewed |
| Gender | `man`, `woman`, `boy`, `girl`, `pair` (duo classes) | VLM + class name |
| Age | `child`, `teen`, `adult`, `elder` | VLM |
| Outfit | 2 to 5 phrases (e.g. `white lab coat`, `karate gi with black belt`) | VLM |
| Props / vehicle | e.g. `guitar`, `bicycle`, `poké ball in hand` | VLM |
| Pose | `standing`, `action stance`, `crouching`, `arms raised`, `throwing` | VLM |
| Size | `full body` (always); add `wide` if the box is wider than 64 px | Measured |

### 3.3 Items LoRA (`pkbwitem`)

**Inclusion:**

- 496 unique icons (deduplicated by pixel hash; TMs and HMs share icons by type).
- Exclude the blank icon (item 0 → pair 1001/1002).
- Hold out 20.
- Result: about **475 images**.

| Tag axis | Values | Source |
| --- | --- | --- |
| Category | ball, medicine, battle item, berry, TM/HM disc, evolution stone, gem, plate, orb, incense, mail, fossil, wing, valuable, held item, key item | Pocket from `packed` bits 7–10 gives the coarse split (medicine, TM/HM, berry, key item, everything else); name rules on bank 54 refine pocket 0, in order: `Ball$`, `Berry$`, `^TM\|^HM`, `Stone$`, `Gem$`, `Plate$`, `Orb$`, `Incense$`, `Mail$`, `Fossil$\|Plume\|Cover`, `Wing$`, then a reviewed lookup for the rest |
| Main colours | 1 to 3 colour words | Measured (palette Lab clusters → nearest colour name) |
| Object | Short noun phrase (e.g. `spray bottle`, `round fruit with leaf`) | VLM + item description (bank 53) as context |

## 4. Architecture

```
                  ┌──────────────────────── TRAINING (once per LoRA) ───────────────────────┐
 black-rom ─► C0 black extract-sprites stills ─► stills/*.png + manifest.csv
                                                     │
                                                     ▼
              C1 catalog ─► catalog.csv (groups, tags, dedupe, holdout)
                                                     │
              C2 caption (game data + VLM) ─► captions.csv  ◄── human review
                                                     │
              C3 prep ─► dataset/<lora>/*.png + *.txt (1024², key bg)
                                                     │
              C4 train (kohya sd-scripts) ─► models/<lora>/*.safetensors
                                                     │
              C5 eval (fixed prompt grid × checkpoints) ─► reports/<lora>/  ◄── human picks checkpoint
                  └─────────────────────────────────────────────────────────────────────────┘

                  ┌──────────────────────── PRODUCTION (per character) ─────────────────────┐
 jobs.csv + concepts/<name>/
          │
          ▼
  C6 concept prep ─► init_1024.png (pre-pixelated) + refs/ (cropped, bg removed)
          │
          ▼
  C7 generate (SDXL + LoRA + IP-Adapter [+ ControlNet]) ─► raw/<view>_<n>.png (1024²)
          │
          ▼
  C8 finish ─► cand/<view>_<n>.png (indexed, game size) + shiny draft + meta.json
          │
          ▼
  C9 score + contact sheet ─► sheet_<view>.png  ◄── human pick (C10)
          │                     (back view: C7 re-runs conditioned on the picked front)
          ▼
  C11 export ─► black-rust assets/sprites/<category>/<id>_{front,back}{,_shiny}.png + .atlas.ron
                  └─────────────────────────────────────────────────────────────────────────┘

  C12 ComfyUI workflows: same LoRAs; nodes call C6/C8 from the spritegen package.
```

## 5. Components

Each component is one `spritegen` subcommand (Typer CLI) backed by one module. All of them read `config.yaml` and are idempotent: outputs are overwritten deterministically, and seeds are recorded.

### C0. ROM still extractor (Rust, in `black-cli`)

New category on the existing command: `black extract-sprites stills <out> [--rom-root black-rom]`. ROM decoding belongs in the Rust extractor that already parses NARC/NCGR/NCLR (`cmd_extract_sprites/pokemon.rs`, `trainers.rs`), not in Python.

- **Output:** `<out>/stills/{creatures,people,items}/<name>.png` as **indexed PNG** (mode P, 16 entries, index 0 transparent via `tRNS`). Creatures also get `<name>_shiny.pal` (16 × RGB, from member 19).
- **Naming:** `pk_{block:04}_{front|back}[_f]`, `trainer_{set:03}`, `item_{icon:03}`.
- **Decode:** the chunk tables in §2.
- **`manifest.csv`**, one row per still: `name, group, view, block|set|icon, species_id, form, female, types, color, egg_groups, evo_stage, classification, species_name, dex_text, class_names, item_pocket, item_ids, item_name, item_desc, w, h, colors, bbox_x0, bbox_y0, bbox_x1, bbox_y1, opaque_px, shape_hash, pixel_hash`.
- **Tests:**
  - Golden SHA-1 for block 1 front/back and trainer 0, in the existing extractor's test style.
  - Counts: 712 + 712 + 96 + 96 creature stills, 95 trainers, 496 unique icons.
  - Invariant: the content box is non-empty and colours ≤ 15 for every still.

### C1. Catalog and curation (`spritegen catalog`)

- **Input:** `manifest.csv`.
- **Output:** `catalog.csv` (adds `lora, split{train,holdout,eval_extra,excluded}, exclude_reason, size_class, item_category`, plus empty VLM columns).
- **Dedupe:** identical `pixel_hash` → keep the first. Identical `shape_hash` (opaque mask) within a LoRA → keep one (forms and palette swaps).
- **Holdout:** stratified, seeded selection: Creatures 24 species by `egg_group × size_class`, People 6 by archetype, Items 20 by category. Held-out species keep both views together.
- **Human step:** edit `catalog.csv` overrides in `catalog_overrides.csv` (exclude, regroup, fix class mapping). The catalog never edits overrides; it re-applies them on every run.

### C2. Captioner (`spritegen caption --lora <x>`)

- **VLM pass:**
  - Model: Qwen2.5-VL-7B-Instruct, local (transformers).
  - Input image: each still upscaled 4× nearest onto mid-grey.
  - Prompt: "List only visible features. No names, no art-style words. JSON: {shape_class, features[3-8], outfit[], props[], pose, gender, age, object}". The fields asked for depend on the LoRA.
  - Context: classification, dex text, class name or item description.
  - Output: strict JSON, validated with pydantic, retried once on failure, cached by `pixel_hash` in `cache/vlm/`.
- **Merge:** fill a fixed template from catalog fields + VLM JSON → `captions.csv (file, lora, caption, source_hash)`.
- **Templates:**
  - Creatures: `pkbwmon, {view}, {size_class} {shape}, {color} body, {type1}[ and {type2}] type, {archetype}, {stage}, {classification}, {features…}, plain blue background`
  - People: `pkbwtrnr, front view, full body, {age} {gender}, {archetype}, {outfit…}, {props…}, {pose}, plain blue background`
  - Items: `pkbwitem, item icon, {category}, {object}, {colours}, plain blue background`
- **Rules:**
  - Never include species names, "Pokémon", "pixel art", sizes or colour counts. Style lives in the trigger.
  - Back-view captions keep only features visible from behind (the VLM sees the back still).
- **Human step:** review `captions.csv` in a spreadsheet. `prep` refuses to run if any training row has an empty caption.

### C3. Dataset prep (`spritegen prep --lora <x>`)

For each `split=train` row:

1. Load the indexed still.
2. Map index 0 to the key colour `#0000FF`.
3. Nearest-neighbour upscale by `scale`.
4. Centre on a 1024×1024 key canvas at a fixed offset of `(1024 − size·scale)/2`. Every image in a LoRA shares one grid phase; the finisher relies on this.
5. Write `dataset/<lora>/<name>.png` + `<name>.txt` (the caption).
6. Write a dataset TOML for kohya: `resolution=1024`, `enable_bucket=false`, `flip_aug=false`, `random_crop=false`, `color_aug=false`, `num_repeats` from config.
7. **Check:** every PNG is 1024², and RGB colours ⊆ (palette ∪ key).

### C4. Trainer (`spritegen train --lora <x>`)

A thin wrapper that renders a kohya `sdxl_train_network.py` command line from `config.yaml`, logs it to `models/<lora>/run.json`, and streams logs. kohya-ss/sd-scripts is pinned to one commit as an external checkout (`SPRITEGEN_KOHYA_DIR`). Recipes are in §7.

### C5. Checkpoint evaluator (`spritegen eval --lora <x> [--ckpt all]`)

- **Prompt grid** per LoRA, fixed in `eval/<lora>.yaml`:
  - 6 captions from training (memorisation check);
  - 6 held-out captions (generalisation);
  - 6 novel prompts (e.g. `stone golem with mossy shoulders`);
  - for Creatures, the same 6 novel prompts in back view.
  - Fixed seeds (4 per prompt).
- **Per checkpoint:** generate → C8 finish → C9 score.
- **Reports:**
  - Contact sheet with the real holdout sprites alongside.
  - `scores.csv`: mean grid residual, colour count, novelty NN similarity, held-out DINOv2 similarity.
- **Human step:** choose a checkpoint → `config.yaml: loras.<x>.checkpoint`.
- The same command with `--baseline` runs SDXL + the public `nerijs/pixel-art-xl` LoRA + a generic prompt. This is the bar to beat.

### C6. Concept prep (`spritegen concept <job>`)

**Inputs:** `concepts/<name>/main.png` (required, one image) and `ref_*.png` (0 to 9 more).

1. **Subject cut-out:** BiRefNet background removal → alpha → tight crop → square pad.
2. **Pre-pixelated init** (from `main` only):
   1. Lab-space area downscale to the category's typical content box (Creatures: longest side from the `size` field, default 56; People: height 72; Items: 22).
   2. Quantise to 15 colours (median cut in Lab).
   3. Place on the game-size canvas at the category anchor (Creatures: centre x 48, feet y 72; People: centre x 40, feet y 78; Items: centred).
   4. Index 0 → key colour.
   5. Nearest upscale ×`scale`, then onto the 1024 canvas at the prep offset.
3. **IP-Adapter refs:** all cut-outs (main + refs) composited on mid-grey, 224² CLIP crops handled by the IP-Adapter image processor.
4. **Optional ControlNet hint:** lineart of the init (`--control lineart`).

### C7. Generator (`spritegen generate <job> --view front|back --n 8`)

- **Pipeline:** diffusers `StableDiffusionXLImg2ImgPipeline` (front with init) or `StableDiffusionXLPipeline` (back, items without init), plus:
  - the LoRA at weight 0.8–1.0;
  - IP-Adapter Plus (ViT-H) with a list of reference images. Use `ip_adapter_scale` with style-layer blocking off by default; if photo shading leaks, switch to "content only" layer scales (`{"down": {"block_2": [0,1]}}`);
  - optional ControlNet-Union in lineart mode at weight 0.3–0.5.
- **Defaults:**
  - Scheduler: DPM++ 2M Karras, 30 steps, CFG 6.
  - Init strength (denoise): 0.55 for front (allowed 0.45–0.7).
  - IP weight: 0.55 for front, 0.7 for back.
  - Negative prompt: `blurry, gradient, anti-aliasing, soft shading, photo, 3d render, text, watermark, multiple characters, cropped, frame`.
- **Front:** `{trigger}, front view, {prompt}, plain blue background`, with the init + IP refs. Produces N seeds.
- **Back (Creatures only):** `{trigger}, back view, {prompt}, plain blue background`.
  - No init.
  - IP refs = the picked front (8× nearest preview on key) + concept refs.
  - Optional init = the picked front **horizontally mirrored**, as a silhouette-only hint at strength ≥ 0.8 (`--back-init mirror`). Off by default; turn it on if C5 shows backs drifting in size.
- **Items:** text + optional refs, no view word, `--init` optional.
- **Records:** writes `raw/<view>_<seed>.png` and `raw/<view>_<seed>.json` (every parameter, model hashes).

**Plan B for backs (gated by Phase 6):** a paired turnaround LoRA (`pkbwmon_pair`). It trains on front|back sheets (2 × 96 px at 8× = 1536×768, a supported SDXL bucket) built by C3 with `--paired`. At generation it inpaints the right half with the picked front fixed in the left half. The 680 pairs make this viable.

### C8. Finisher (`spritegen finish <png> --lora <x> [--palette-from <front.png>]`)

This is deterministic Pillow + NumPy + scikit-image code. It is the only path from 1024 px to game pixels: it is used by C5, C7, C12 and for hand-drawn art.

1. **Background mask:** flood-fill from the canvas border with ΔE2000 < 20 to the key colour. Pixels near the key colour inside the sprite are kept as colours.
2. **Grid fit:** search phase `(dx, dy) ∈ [0, scale)²` around the prep offset. Optionally search `scale × {0.97, 1.0, 1.03}` for drift (`--scale-search`). Keep the fit with the lowest mean within-cell Lab variance. Record this as `grid_residual`.
3. **Cell vote:** per cell, the cell is transparent if the background fraction is > 0.5; otherwise it takes the **mode** colour of its non-background pixels (never the mean).
4. **Palette:**
   - Front / item: median cut in Lab to ≤ 15 colours, then merge entries with ΔE < 4.
   - Back: nearest-colour map onto the front palette (`--palette-from`). No new colours.
5. **Cleanup:**
   - Remove orphan pixels (opaque with 0 opaque 4-neighbours).
   - Majority filter on single-pixel colour islands where a neighbour colour is within ΔE < 10.
   - Optional `--outline auto`: boundary pixels next to transparency are set to the darkest palette entry of the same hue ramp. Off by default; measured in C5.
6. **Placement:**
   - Crop to the content box and re-place at the category anchor: Creatures centre x 48, keep generated feet y clamped to [64, 82]; People centre x 40, feet y 78; Items centred.
   - Reject the candidate if the content box exceeds the canvas.
7. **Shiny draft (Creatures):** rotate each palette entry's hue in LCh by `shiny.hue_shift` (default +40°). Skip near-greys (C < 8) and the outline entry. Write `<name>_shiny.pal` + preview.
8. **Write:**
   - Indexed PNG (16-entry palette, index 0 transparent).
   - An 8× preview.
   - `meta.json` with palette, grid fit, residual and source.

**Acceptance test (`spritegen roundtrip --lora <x>`):** for every holdout still:

- Degrade it: upscale ×scale → random phase shift ±3 px → Gaussian blur σ 1.5 → JPEG q85 → add 4 extra near-duplicate colours.
- Finish it.
- Pass: ≥ 99% of pixels have the same palette index after palette matching, and the palette size is identical.

### C9. Scorer and contact sheets

The scorer computes these per-candidate metrics and stores them in `meta.json`:

| Metric | Meaning | Used for |
| --- | --- | --- |
| `grid_residual` | Crispness of the raw blocks | Rank (lower is better) |
| `colors` | Palette entries used | Flag < 6 or 15 with many tiny clusters |
| `area_z` | Opaque area z-score vs the category's size class | Flag outliers |
| `outline_ratio` | Share of boundary pixels that are the darkest ramp entry | Compare to the ROM median per LoRA |
| `identity` | DINOv2 cosine(candidate preview, concept main cut-out) | Rank |
| `novelty` | Max DINOv2 cosine to any training still; also reports the nearest name | Flag "too close to <species>" above a threshold (calibrated on holdout) |
| `pair_consistency` (back only) | Palette-usage histogram distance + content-height ratio vs the picked front | Rank backs |

The contact sheet shows every candidate at 1× and 4×, sorted by score with metric badges. It also shows 2 real sprites of the same size class and the concept main image. Flagged candidates are greyed out, not hidden.

### C10. Pick (`spritegen pick <job> --front <n> [--back <n>]`)

- Copies picks to `out/<job>/pick/`.
- Freezes the front palette as the job palette.
- Writes `picks.csv` (job, view, candidate, seed, checkpoint).
- Touch-ups are done in any pixel editor on the indexed PNG. After that, `spritegen finish --verify` checks size, palette ≤ 16 and index 0 transparency.

### C11. Exporter (`spritegen export <job> --id <n> --assets <dir>`)

- **Target:** the `black-game` asset tree (`assets/sprites/<category>/`), which loads `*.png + *.atlas.ron` (`black-game/src/loading/types.rs`).
- **Writes** files in the same shape as the ROM extractor's output:
  - Creatures: `{id:04}_front.png`, `{id:04}_front_shiny.png`, `{id:04}_front.atlas.ron`, plus `_back` equivalents.
  - People: `trainer_{id:03}`.
  - Items: one-cell entries appended to a `custom_items` atlas.
- **Static atlas content:**
  - One frame = the full still, `cells: 1`.
  - One `sequences` entry with a single step.
  - One `multicells` entry with one node at (0,0).
  - Origin chosen to match the ROM anchor for that category.
- **No animation:** the Rigger replaces the atlas later.
- Updates `manifest.json` the way `black extract-assets` does.
- **Golden test:** export a ROM still through C11 and check it lands at the same screen position as the ROM multi-cell frame in `black-game`'s sprite renderer.
- `--dry-run` prints the files it would write. It refuses to overwrite ROM-derived IDs unless `--force`.

### C12. ComfyUI workflows

- `comfy/workflows/{creature_front,creature_back,person_front,item}.json`, using stock nodes + ComfyUI_IPAdapter_plus + ControlNet.
- `comfy/custom_nodes/spritegen_nodes/` exposes `SpritegenConceptPrep` and `SpritegenFinish`, which import the `spritegen` package. There is no second implementation.
- A CI-style test loads each workflow JSON and checks that its node types and model filenames match `config.yaml`.

## 6. Configuration (`config.yaml`)

```yaml
base_model: stabilityai/stable-diffusion-xl-base-1.0
vae: madebyollin/sdxl-vae-fp16-fix
gen_resolution: 1024
key_color: "#0000FF"         # ≥81 RGB from every ROM colour; magenta collides
max_colors: 15               # + index 0 transparent
paths:
  stills: work/stills        # C0 output
  dataset: work/dataset
  models: work/models
  out: work/out
  assets: ../../assets       # black-game asset root for C11
models:
  ip_adapter: h94/IP-Adapter/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors
  ip_image_encoder: h94/IP-Adapter/models/image_encoder
  controlnet: xinsir/controlnet-union-sdxl-1.0
  vlm: Qwen/Qwen2.5-VL-7B-Instruct
  matting: ZhengPeng7/BiRefNet
  embed: facebook/dinov2-base
loras:
  creatures:
    trigger: pkbwmon
    sprite_w: 96
    sprite_h: 96
    scale: 8                 # 768 px, 128 px margin
    views: [front, back]
    anchor: {cx: 48, feet_y: 72, feet_clamp: [64, 82]}
    holdout: 24
    checkpoint: null         # set after C5
    shiny: {hue_shift: 40}
  people:
    trigger: pkbwtrnr
    sprite_w: 80
    sprite_h: 80
    scale: 8                 # 640 px, 192 px margin
    views: [front]
    anchor: {cx: 40, feet_y: 78}
    holdout: 6
    checkpoint: null
  items:
    trigger: pkbwitem
    sprite_w: 32
    sprite_h: 32
    scale: 32                # 1024 px, no margin
    views: [none]
    anchor: {center: true}
    holdout: 20
    checkpoint: null
generate:
  sampler: dpmpp_2m_karras
  steps: 30
  cfg: 6.0
  lora_weight: 0.9
  front: {denoise: 0.55, ip_weight: 0.55}
  back: {ip_weight: 0.7, init: none}       # none | mirror
  n: 8
```

Rule for any future size: `scale` = the largest multiple of 8 with `max(w,h)·scale ≤ 1024`, centred on the key canvas.

## 7. Training recipes

kohya `sdxl_train_network.py`, `network_module=networks.lora`. Common settings:

- Precision and memory: `mixed_precision=bf16`, `cache_latents`, `gradient_checkpointing`, SDXL fp16-fix VAE.
- Loss and noise: `min_snr_gamma=5`, `noise_offset=0`.
- Augmentation off: no flip, crop or colour aug, no bucketing.
- Text encoder: `network_train_unet_only`. Turn text-encoder training on at 5e-5 only if the trigger doesn't take.
- Checkpoints: one save per epoch, `save_model_as=safetensors`.

| | Creatures | People | Items |
| --- | --- | --- | --- |
| Images | ~1,360 | ~89 | ~475 |
| Rank / alpha | 32 / 16 | 16 / 8 | 16 / 8 |
| Optimizer / LR | AdamW8bit, 1e-4 (cosine, 100 warmup) | same | same |
| Batch × repeats | 4 × 1 | 2 × 4 | 4 × 1 |
| Epochs (≈ steps) | 8 (~2,700) | 10 (~1,800) | 12 (~1,400) |
| First alternative | Prodigy, LR 1.0, d_coef 1 | Prodigy | Prodigy |

Pick checkpoints with C5:

- Too early: generic pixel art and soft blocks (high `grid_residual`).
- Too late: novel prompts return training species (high `novelty`).
- Take the last checkpoint before novelty rises.

If People underfits at 89 images, retrain it with 10% of Creatures front images captioned `pkbwmon` as regularisation. This is an experiment, not a default.

## 8. Directory layout and data contracts

```
black-rust/tools/spritegen/
  pyproject.toml            # uv project, Python 3.12, pinned deps
  config.yaml
  src/spritegen/
    cli.py                  # Typer entry: catalog caption prep train eval concept generate finish roundtrip score pick export
    config.py               # pydantic models for config.yaml
    catalog.py  caption.py  prep.py  train.py  evaluate.py
    concept.py  generate.py  finish.py  palette.py  score.py  sheet.py  export.py
  eval/{creatures,people,items}.yaml
  comfy/workflows/*.json
  comfy/custom_nodes/spritegen_nodes/
  tests/                    # roundtrip, palette, export golden, config, workflow lint
  catalog_overrides.csv     # human edits (tracked)
  captions.csv              # reviewed captions (tracked)
  jobs.csv                  # production jobs (tracked)
  concepts/<job>/main.png, ref_*.png
  work/                     # untracked: stills, dataset, models, cache, out
```

| File | Columns / content |
| --- | --- |
| `manifest.csv` (C0) | See C0 |
| `catalog.csv` (C1) | manifest + `lora, split, exclude_reason, size_class, item_category, shape_class, archetype, gender, age` |
| `captions.csv` (C2) | `file, lora, caption, source_hash` (stale rows are flagged when the still changes) |
| `jobs.csv` | `job, lora, prompt, size_class, views, denoise, ip_weight, n, seed, control` (blank = config default) |
| `out/<job>/raw/*.json`, `cand/*.meta.json` | Every generation parameter, model and LoRA SHA-256, seed, finisher fit and scores |
| `picks.csv` | `job, view, candidate, seed, checkpoint, touched_up` |

Production runs: `spritegen run jobs.csv` does concept → front generate → finish → score → sheet for every job. After `pick --front`, `spritegen run jobs.csv --view back` does the backs.

## 9. Software stack

| Layer | Choice | Licence / note |
| --- | --- | --- |
| Runtime | Python 3.12 via `uv`. The system Python 3.15 is too new for torch wheels | n/a |
| Core ML | torch, diffusers, transformers, accelerate, peft, safetensors | Apache-2.0 / BSD |
| Training | kohya-ss/sd-scripts (pinned commit), bitsandbytes, prodigyopt | Apache-2.0 / MIT |
| Base + VAE | SDXL 1.0 base; sdxl-vae-fp16-fix | CreativeML OpenRAIL++-M; MIT |
| Image prompt | h94 IP-Adapter Plus SDXL (ViT-H) | Apache-2.0 |
| Pose (optional) | xinsir controlnet-union-sdxl-1.0 | Apache-2.0 |
| Captioning VLM | Qwen2.5-VL-7B-Instruct | Apache-2.0 |
| Matting | BiRefNet | MIT |
| Embeddings | DINOv2-base | Apache-2.0 |
| Image / colour | Pillow, NumPy, scikit-image (Lab, ΔE2000) | BSD-style |
| CLI / config | Typer, pydantic, PyYAML | MIT |
| Tests | pytest | MIT |
| UI | ComfyUI + ComfyUI_IPAdapter_plus | GPL-3.0. Kept in a separate install; our custom node is only imported by it |
| ROM side | Rust `black-cli` (`nds-rom` crate) | Existing |
| Baseline only | nerijs/pixel-art-xl | Check licence; not shipped |

The ROM art and anything trained on it are Nintendo's. The models and outputs stay inside this personal fan project.

## 10. Build plan

Each phase ends in a check. A failed check stops the line.

| Phase | Builds | Done when |
| --- | --- | --- |
| 0. Stills | C0 (Rust) + tests | Counts and golden hashes pass; a contact sheet of 40 random stills per group looks correct |
| 1. Finisher | C8 + `roundtrip` + `palette.py` | Roundtrip ≥ 99% index match on all holdout stills for all 3 LoRAs |
| 2. Catalog + captions | C1, C2, review pass | Every train row has a reviewed caption; holdouts frozen and committed |
| 3. Prep + baseline | C3, C5 `--baseline`, C9 sheets | Datasets pass checks; baseline sheets saved as the bar to beat |
| 4. Train Items → Creatures → People | C4, C5 | Per LoRA: in a blind side-by-side at 1×, a reviewer can't reliably separate held-out real sprites from generated ones for the held-out prompts (≤ 60% correct over 20 pairs) and novelty flags < 10% |
| 5. Concept → front | C6, C7 front, C10 | 5 held-out characters per LoRA, drawn as concepts, come back recognisable in ≥ 1 of 8 candidates |
| 6. Front → back (Creatures) | C7 back, `pair_consistency` | Held-out backs match their fronts in ≥ 1 of 8; else build Plan B (paired LoRA) |
| 7. Export | C11 + golden test | A ROM still exported through C11 renders at the identical position in `black-game` |
| 8. ComfyUI | C12 | All 4 workflows reproduce a CLI candidate bit-exactly for the same seed and settings |
| 9. Production | `spritegen run` | First batch of new characters exported |

## 11. Risks

| Risk | Mitigation |
| --- | --- |
| Creatures LoRA memorises species | No names in captions; `novelty` flag; earlier checkpoint; shape-hash dedupe |
| People LoRA too thin (89 images) | Rich VLM tags; rank 16; optional regularisation mix; Prodigy |
| Backs drift from fronts | Front as IP ref, palette lock, `pair_consistency` ranking, mirror-init option, Plan B paired LoRA |
| Photo shading leaks from concepts | Pre-pixelated init, IP content-only layer scales, negative prompt, finisher palette lock |
| Grid drift → double-width pixels | Fixed prep offset, phase + scale search, `grid_residual` ranking |
| Several classes share one sprite set (e.g. The Riches, GAME FREAK) | C0 lists all class names per set; the VLM gives the visual tags |
| VLM hallucinated features | Fixed JSON schema, cache, human review before `prep` |
| Exported atlas misplaced in game | C11 golden test against a ROM still |
| Key colour bleeds into sprites | `#0000FF` chosen by measured distance; border flood-fill, not global colour match |

## 12. Remaining unknowns (none block Phase 0–3)

- [ ] Exact `origin` convention for a one-cell static atlas. Settle it with the C11 golden test against `black-game`'s renderer.
- [ ] `form_sprite_index` meaning in personal data (UNVERIFIED). This affects only form labelling in the catalog.
- [ ] Trainer multi-cell compose bug in `trainers.rs` (separate fix; not on this pipeline's path).

Resolved on Oct 20, 2026 (evidence in the checklist's Unknowns table): the trainer class → sprite set table (ARM9 `0x020A023C`) and the item pocket bits (ARC 024 `packed` bits 7–10).

## Appendix A. Evidence

- **Extractor runs:** `black extract-sprites {pokemon,trainers,overworld,items}`.
  - pokemon: 712 blocks / 1,618 sets, of which 1,616 species sets + 2 special.
  - trainers: 107 sets.
  - overworld: 758 sets / 5,521 frames.
  - items: 627 items.
- **Still decode** verified by a probe over `nds-rom` (`Ncgr::tile_pixels`, 1D chunk order above). Contact sheets were checked visually for Creatures (blocks 1, 3 female, 6, 644) and trainers (sets 0, 10, 20, 30, 40, 50, 60, 94).
- **Statistics** (colours, content boxes, placement percentiles, duplicate hashes, key-colour distances) were computed over all decoded stills and the item atlas.
- **Text banks** via `black msg dump black-rom/files/a/0/0/2`: 70 species names, 260 classifications, 235/236 dex entries, 191 trainer classes, 54 item names, 53 item descriptions.
- **Code references:**
  - `black-rust/crates/black-cli/src/cmd_extract_sprites/{pokemon,trainers,items,overworld}.rs`
  - `black-rust/crates/black-data/src/{personal,items}.rs`
  - `black-rust/crates/black-game/src/loading/types.rs`
