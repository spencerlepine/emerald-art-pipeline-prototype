# sprite-creature-generator (creature battle sprites)

**Status: PENDING (needs a GPU).** The tool builds, verifies and installs every file a species
needs. The drawing will be done by an image model (D15); the research and the build plan are in
**[research/](research/README.md)** (start with `research/EMERALD-PLAN.md`). Nothing below the
format section draws final art yet. Categories A1 (front + 2nd frame, normal and
shiny palettes) and A2 (back).

Mockups: `art/rancor_drawn.yaml` (replaces Rhydon), `mynock_drawn.yaml` (Zubat).
Review sheet: `output/creature-drawn-r1.png`.

## Setup

This folder is a standalone tool: its own Python package, requirements, corpus, art and
output. It shares no code with the other tools in `tools/`.

```bash
cd tools/sprite-creature-generator
pip install -r requirements.txt     # pillow, pyyaml
# pokeemerald next to this repo (its game/ folder is used if present), or set EMERALD_DIR
git clone https://github.com/spencerlepine/pokeemerald ../../../pokeemerald
```

| Path | What |
| --- | --- |
| `creature_sprite/` | The Python package: builds, lints, verifies and installs the five species files (the future image-model finisher, D15) |
| `art/<name>.yaml` | Creature specs |
| `output/<name>/` | `anim_front.png`, `front.png`, `back.png`, `normal.pal`, `shiny.pal`, `lint.txt`, `metrics.json`, `preview/` |
| `corpus/creature64.json` | Style metrics measured on 384 vanilla fronts (`python -m creature_sprite corpus`) |
| `research/` | Image-model research and build plan (start with `research/EMERALD-PLAN.md`) |

## Format (what the game needs)

Per species, `graphics/pokemon/<species>/` (built by `src/data/graphics/pokemon.h`):

| File | Content |
| --- | --- |
| `anim_front.png` | 64x128: front frame on top, 2nd animation frame below (battle intro, Pokédex) |
| `front.png` | 64x64: identical to the top frame (the still front) |
| `back.png` | 64x64: player-side sprite, drawn larger (median 1.22x the front's area; 3% touch the bottom edge) |
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

`D1`-`D16` refer to the repo-wide decision log, [docs/DECISIONS.md](../../docs/DECISIONS.md); the
game's format facts are in [docs/EMERALD-ART-REQUIREMENTS.md](../../docs/EMERALD-ART-REQUIREMENTS.md).

## Commands

```bash
python -m creature_sprite build   art/<name>.yaml               # 5 files + previews + lint
python -m creature_sprite verify  art/<name>.yaml               # gbagfx round trip of all 5
python -m creature_sprite install art/<name>.yaml               # copy into graphics/pokemon/<replaces>/ + y_offsets
python -m creature_sprite inspect <vanilla.png> <out.png>       # which palette index is which material
python -m creature_sprite compare output/<x>.png a.yaml b.yaml  # variant sheet
python -m creature_sprite corpus                                # re-measure vanilla fronts
```

Previews in `output/<name>/preview/`: `zoom.png` (3 frames, 6x, grid), `battle.png`
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

Finding (details in `research/ROUND1-HAND-DRAWN.md`): the LLM places a readable silhouette and features, but cannot render form the way
Emerald's artists do (clustered light, selective outlines, texture). That is the same gap D13
found for trainers, and here there is no vanilla figure to borrow it from.
Fronts only; `front2` and `back` in both specs are placeholders.
