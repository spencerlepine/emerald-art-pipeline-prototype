# sprite-walker-generator (overworld walkers)

**Status: READY** for the 16x32 people kit (category B3). Other kits (32x32 big, 16x16 small,
bike/surf/fishing/field-move sheets, creature walkers A6, dolls/cushions C4) are not built.

Reference: `art/vader.yaml` -> `output/vader/` (approved, helmet variant A).

## Setup

This folder is a self-contained tool: its own Python package, requirements, decision log,
corpus, art and output. It needs nothing outside this folder except a pokeemerald checkout.

```bash
# from this folder
pip install -r requirements.txt     # pillow, pyyaml
# a pokeemerald checkout: set EMERALD_DIR, or keep a clone named pokeemerald beside any
# folder above this one (its game/ subfolder is used when present)
export EMERALD_DIR=/path/to/pokeemerald/game
```

| Path | What |
| --- | --- |
| `walker_sprite/` | The Python package (`python -m walker_sprite ...`) |
| `art/<name>.yaml` | Walker specs: what the LLM writes |
| `output/<name>/` | Built game-ready PNG, `lint.txt`, `metrics.json`, `preview/` (zoom, walk.gif, scene, showcase) |
| `palettes/` | Copies of Emerald's four shared NPC palettes (D6) |
| `corpus/people16x32.json` | Style metrics measured on the 90 vanilla 16x32 walkers (`python -m walker_sprite corpus`) |

`D1`, `D2`... are the decisions in this folder's [DECISIONS.md](DECISIONS.md): read it before changing
the tool.

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

## Format (what the game needs)

| Fact | Value | Source |
| --- | --- | --- |
| Sheet | 144x32 PNG = 9 frames of 16x32, side by side | `graphics/object_events/pics/people/**` (90 vanilla sheets) |
| Frame order | 0 face down, 1 face up, 2 face left, 3-4 walk down, 5-6 walk up, 7-8 walk left | `sPicTable_*` + `sAnimTable_Standard` |
| East | Frames 2/7/8 drawn with `hFlip`; there is no right-facing art | `sAnim_GoEast` in `object_event_anims.h` |
| Walk cycle | step A, stand, step B, stand; 8 ticks per frame at normal speed | `sAnim_GoSouth` etc. |
| Palette | **Shared**: one of four NPC palettes (`npc_1..4.pal`) for ~107 sprites. Indices 1-4 are the same skin ramp in all four | `graphics/object_events/palettes/`, `.paletteTag` in `object_event_graphics_info.h` |
| Slot | `.paletteTag` and `.paletteSlot` must agree (`OBJ_EVENT_PAL_TAG_NPC_4` + `PALSLOT_NPC_4`) | same |
| Size | `.size = 256` bytes per frame (16x32 at 4bpp) | same |

Measured style of the 90 vanilla sheets (`corpus/people16x32.json`, rebuilt with
`python -m walker_sprite corpus`): art starts on row 10-13 and stands on row 30, is 18-21 px
tall and 14-16 px wide, ~226 opaque pixels, 10-15 colours, outlined in near-black on almost
every edge pixel, and a step frame changes ~70% of pixels (the whole body bobs 1 px plus legs
and arms).

### Rules for all GBA 4bpp art

- The game builds from **indexed PNGs** (mode `P`) via pokeemerald's `tools/gbagfx`, which
  reads pixel *indices*; the colours on screen come from the palette the game loads.
- Max 16 colours per palette, index 0 is transparent.
- GBA colour is 15-bit: each channel keeps 5 bits (`v >> 3 << 3`). Colours that differ only in
  the low 3 bits look identical in game, so use multiples of 8.
- Sizes are multiples of 8 (tiles are 8x8).
- Replacing a PNG at the same path needs no code change; a new asset needs C table entries.

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
   feedback in `DECISIONS.md`.
