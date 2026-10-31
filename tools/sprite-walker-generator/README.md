# sprite-walker-generator (overworld walkers)

**Status: READY** for the 16x32 people kit (category B3). Other kits (32x32 big, 16x16 small,
bike/surf/fishing/field-move sheets, creature walkers A6, dolls/cushions C4) are not built.

Reference: `art/vader.yaml` -> `output/vader/` (approved, helmet variant A).

## Setup

This folder is a standalone tool: its own Python package, requirements, corpus, art and
output. It shares no code with the other tools in `tools/`.

```bash
cd tools/sprite-walker-generator
pip install -r requirements.txt     # pillow, pyyaml
# pokeemerald next to this repo (its game/ folder is used if present), or set EMERALD_DIR
git clone https://github.com/spencerlepine/pokeemerald ../../../pokeemerald
```

| Path | What |
| --- | --- |
| `walker_sprite/` | The Python package (`python -m walker_sprite ...`) |
| `art/<name>.yaml` | Walker specs: what the LLM writes |
| `output/<name>/` | Built game-ready PNG, `lint.txt`, `metrics.json`, `preview/` (zoom, walk.gif, scene, showcase) |
| `palettes/` | Copies of Emerald's four shared NPC palettes (D6) |
| `corpus/people16x32.json` | Style metrics measured on the 90 vanilla 16x32 walkers (`python -m walker_sprite corpus`) |

`D1`-`D16` refer to the repo-wide decision log, [docs/DECISIONS.md](../../docs/DECISIONS.md); the
game's format facts are in [docs/EMERALD-ART-REQUIREMENTS.md](../../docs/EMERALD-ART-REQUIREMENTS.md).

## Commands

```bash
python -m walker_sprite build   art/<name>.yaml               # PNG + previews + lint
python -m walker_sprite verify  art/<name>.yaml               # round trip through pokeemerald's gbagfx
python -m walker_sprite install art/<name>.yaml               # copy into pokeemerald, set the palette tag
python -m walker_sprite compare output/<x>.png a.yaml b.yaml  # variant review sheet
python -m walker_sprite lint    <any_sheet.png>               # lint an existing sheet
python -m walker_sprite corpus                                # re-measure vanilla walkers
```

## Spec

`kit: person16x32` (the default), `palette: npc_1..4`, `replaces:`, `graphics_info:`,
`palette_tag:`, `legend:` (one character -> one palette index), and the nine frames
`down up left down_a down_b up_a up_b left_a left_b`. A frame is a 16-wide grid
(bottom-anchored), `half:` (left half, mirrored, optional `mirror_shade`), `base:` + `shift` +
`patch_y`/`rows` (D4), or `mirror_of:`; any of them plus `patches:`.

## Drawing a new 16x32 walker

1. Find the asset in `emerald-sw-db/database/pending_art.csv` (`kind = object_events`) to get
   the vanilla file it replaces and the Star Wars character.
2. Pick the NPC palette (`palettes/npc_1..4.pal`) that already holds the character's colours
   (D6). Write `art/<name>.yaml`, copying `vader.yaml`'s structure: `replaces`,
   `graphics_info`, `palette`, `palette_tag`, `legend`, frames.
3. Draw `down`, `up`, `left` as 16-wide grids, bottom-anchored, feet on row 30 (empty last
   line), top no higher than row 10. Pure black outline; clothes in a 3-step ramp
   (shadow/base/highlight), light from the upper left (D7). Derive step frames with
   `base/shift/patch_y/rows` (D4). For helmeted characters start from Vader's helmet language
   (round dome, pinch at the temples, flare past the shoulders).
4. `cd tools && python -m walker_sprite build art/<name>.yaml`, then **look at**
   `output/<name>/preview/zoom.png` and `scene.png` (the sprite next to vanilla walkers
   at 1x-3x). Fix and rebuild until it reads at 1x. Address every lint warning or note in the
   spec why it is accepted.
5. `python -m walker_sprite verify art/<name>.yaml` must report an identical round trip.
6. Uncertain part (helmet, hair, silhouette)? Draw 2-4 variants and make a review sheet with
   `python -m walker_sprite compare output/<name>-variants.png a.yaml b.yaml ...`.
7. Commit the spec with `output/<name>/`. Show the owner `showcase.png` and record
   feedback in the repo's `docs/DECISIONS.md`.
