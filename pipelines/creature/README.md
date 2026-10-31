# Tool: `creature` (creature battle sprites)

**Status: IN-REVIEW.** The tool builds, verifies and installs every file a species needs; the
*drawing method* is not settled (see Round 1 below). Categories A1 (front + 2nd frame, normal and
shiny palettes) and A2 (back).

Mockups: `art/creatures/rancor_drawn.yaml` (replaces Rhydon), `mynock_drawn.yaml` (Zubat).
Review sheet: `output/creatures/creature-drawn-r1.png`.

## Format (what the game needs)

Per species, `graphics/pokemon/<species>/` (built by `src/data/graphics/pokemon.h`):

| File | Content |
| --- | --- |
| `anim_front.png` | 64x128: front frame on top, 2nd animation frame below (battle intro, Pokédex) |
| `front.png` | 64x64: identical to the top frame (the still front) |
| `back.png` | 64x64: player-side sprite, drawn larger and cut off by the bottom edge |
| `normal.pal`, `shiny.pal` | JASC palettes, 16 entries; the PNGs' own colours are ignored |

Placement: `front_pic_coordinates.h` / `back_pic_coordinates.h` hold `y_offset` = empty rows
under the art (the tool computes it; `install` writes it), `enemy_mon_elevation.h` lifts
floating creatures (`elevation:` in the spec). All four files share one palette: max 15 colours
over front, 2nd frame and back together.

Measured on 384 vanilla fronts (`corpus/creature64.json`): bottom row 45-63, 28-64 px wide,
566-2,346 opaque px (median 1,205), 10-15 colours, dark outline on ~80% of edge pixels (many
use a dark hue of the body colour instead of black), 9-21% single-pixel accents, symmetry
0.08-0.31 (3/4 views; most face left, some right).

## Spec

`kit: creature64`, frames `front`, `front2`, `back`, inline `palette:` and `shiny:` (same
length, same index meaning), `replaces: <species folder>`, optional `elevation:`.
A frame can be:

- a 64-row grid (hand-placed pixels);
- `sketch:` a 32x32 grid, doubled, outlines thinned to 1 px, then refined with `patches:`;
- `splice:` parts of any vanilla sprite (front, front2 or back of any of the 386 species),
  each cropped, optionally polygon-masked, moved, flipped and palette-remapped
  (`remaps:` holds named maps), then `rig:` layers (erase, recolour, pixels, edge) and
  `patches:` on top;
- `base:` another frame shifted, with rows replaced, or `mirror_of:`.

## Commands

```bash
cd tools
python -m emerald_sprite build   ../art/creatures/<name>.yaml   # 5 files + previews + lint
python -m emerald_sprite verify  ../art/creatures/<name>.yaml   # gbagfx round trip of all 5
python -m emerald_sprite install ../art/creatures/<name>.yaml   # copy into graphics/pokemon/<replaces>/ + y_offsets
python -m emerald_sprite compare out.png a.yaml b.yaml          # variant sheet
```

Previews in `output/creatures/<name>/preview/`: `zoom.png` (3 frames, 6x, grid), `battle.png`
(front on the opponent side, back on yours, next to the vanilla species, 2x and 1x),
`anim.gif`, `showcase.png` (with the shiny strip).

## Round 1 (2026-10-31): can the LLM draw a creature?

The owner ruled out shape-based drawing (D14) and repaints for creatures (Star Wars creatures
do not share Pokémon shapes). So round 1 tests pure hand-drawing: every pixel placed by the
LLM, no vanilla pixels, no shapes.

- **Rancor** (Rhydon's slot): sketched at 32x32, redrawn at 64x64 in segments, two detail
  passes. Reads as a Rancor at 1x in battle (hunched, long arms, underbite, claws), but the
  rendering is flat next to Rhydon: big single-tone areas, few form clusters, no texture
  (a mottling pass read as noise and was removed). Self-rated ~60%.
- **Mynock** (Zubat's slot): one pass. Wings came out as flat triangles with dotted ribs, not
  membranes; body is a ball. ~35%.

Finding: the LLM places a readable silhouette and features, but cannot render form the way
Emerald's artists do (clustered light, selective outlines, texture). That is the same gap D13
found for trainers, and here there is no vanilla figure to borrow it from.
Fronts only; `front2` and `back` in both specs are placeholders.
