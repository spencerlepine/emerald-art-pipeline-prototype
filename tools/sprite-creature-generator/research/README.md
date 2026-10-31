# Creature sprites with an image model: research

Status: **research only** (2026-10-31). Nothing here has been run on a GPU. The owner chose an
image model for every creature (D7) after hand-drawing fell short in round 1, and asked for
all research, old and new, to be kept in this folder so the build can start later without
re-asking.

## Files

| File | What |
| --- | --- |
| [EMERALD-PLAN.md](EMERALD-PLAN.md) | **Start here.** The plan for Emerald: what to reuse from the Black design, what changes for 64x64 GBA sprites, model and hosting choice, costs, build phases, open questions |
| [WEB-RESEARCH-2026-10-31.md](WEB-RESEARCH-2026-10-31.md) | New research with sources: existing Pokémon sprite LoRAs, pixel-art models, cleanup tools, hosted APIs and GPU prices, image-edit models for back views, licences |
| [ROUND1-HAND-DRAWN.md](ROUND1-HAND-DRAWN.md) | What the LLM-only attempt showed, and how its output can still feed the model (sketch as init image) |
| [prior-black/](prior-black/) | Copies of the owner's earlier designs from `spencerlepine/black` `.docs/` @ 506caef (2026-10-22): the `spritegen` LoRA pipeline (C0-C12), the walker pipeline (W0-W12) and the PMD-style sprite tool conversation (M1 Mac, rented GPU for training) |
| [measure.py](measure.py) | Measures the 384 vanilla species and joins the Star Wars mapping; no GPU |
| [vanilla-stats.json](vanilla-stats.json) | Its output: sizes, colours, placement, front2 change, back scale, key-colour distances, per species |
| [sw-creature-jobs.csv](sw-creature-jobs.csv) | One row per species folder: the Star Wars creature that replaces it, canon/original, description, Datapad text, types, colour, egg groups, size class. The future `jobs.csv` source |

Re-run the measurements with
`python measure.py <pokeemerald>/game <emerald-sw-db>/database` (pokeemerald keeps the game
under `game/`).

## The short version

1. The Black `spritegen` design (SDXL + LoRA trained on the game's own sprites + a
   deterministic finisher) fits Emerald almost unchanged. Main differences: 64x64 at 16x scale
   (exactly 1024 px), 384 species with front, **second animation frame** and back, and our
   existing `creature_sprite` tool is already the exporter and verifier.
2. No public model is trained on Gen 3 sprites specifically. The closest is the CivitAI
   "Pokemon Sprite PixelArt 768" SD 1.5 LoRA (96x96 sprites, gen1-5 tags, `backside` and
   `shiny` tags): a free baseline to beat, not the answer.
3. Hosting for an M1 Mac owner: train on a rented GPU (a few dollars per run) and run the
   batch on a rented RTX 4090 (about $0.34/h; ~400 creatures x ~20 candidates is a few hours).
   Per-image hosted APIs work but cost ~100x more at batch scale.
4. Cheapest first test, no GPU at all: PixelLab's API draws native 64x64 sprites with a palette
   lock and has a rotate tool (about $0.01 per 64x64 call). Worth one evening before any
   training, as a bar for the LoRA.
5. The hard parts are the same as Black's plus one: back views that match the front, and the
   second frame (vanilla's changes a median 72% of pixels: a real pose change, not a bob).
