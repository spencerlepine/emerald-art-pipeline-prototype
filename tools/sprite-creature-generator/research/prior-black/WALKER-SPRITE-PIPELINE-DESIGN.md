# Walker Sprite Pipeline: Technical Design

Oct 19, 2026 · @spencer · Status: design final, ready to build

Companion to `2D-SPRITE-LoRA-PIPELINE-DESIGN.md` (the "battle doc"). It covers overworld walker sprites for people and creatures, including the 64 px sets and the story/player specials. It reuses the battle doc's `spritegen` package. Component IDs `C0`–`C12` refer to that doc; the new walker components are `W0`–`W12`. Hardware is out of scope.

## 1. Summary

A walker is a set of 1 to 32 frames at 32×32 or 64×64 that share one 16-colour palette. The frames show a character from 3 or 4 directions, standing and stepping, plus optional action frames. The hard part is **drawing 3 or 4 consistent views**. The walk animation itself is small: a step frame is the stand frame shifted 1–2 px with about **16–20% of pixels changed** (feet, legs, arms). The pipeline therefore splits the problem in two:

1. **Keyframe LoRA (diffusion):** draws all direction stand frames at once, as one sheet. When a character also has a battle sprite, that sprite sits fixed beside the sheet as a reference.
2. **Animator (small native-resolution model):** turns each stand frame into its step/run frames by predicting palette indices directly. Output is pixel-exact and palette-locked by construction.

Specials (bike, surf, fishing, item-get, PC, cut-in, dance, story-NPC actions, legendary actions) come from a third component:

3. **Template retargeting (deterministic + light diffusion):** takes the ROM's special frames as templates, maps their colours to the new character by material, transplants the new character's head, and runs a low-strength inpaint clean-up.

### Locked decisions

| Decision | Choice |
| --- | --- |
| Scope | All walker kinds: standard people and creatures (32 px and 64 px), player kit, story-NPC extras, legendary 64 px sets, static objects, effects |
| Battle → walker | Every new battle character automatically gets a walker in the same job (`spritegen run`) |
| Frame generation | Diffusion only for direction keyframes; walk/run frames come from the animator; specials come from template retargeting |
| Not used | Per-frame diffusion (flickers), 3D model → render (doesn't look hand-pixelled at 32 px; creature rigging unreliable), multi-view diffusion (wrong chibi proportions) |
| Palette | Walker palette ⊆ the character's battle palette (≤ 15 + transparent). For creatures, the shiny walker palette is derived index-by-index from the battle shiny palette |
| Package | Same `black-rust/tools/spritegen/`, subcommand group `spritegen walker …`; same config, finisher, scorer, pick and export conventions |

### Corrections to earlier docs (verified Oct 19, 2026)

| Earlier claim | Actually true |
| --- | --- |
| Checklist #8: "Walker frame timing = ARC 069 (29 files)" | ARC 069 is 29 **BTA0 map-texture SRT animations** (`sea_mizu1`, `kawa01a`, `ue_grass01`…), not walker data. Walker frames come from the **anime tables in overlay 21** (directory `0x021D7F68`), selected by byte 9 of the ARC 048 OBJ record (§2) |
| "mostly 32×32 with 6–12 frames" | True for 677 of 758 sets. The other 81 are 64 px creatures, specials, objects and effects (§2) |
| Walker = one palette | Creature walkers (`poke*`) ship **2 palettes** (`_p1` presumably shiny, UNVERIFIED); people walkers have 1 |

## 2. Source assets (verified)

Source: ARC 049. Members 0–5 are BMD0 quad models; members 6–763 are 758 BTX0 texture sets, one per character, with 16-colour textures (index 0 transparent). `black extract-sprites overworld` writes `<member>_<kind>.png` (+ `_p1.png`) and `.atlas.ron` (`frame_size`, `columns: 8`, frames named `t4x4<kind>.N` in texture order).

| Kind | Sets | Size | Frames | Palettes | Colours (median) | Content box h×w (median) | Feet y (median) | What it is (from visual check) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pokeflip` | 394 | 32 | 6 | 2 | 12 | 20×19 | 29 | Creature, symmetric: up ×2, down ×2, side ×2 (right = mirrored left) |
| `pokeflip` | 31 | 64 | 6 | 2 | 14 | 39×26 | 61 | Large creature, same layout |
| `pokenflip` | 141 | 32 | 8 | 2 | 12 | 19×17 | 29 | Creature, asymmetric: up, down, left, right × 2. Right differs from mirrored left by a median of **11%** of pixels |
| `x15poke` | 7 | 64 | 15 | 1 | 13 | 53×61 | 62 | Legendary: idle/walk frames + action frames + effect-line frames |
| `flip` | 65 | 32 | 7 | 1 | 15 | 28×18 | 30 | Person, symmetric: up ×2, down ×2, side ×3 |
| `nflip` | 77 | 32 | 12 | 1 | 14 | 30×18 | 31 | Person, asymmetric: 4 directions × 3 (stand, step A, step B) |
| `hero` | 2 | 32 | 32 | 1 | 15 | 27×19 | 30 | Player (male / female): walk + run + extras |
| `cycle` | 2 | 32 | 16 | 1 | 15 | 28×19 | 30 | Player on bike |
| `swim` | 2 | 32 | 4 | 1 | 15 | 23×23 | 27 | Player surfing, 4 directions |
| `hurahero` | 2 | 32 | 16 | 1 | 15 | 27×22 | 30 | Player spin/dance action |
| `pchero` / `reporthero` / `gethero` / `cutinhero` | 2 each | 32 | 5 / 2 / 2 / 4 | 1 | 15 | ~26×20 | 30 | Player at PC, saving/report, item get, cut-in pose |
| `fishgirl` | 2 | 64 | 12 | 1 | 15 | 29×19 | 46 | Player fishing (rod extends beyond 32 px) |
| `pcwoman` | 2 | 32 | 9 | 1 | 14 | 28×20 | 30 | Nurse: 4-direction walk + bow |
| `x14` / `x20` / `x22` | 1 / 5 / 1 | 32 | 14 / 20 / 22 | 1 | 15 | ~30×22 | 31 | Story NPCs: 12-frame walk + action frames |
| `xocell` | 15 | 32 | 1 | 1 | 11 | 15×18 | 30 | Static field objects (e.g. tree) |
| `spider` | 1 | 32 | 4 | 1 | 11 | 32×32 | 31 | Field effect (web, dust clouds) |

Totals: 758 sets, 5,521 frames: about 573 creature sets, about 169 people sets, 16 object/effect sets.

### Measured motion facts (drive the animator design)

| Kind | Stand → step: pixels changed | After best ±2 px vertical shift |
| --- | --- | --- |
| `pokeflip` | 22% | 19% |
| `pokenflip` | 16% | 16% |
| `flip` | 66% | 19% (a step frame is mostly a 1–2 px bob + legs) |
| `nflip` | 67% | 41% (measured with an assumed pairing; recompute in Phase 0 with the decoded table below) |

### Frame table (decoded from code)

Each ARC 048 OBJ record (799 × 0x1C) holds the walker's draw data:

| Byte | Meaning |
| --- | --- |
| b3 | Draw proc (table `0x021D770C`) |
| b7 | Quad scale index (`0x021D75D0`: 0 = 32 px, 2 = 64 px) |
| b8 | Resource class: `0x15` Pokémon, `0x16` NPC, `0x17` player, `0x1E`/`0x1F` 64 px |
| b9 | **Anime table id** |
| halfword 8 | ARC 049 member (the texture set) |

- **Lookup:** `0x0219C6B8` → `0x0219D3E4` reads the anime-table directory at **`0x021D7F68`** (overlay 21, 8-byte `{ptr, count}` entries).
- **Sequence format:** `(u16 frame, u16 wait)` pairs.
  - Frame bit `0x4000` = draw horizontally mirrored.
  - `0x3FFC` = loop; `0x3FFF` = hold.
- **Sequence index:** 0–3 = stand (up, down, left, right); `4 + 4k + dir` = walk at speed k (waits 16/8/4/2/1…).
- **Walk cycle:** step, stand, step2, stand.

| Kind (b9) | Up (stand; steps) | Down | Left | Right |
| --- | --- | --- | --- | --- |
| `flip` (5) | 0; 1, 1m | 2; 3, 3m | 4; 5, 6 | 4m; 5m, 6m |
| `nflip` (6) | 0; 1, 2 | 3; 4, 5 | 6; 7, 8 | 9; 10, 11 |
| `pokeflip` (0x0D) | loop 0, 1 | 2, 3 | 4, 5 | 4m, 5m |
| `pokenflip` (0x0E) | 0, 1 | 2, 3 | 4, 5 | 6, 7 |

`m` = the same texture drawn mirrored at runtime. Pokémon kinds have only 4 always-looping sequences, with no stand/walk split; the down cycle is `2:5 3:10 2:5`.

Specials:

| Kind | Layout |
| --- | --- |
| `hero` (table 1) | `nflip` layout on frames 0–11; run on 12–23 (sequences 40–47); 24–31 used by other tables |
| `cycle` (7) | Stand 12–15; ride uses the `nflip` layout on 0–11 |
| `swim` (4) | 0, 1, 2, 2m |
| `x14` (23), `x20` (21/24/26/27/28), `x22` (25) | `nflip` layout + 1–3 action sequences on frames 12+ |
| `pcwoman` (12) | `flip` layout + bow `2,7,8,7,2` |
| `gethero` (9), `pchero` (10), `reporthero` (11), `cutinhero` (16), `hurahero` (17), `fishgirl` (15), `spider` (19) | 1–16 short sequences each; `fishgirl` = 4 directions × 4, right mirrored |
| `x15poke` (18/22/29) | Idle/action loops, e.g. `0..3,1` and `4,5,6,14,6,5` |
| `xocell` (8) | Static frame 0 |

This matches the extracted atlases `013_flip`, `018_nflip`, `400_pokeflip`, `590_pokenflip` and `006_hero`.

## 3. Kits: what a new character gets

A **kit** is the frame layout a job produces. It maps 1:1 to a ROM kind, so exported sets are native to the game.

| Kit | ROM kind | Frames | Default for | Frame sources |
| --- | --- | --- | --- | --- |
| `person` | `flip` (sym) / `nflip` (asym) | 7 / 12 | Every new trainer / NPC | Keyframes (W6) + animator (W7) |
| `creature` | `pokeflip` (sym) / `pokenflip` (asym), 32 or 64 px | 6 / 8 | Every new creature | Keyframes + animator |
| `legendary` | `x15poke` | 15 | Creatures flagged legendary | Keyframes + animator + retarget for actions (W8) + effect frames copied from template |
| `player` | `hero` + `cycle` + `swim` + `hurahero` + `pchero` + `reporthero` + `gethero` + `cutinhero` + `fishgirl` | 93 over 9 sets | New protagonists | Keyframes + animator (walk/run) + retarget (everything else) |
| `story_npc` | `x14` / `x20` / `x22` / `pcwoman` | 9–22 | Flagged story NPCs | Keyframes + animator (walk) + retarget (actions) from the nearest template |
| `object` | `xocell` | 1 | Static props | Keyframe LoRA in object mode, single view |
| `effect` | `spider` | 4 | Field effects | Template recolour only |

Automatic choices (overridable in `jobs.csv`):

- **Symmetric vs asymmetric:**
  - Generate all 4 directions; finish them; compute `asym = diff(mirror(left), right) / union`.
  - `asym > τ` → `nflip` / `pokenflip`; otherwise `flip` / `pokeflip`, and the right view is dropped.
  - τ is calibrated on the ROM: the threshold that best separates `pokeflip` from `pokenflip` sets (start at 0.08).
- **32 vs 64 px (creatures):** from the picked battle front's content box. Threshold `size64_min` is calibrated on the paired ROM data (W2) as the battle box size above which ROM walkers are 64 px.
- **Legendary flag:** inherited from the battle job (stage tag `legendary-like` in the battle catalog) or set by hand.

## 4. Architecture

```
            ┌──────────────── ONE-TIME (per model) ────────────────┐
black-rom ─► W0 black extract-sprites overworld --indexed ─► walkers/<set>/frame_NN.png (indexed) + manifest
                  │
                  ├─► W1 frame-map labelling ─► walker_layouts.yaml   (slot meaning per kind)
                  ├─► W2 battle↔walker pairing ─► walker_pairs.csv     (creature species, trainer class)
                  ├─► W3 catalog + captions (C1/C2 extended)
                  │
                  ├─► W4 sheet prep ─► dataset/walkers/*.png + .txt (1536×768 paired sheets)
                  │        └─► W5 train Keyframe LoRA (C4) ─► eval (C5)
                  │
                  ├─► W7a animator dataset (stand → slot pairs) ─► W7b train animator ─► eval
                  │
                  └─► W8a template library (special frames + material maps + prop masks)
            └───────────────────────────────────────────────────────┘

            ┌──────────── PER CHARACTER (chained after battle job) ───────────┐
picked battle front (or concept only)
   ─► W6 keyframe generate: inpaint right panel, battle panel fixed ─► finish (multi-panel) ─► pick
   ─► W7 animator: stand frames → step/run slots
   ─► W8 retarget specials (kit-dependent)
   ─► W9 assemble kit: layout, mirroring, palettes (normal + shiny), walk GIFs
   ─► W10 score + contact sheet ─► pick per group
   ─► W11 export ─► assets/sprites/overworld/<id>_<kind>{,_p1}.png + .atlas.ron; characters.csv link
            └──────────────────────────────────────────────────────────────────┘
```

## 5. Components

### W0. Indexed walker export (Rust, `black-cli`)

Add `--indexed` to `black extract-sprites overworld`. It writes `walkers/<member>_<kind>/frame_{NN}.png` as **indexed PNG** (palette 0; index 0 transparent) and `palette_{0,1}.pal`, alongside the existing RGBA atlases.

Indices must come from the BTX0 data (`overworld.rs` already has `Tex.pixels` as palette indices), not from reverse colour lookup: palettes can contain duplicate colours.

It also writes `walkers/manifest.csv`, one row per set: `set, member, kind, frame_size, frames, palettes, colors, bbox per frame, shape_hash`.

Tests:

- Counts: 758 sets, 5,521 frames.
- Every frame index is < 16.
- RGBA atlas == indexed frames rendered with the palette (byte-identical).

### W1. Frame map (`walker_layouts.yaml`)

This defines each slot of each kind: `{index, dir: up|down|left|right|none, pose: stand|step_a|step_b|run_*|action:<name>|effect, mirror_of: <index>|null, runtime_mirror: bool}`.

Two sources, in this order:

1. **Code (primary, located):** `spritegen walker layouts --from-rom` decodes the anime-table directory at `0x021D7F68` in `OVY_21.sbin` (§2 Frame table) for every anime-table id referenced by ARC 048 byte 9, and writes the YAML, including frame waits and mirror flags.
2. **Labelling (only for action sequences whose pose names aren't obvious, ~60 frames):** `spritegen walker label` renders one contact sheet per kind (2–3 exemplar sets, frames numbered) next to a pre-filled YAML of the visually inferred layout. A human confirms or edits it. This is labelling, not drawing.

Validation (`spritegen walker check-layouts`):

- Every set of a kind has the declared frame count.
- In `*nflip` sets, `right` vs `mirror(left)` diff is in 5–30%. In `flip` sets, the side frames are self-consistent.
- Stand → step diff after bob is < 45% for every walk pair.

### W2. Battle ↔ walker pairing (`walker_pairs.csv`)

The pairs are needed to train battle-conditioned keyframes and to evaluate battle→walker fidelity.

- **Creatures:**
  - **Deterministic rule (no matching needed):** OBJ code `0x1000 + k` → ARC 049 member `198 + k`, in national dex order **#1–493** with each extra form or female variant right after its base (73 extras). Gen 5 species (#494–649) have no standard walker; the 9 low-code creature records (codes 121, 160, 161, 211–214, 221, 222) are the 64 px / `x15poke` sets. That gives about 566 creature pairs for free.
  - Verification only: DINOv2 cosine between the battle front still (C0) and the walker down-stand frame, plus Lab palette similarity. Flag pairs below threshold for a contact-sheet check of the exact middle offsets.
  - Gen 5 battle species stay unpaired (`no reference` sheets are not needed for them; they simply have no walker target).
- **People:** the game has **no** trainer-class → walker table. Each NPC's look is the OBJ code in its event record (ARC 125), independent of its battle class. So trainer battle sets (95) ↔ `flip`/`nflip` NPC sets (142) are paired by matching:
  - Score: DINOv2 cosine + Lab palette similarity.
  - Assign: Hungarian assignment.
  - Review: a human checks matches below the confidence threshold.
  - Seed: class names (bank 191) and the class → battle-set table (ARM9 `0x020A023C`, see the battle doc). Many NPC walkers have no battle sprite and stay unpaired.
- **Output:** `walker_set, battle_still, confidence, reviewed`.
- **Target:** all ~566 creature pairs verified (flags reviewed) and ≥ 60 reviewed people pairs.

### W3. Catalog and captions (extends C1/C2)

- **Splits:**
  - `train`: all character sets.
  - `holdout`: 20 creature sets + 8 people sets, all **paired**, stratified by kind.
  - `template`: all specials, also used for training.
  - `object`/`effect`: the 16 non-character sets.
- **VLM** (same model and cache as C2):
  - Input: the 4 stand frames upscaled 6×.
  - JSON: `{subject: person|creature|object, features[3-8], outfit[], props[], colours[]}`.
- **Caption template:** `pkbwwalk, {person|creature|object}, overworld sprite sheet, {kit_kind}, {features…}, {ref_mode}, plain blue background`.
  - `ref_mode` = `with battle reference` / `no reference`.
  - Same rules as C2: no names, no style words.

### W4. Sheet prep (`spritegen walker prep`)

All sheets are **1536×768** RGB on key `#0000FF`, built so every art pixel is a whole multiple of 8 px in its own panel.

```
┌──────────── 768 ────────────┬──────────── 768 ────────────┐
│ BATTLE PANEL                │ WALKER PANEL (2×2 views)    │
│ battle front still @8×      │  up      │  down            │
│ (creature 96 → 768,         │──────────┼──────────        │
│  person 80 → 640 centred)   │  left    │  right           │
│ or all key colour           │ 32 px @8× = 256 per view,   │
│ ("no reference")            │ 512² grid centred (128 pad) │
└─────────────────────────────┴─────────────────────────────┘
```

- **64 px sets** (31 `pokeflip` + 7 `x15poke` + 2 `fishgirl`): views at **6×** (384 px each, 768² grid with no padding). 6 is not latent-aligned; the finisher uses the known scale and phase search (C8 step 2). This is accepted for 40 sets rather than a second resolution.
- **Views:**
  - Stand frames per W1.
  - For runtime-mirrored kinds, `right` = mirrored `left` (the game does the same).
  - Creature sets with only 3 directions do the same.
- **Unpaired sets:** battle panel left as key colour with caption `no reference`. At generation, the same LoRA works from concept/IP refs alone.
- **Object sets:** a single view in the `down` slot; the other slots are key colour.
- **Count:** about 742 sheets (character sets) + 15 object sheets.

### W5. Keyframe LoRA (`pkbwwalk`)

Uses C4 with resolution `1536,768`, no bucketing, no flips (mirroring is semantic here), rank 32 / alpha 16, AdamW8bit 1e-4, batch 2, about 8 epochs (~3,000 steps), and one checkpoint per epoch.

C5 eval grid:

- 10 paired holdouts generated from their battle still: compare with the real walker.
- 10 novel concepts without reference.
- 5 objects.

Track per checkpoint:

- `view_consistency`: DINOv2 cosine between the 4 views of one sheet, compared with the ROM median.
- `ref_fidelity`: down view vs real walker, holdouts only.
- `novelty`: as in C9.
- `grid_residual`: as in C9.

### W6. Keyframe generation (`spritegen walker keyframes <job>`)

- **With battle sprite (chained job):** SDXL inpaint pipeline.
  - Init: the sheet with the **picked battle front** (finished, indexed → key bg → 8×) in the left panel; right panel key colour.
  - Mask: the right panel only.
  - Prompt: `pkbwwalk, {person|creature}, overworld sprite sheet, {kit_kind}, {battle prompt features}, with battle reference, plain blue background`.
  - IP-Adapter refs: the battle front + concept refs, weight 0.5.
  - Defaults: N = 8, denoise 1.0 inside the mask, CFG 6, 30 steps.
- **Concept only:** same, with the left panel key colour and `no reference`, plus C6's pre-pixelated init for the down view slot if available.
- **Fix-a-view mode:** `--keep down=<png>` puts an accepted view into its slot and masks only the others. Used to iterate a single bad view.
- **Finisher (multi-panel mode):** C8 run per view panel with the known scale and offset, then one **shared palette** across all 4 views:
  - With battle: palette = nearest subset of the battle palette (≤ 15 entries used).
  - Without: median cut over the 4 views pooled.
  - Placement: centre x 16 (32 px) / 32 (64 px); feet y anchored to the per-kind ROM median (§2) ± 1.
- **Then:**
  - Compute `asym` → choose sym/asym kind (§3).
  - Contact sheet with the 4 views + an auto walk preview (stand frames only); pick (C10).

### W7. Animator (`spritegen walker animate`)

A small model that maps a stand frame to the other frames of the same direction. It is trained only on ROM walkers and works in **palette-index space**.

**Dataset (W7a):** from W1, every `(stand frame of dir d) → (slot s in dir d)` pair for walk and run poses.

- Sizes: about 1,275 pairs (`pokeflip`) + 564 (`pokenflip`) + 260 (`flip`) + 616 (`nflip`) + about 120 (hero/cycle/x-NPC walk/run) + 64 px sets ≈ **2,900 pairs**.
- Holdout: the same sets as W3.
- Augmentations:
  - Random permutation of indices 1–15 (forces structure over colour IDs).
  - Horizontal mirror of side directions (left ↔ right swap).
  - ±1 px translation of the pair.
  - 32 px frames centred into a 64 px canvas for a shared 64×64 input size.

**Model (W7b):**

- Inputs, as channels:
  - one-hot(16) of the source stand frame;
  - one-hot(16) of the other stand frames of the same character (3 × 16, giving body context);
  - embeddings for `kind`, `dir` and `target slot`, applied via FiLM.
- Architecture: U-Net, 4 levels, ~8M parameters, 64×64 input.
- **Residual head** (enforces identity):
  1. `bob`: 5-way classification of the global vertical shift (−2…+2), plus a 3-way horizontal shift.
  2. `change mask`: per-pixel probability that the pixel differs from the shifted source.
  3. `index`: 16-way logits for changed pixels.
- Output frame = shifted source where mask < 0.5; otherwise the argmax index, restricted to indices used by the character (a palette-subset mask on the logits).
- Loss: CE on bob + BCE (mask, positive weight from the measured changed-pixel ratio) + CE on index over changed pixels; edge pixels weighted ×2.
- Training: plain PyTorch, AdamW 3e-4, cosine, ~30k steps at batch 64, seeded.

**Upgrade path, only if gates fail:** a MaskGIT-style masked-token model over the same index grid. It handles multi-modal leg poses that a deterministic U-Net averages. The inputs, outputs and residual formulation stay the same.

**Fallback per frame:** the rule rig.

- Apply the template's bob.
- Swap the lower-body band: rows below the waist line found via the W8 material map, taken from the nearest ROM set of the same kind (DINOv2 on the stand frame), recoloured through the material map.
- Used when the animator's mask covers > 50% of the body or the frame fails a check.

**Checks on every output:** palette ⊆ the character palette; content box height within ±2 px of the stand frame; head region (top 40% of content) identical to the shifted stand frame for people kits.

### W8. Template retargeting for specials (`spritegen walker retarget`)

This produces any frame whose pose the animator was not trained on: player actions, story-NPC actions, legendary actions.

**Template library (one-time, W8a), for each special template set:**

- **Material map:** label each palette index with one of `outline, skin, skin_shadow, hair, hair_shadow, hat, hat_shadow, top, top_shadow, bottom, shoes, accessory, eye, prop_*, effect`. About 25 palettes × 16 entries. The VLM drafts the labels; a human confirms.
- **Prop masks per frame:** pixels whose material is `prop_*` or `effect`, i.e. the bike, rod, surf mount, effect lines. Derived from the material map, so no painting.
- **Head box per frame:** the head region (`hair`/`hat`/`skin` above the neck line) and its anchor offset relative to the matching-direction stand frame.

**Per character and special frame:**

1. **Material correspondence.** Align the new character's down-stand frame with the template's down-stand frame (both chibi, same canvas). Count index co-occurrence, then solve a Hungarian assignment from template materials to new palette indices. Unmatched materials take the nearest Lab colour in the new palette.
2. **Recolour.** Template frame → material → new index. Prop/effect pixels keep the template's colours, which are appended to the palette if there is room. If the palette is full, map them to the nearest existing entries.
3. **Head transplant.** Paste the new character's head pixels from its stand frame of the frame's direction at the template's head anchor. This carries hair, hats and faces exactly.
4. **Clean-up (optional, default on for people).** Walker LoRA inpaint at 8× on the body region (not head, not props), denoise 0.35–0.5, IP refs = the new 4 views, N = 4. Then the finisher locks to the character palette.
5. **Legendary actions.** There is no head transplant. Use recolour by material plus a keyframe-derived silhouette: the inpaint step runs on the whole creature with the template frame as a ControlNet lineart hint. Effect-only frames (lines) are copied unchanged.

**Story-NPC kit:** the template is the nearest ROM story set (DINOv2 on stand frames) per action group.

### W9. Kit assembler (`spritegen walker assemble`)

- Reads the kit + W1 layout and places stand (W6), animated (W7) and retargeted (W8) frames into texture-index order.
- Applies runtime-mirror rules: mirrored slots are **not** stored when the ROM kind doesn't store them.
- Builds palettes:
  - `palette_0` = character palette.
  - Creatures: `palette_1` (shiny) = for each walker entry, the battle shiny entry at the **same battle palette index**. The walker palette is a subset of the battle palette, so the correspondence is exact.
  - People: palette 1 only.
- Previews: walk GIF per direction at 1× and 4× using the frame order from W1, plus a per-kit sheet in ROM atlas layout.
- **Set-level checks:**
  - One palette across all frames.
  - Frame count == kind.
  - Feet line stable ±1 px across walk frames.
  - No frame exceeds the canvas.

### W10. Scoring and picking (extends C9/C10)

| Metric | Meaning |
| --- | --- |
| `view_consistency` | Mean DINOv2 cosine between views vs the ROM distribution |
| `ref_fidelity` | Similarity of the down view to the battle front (identity carried over) |
| `asym` | Mirror difference (drives the kind choice; shown on the sheet) |
| `temporal_delta` | Changed pixels per step vs the per-kind ROM distribution (flags frozen or exploding frames) |
| `head_stability` | Head region identical across walk frames after bob (people) |
| `palette_used` | Entries used vs ROM median per kind |

Picking happens per group: keyframe sheet first (from N = 8), then each special group (from N = 4). The animator is deterministic, so it has nothing to pick; rerun `--fallback rule` for a bad direction. Touch-ups happen on the indexed frames; `spritegen walker assemble --verify` re-runs the checks.

### W11. Exporter (`spritegen walker export <job> --id <member>`)

- Writes `assets/sprites/overworld/{member:03}_{kind}.png`, `_p1.png` (creatures) and `.atlas.ron` in the exact shape `black extract-sprites overworld` produces: `source`, `name`, `frame_size`, `columns: 8`, `images[(palette, file)]`, `frames[(name: "t4x4{kind}.N", rect)]`.
- **IDs:** new sets are appended after the last ROM member (763). The exporter refuses ROM IDs without `--force`.
- Appends `characters.csv` (`character, battle_id, battle_kind, walker_member, walker_kind, kit, palettes`), which links battle and walker for the Map & Event Editor. It also updates `manifest.json`.
- **Golden test:** re-export a ROM set (indexed frames + palettes from W0) through W11. Output must be byte-identical to the extractor's atlas and PNGs.
- **Registration:** a walker appears in the game through an **ARC 048 OBJ record** (0x1C bytes: code, draw proc b3, scale b7, resource class b8, anime table b9, ARC 049 member at halfword 8). Event records (ARC 125) then reference that OBJ code. W11 writes the asset files, `characters.csv`, and a proposed OBJ record (`obj_records.csv`: next free code, kind-matched b3/b7/b8/b9). Committing records and placing NPCs belongs to the Map & Event Editor.

### W12. ComfyUI

- `comfy/workflows/walker_keyframes.json`: sheet inpaint with the battle panel, IP-Adapter and `SpritegenFinish` in multi-panel mode.
- `walker_retarget_cleanup.json`: W8 step 4.
- The animator runs only from the CLI. ComfyUI calls `spritegen walker animate` through a `SpritegenAnimate` node that imports the package; there is no second implementation.

## 6. Chained job (battle → walker)

`jobs.csv` gains walker columns. Blank means auto:

| Column | Values | Default |
| --- | --- | --- |
| `walker_kit` | `person`, `creature`, `legendary`, `player`, `story_npc`, `object`, `effect`, `none` | `person` for the People LoRA, `creature` for Creatures (`legendary` if tagged) |
| `walker_size` | `auto`, `32`, `64` | `auto` (§3) |
| `walker_symmetry` | `auto`, `sym`, `asym` | `auto` |
| `walker_template` | ROM set id | Nearest by DINOv2 (`story_npc`, `legendary`, `player`) |

`spritegen run jobs.csv` stages:

1. Battle front (C6–C10).
2. Battle back (creatures).
3. Walker keyframes (W6), conditioned on the picked battle front.
4. Animator (W7).
5. Retarget (W8, kit-dependent).
6. Assemble (W9).
7. Export battle (C11) + walker (W11) together.

The run pauses at each human pick and resumes with `spritegen run jobs.csv --resume`. State is kept in `out/<job>/state.json`.

## 7. Configuration additions (`config.yaml`)

```yaml
walkers:
  trigger: pkbwwalk
  sheet: {width: 1536, height: 768, battle_scale: 8, view_scale: {32: 8, 64: 6}, grid: [[up, down], [left, right]]}
  layouts: walker_layouts.yaml
  anchors:                    # per-kind ROM medians (§2)
    person32: {cx: 16, feet_y: 30}
    creature32: {cx: 16, feet_y: 29}
    creature64: {cx: 32, feet_y: 61}
    legendary64: {cx: 32, feet_y: 62}
  asym_threshold: 0.08        # calibrated in Phase 0
  size64_min: null            # calibrated from walker_pairs.csv
  palette_from_battle: true
  holdout: {creature: 20, person: 8}
  checkpoint: null
  generate: {n: 8, cfg: 6.0, steps: 30, ip_weight: 0.5, lora_weight: 0.9}
  retarget: {cleanup: true, denoise: 0.4, n: 4}
animator:
  canvas: 64
  channels: [64, 128, 256, 256]
  steps: 30000
  batch: 64
  lr: 3.0e-4
  bob_range: 2
  checkpoint: null
```

## 8. Directory layout additions

```
black-rust/tools/spritegen/
  src/spritegen/walker/
    layouts.py        # W1 load/validate/label sheets
    pairs.py          # W2
    prep.py           # W4 sheets
    keyframes.py      # W6 (uses generate.py / finish.py)
    animator/         # W7: dataset.py, model.py, train.py, infer.py, rules.py
    retarget.py       # W8
    templates.py      # W8a material maps, prop masks, head boxes
    assemble.py       # W9
    export.py         # W11
  walker_layouts.yaml         # tracked
  walker_pairs.csv            # tracked (reviewed)
  walker_templates/<set>/materials.yaml   # tracked (reviewed)
  work/walkers/               # untracked: indexed frames, datasets, models, out
```

## 9. Software

Same stack as the battle doc §9. The only additions are inside existing dependencies:

- **Animator:** plain PyTorch (already present).
- **Assignment:** `scipy.optimize.linear_sum_assignment` (SciPy, BSD) for W2/W8.
- **GIF previews:** Pillow.

No new model downloads: W2 and W10 reuse DINOv2, and W3 and W8a reuse the VLM.

## 10. Build plan

Each phase ends in a check; a failed check stops the line. Phases 1 and 2 are independent and can run in parallel.

| Phase | Builds | Done when |
| --- | --- | --- |
| 0. Data | W0 `--indexed`, W1 layouts, W2 pairs, calibrate `asym_threshold` and `size64_min` | Export tests pass; `layouts --from-rom` + `check-layouts` pass on all 758 sets; creature pairs verified, ≥ 60 people pairs reviewed |
| 1. Animator | W7a/b + rule fallback | On holdout sets: full-frame index accuracy ≥ 97%, changed-region IoU ≥ 0.6, bob accuracy ≥ 95%. In a blind GIF review, a reviewer can't reliably pick real from generated walk cycles (≤ 60% correct over 20 pairs) |
| 2. Keyframe LoRA | W3, W4, W5 + eval | Holdout battle→walker down views recognisable in ≥ 1 of 8; `view_consistency` within the ROM inter-quartile range; blind 1× test as in the battle doc |
| 3. Standard kits | W6, W9, W10 for `person` / `creature` (32 and 64) | 5 held-out battle characters per kit produce a complete, game-valid walker with ≤ 2 picks and no hand edits on ≥ 3 of 5 |
| 4. Specials | W8a library, then W8 for `player` → `story_npc` → `legendary`; `object`, `effect` | Each special group accepted in ≥ 1 of 4 candidates for 3 test characters |
| 5. Export | W11 + golden test; chained `spritegen run` | ROM re-export byte-identical; one end-to-end job exports battle + walker together |
| 6. ComfyUI | W12 | Workflows reproduce CLI keyframe candidates for the same seed |

## 11. Risks

| Risk | Mitigation |
| --- | --- |
| Frame map wrong → animator learns wrong pairs | W1 validation rules; animator data built only from validated layouts |
| Keyframe views disagree (e.g. hair different on back view) | Joint sheet generation, battle panel + IP refs, fix-a-view inpaint, `view_consistency` ranking |
| Animator averages legs into mush | Residual head (copy unchanged pixels), palette-subset logits, MaskGIT upgrade path, rule-rig fallback |
| Specials data is tiny (2 sets per player kind) | Retargeting is mostly deterministic (material map + head transplant); diffusion only cleans up |
| Odd creature bodies (serpent, floating, blob) | 573 creature sets cover them; the animator is conditioned on all views; fallback picks the nearest same-shape ROM set |
| Battle ↔ walker colour mismatch | Walker palette is a subset of the battle palette by construction; shiny derived by index |
| 64 px views not latent-aligned (6×) | Known-scale grid search in the finisher; only 40 training sets affected |
| Pairing errors poison battle-conditioned training | Confidence threshold + review; unpaired sets train as `no reference` |
| New walker not registered in maps | W11 proposes the ARC 048 OBJ record; the Map & Event Editor commits it and places NPCs |

## 12. Remaining unknowns

- [ ] Whether `_p1` is the shiny palette, and when the game uses it.
- [ ] Identity of the `spider` / `xocell` sets (not needed by the pipeline).

Resolved on Oct 20, 2026, with evidence in the checklist's Unknowns table:

- the frame table (§2);
- creature walker ↔ species (W2);
- the class ↔ walker relation (none by design; W2);
- OBJ code → ARC 049 member (ARC 048, W11);
- quad size (ARC 048 b7).

## Appendix A. Evidence

- **Extractor run:** `black extract-sprites overworld /tmp/spr` → 758 character sets, 5,521 frames, 0 failures.
- **Kinds, sizes, frame and palette counts:** from every `.atlas.ron` and its PNGs.
- **Colours, content boxes, feet lines:** stand-frame statistics per kind. The `pokenflip` mirror difference (11%) and stand→step pixel deltas were computed over all 32 px `flip` / `nflip` / `pokeflip` / `pokenflip` sets.
- **Visual check:** contact sheets of `hero`, `cycle`, `swim`, `x14`, `pcwoman`, `x22`, `xocell`, `gethero`, `pchero`, `spider`, `cutinhero`, `hurahero`, `fishgirl`, `x20`, 64 px `pokeflip`, `pokenflip` and `x15poke` sets.
- **ARC 069:** 29 members, all `BTA0`; strings are map-texture names (`sea_mizu1`, `kawa01a`, `ue_grass01`, …).
- **Code:** `black-rust/crates/black-cli/src/cmd_extract_sprites/overworld.rs` (BTX0 decode, palette indices, frame naming).
