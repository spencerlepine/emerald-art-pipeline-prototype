# What pokeemerald needs from the art pipeline

Verified against `spencerlepine/pokeemerald` (commit 731ad5bf) on 2026-10-31. This is the
contract every tool in this repo must meet.

## The short answer

Yes, the game consumes plain PNG files, but not any PNG. Every sprite and tile is an
**indexed PNG** (mode `P`) that the build converts with `tools/gbagfx` into 4bpp tile data.
gbagfx reads the **pixel indices only**: the colours stored in the PNG are ignored for most
assets, and the colours on screen come from a separate palette file (`.pal`, JASC-PAL text).
So the pipeline's output has to be index-correct against the palette the game will load, not
just "look right" as RGB.

General rules for all 4bpp art:

- Max 16 colours per palette, index 0 is transparent.
- GBA colour is 15-bit: each channel is truncated to 5 bits (`v >> 3 << 3`). Colours that
  differ only in the low 3 bits look identical in game.
- Sizes are multiples of 8 (tiles are 8x8).
- Conversion happens inline: e.g. `INCGFX_U32("graphics/.../maxie.png", ".4bpp", "-mwidth 2 -mheight 4")`
  in `src/data/object_events/object_event_graphics.h`. Replacing a PNG at the same path needs
  no code change; a new asset needs entries in the C tables.

## Overworld walkers (people) — the prototype's target

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
`python -m emerald_sprite corpus`): art starts on row 10-13 and stands on row 30, is 18-21 px
tall and 14-16 px wide, ~226 opaque pixels, 10-15 colours, outlined in near-black on almost
every edge pixel, and a step frame changes ~70% of pixels (the whole body bobs 1 px plus legs
and arms).

## Other categories (for later prototypes)

| Asset | Format | Palette | Count in `emerald-sw-db/database/pending_art.csv` |
| --- | --- | --- | --- |
| Pokémon front | `anim_front.png` 64x128 (two 64x64 frames), `back.png` 64x64 | own `normal.pal` + `shiny.pal` per species | `pokemon`: 2066 rows (all per-species files) |
| Pokémon icon | `icon.png` 32x64 (two frames) | one of 3 shared icon palettes | (in `pokemon`) |
| Trainer front pic | 64x64 | own palette | `trainers`: 101 |
| Item icon | 24x24 | own palette | `items`: 218 |
| Walkers | as above | shared NPC palettes | `object_events`: 253 |
| Tilesets | `tiles.png` 128 px wide of 8x8 tiles; metatiles = 2 layers x 4 tiles (`metatiles.bin`) | primary uses palettes 0-5, secondary 6-12; each **tile** picks one palette | `tileset`: 226 |

Tilesets are the hardest to automate: art is assembled from 8x8 tiles that share palettes
with the rest of the tileset, metatile layouts and behaviours live in binary files, and maps
reference metatile ids. That is a separate tool from the sprite one.
