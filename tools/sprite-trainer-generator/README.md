# sprite-trainer-generator (trainer battle pics)

**Status: READY.** A repaint tool (D13): each pic starts from the vanilla pic closest in pose
and costume, recoloured and kitbashed. Approved by the owner on round 5 (Vader, Boba Fett,
Leia, Obi-Wan). Category B1 (93 pics) and B4 (professor portrait).

**Read [STYLE-GUIDE.md](STYLE-GUIDE.md) first**: pose, perspective and pixel rules from the 93
vanilla pics, a review checklist, and the owner's feedback log. Getting the pose right is the
hard part of this category; the format is handled by the tool.

Reference specs (repaints): `art/vader.yaml` (base Drake), `boba.yaml` (Pyramid King
Brandon), `leia.yaml` (Glacia), `obiwan.yaml` (Expert M), plus the later mockups listed in
STYLE-GUIDE's feedback log. Review sheets: `output/style-check-r5.png` and
`repaint-bases-r5.png` (approved round), `style-check-r4.png` and `vader-poses-r*.png` (rig
drawings, rejected, kept for comparison). Back pics (category B2) are a separate tool,
`tools/sprite-trainer-back-generator`.

## Setup

This folder is a standalone tool: its own Python package, requirements, corpus, art and
output. It shares no code with the other tools in `tools/`.

```bash
cd tools/sprite-trainer-generator
pip install -r requirements.txt     # pillow, pyyaml
# pokeemerald next to this repo (its game/ folder is used if present), or set EMERALD_DIR
git clone https://github.com/spencerlepine/pokeemerald ../../../pokeemerald
```

| Path | What |
| --- | --- |
| `trainer_sprite/` | The Python package (`python -m trainer_sprite ...`) |
| `art/<name>.yaml` | Trainer pic specs (repaints): what the LLM writes |
| `output/<name>/` | Built game-ready PNG, `lint.txt`, `metrics.json`, `preview/` (zoom, battle, showcase) |
| `output/*.png` | Review sheets shown to the owner (`compare`) |
| `corpus/trainer64.json` | Style metrics measured on the 93 vanilla pics (`python -m trainer_sprite corpus`) |
| `STYLE-GUIDE.md` | Pose, perspective and pixel rules, review checklist, owner feedback log |

`D1`-`D16` refer to the repo-wide decision log, [docs/DECISIONS.md](../../docs/DECISIONS.md); the
game's format facts are in [docs/EMERALD-ART-REQUIREMENTS.md](../../docs/EMERALD-ART-REQUIREMENTS.md).

## Commands

```bash
python -m trainer_sprite build   art/<name>.yaml               # PNG + previews + lint
python -m trainer_sprite verify  art/<name>.yaml               # round trip through pokeemerald's gbagfx
python -m trainer_sprite install art/<name>.yaml               # copy over the vanilla pic it replaces
python -m trainer_sprite inspect <vanilla.png> <out.png>       # which palette index is which material
python -m trainer_sprite compare output/<x>.png a.yaml b.yaml  # review sheet in a battle scene
python -m trainer_sprite corpus                                # re-measure the vanilla pics
```

## Format (what the game needs)

- One 64x64 indexed PNG per pic in `graphics/trainers/front_pics/`, one frame.
- **Own palette, stored in the PNG**: `src/data/graphics/trainers.h` builds both the tiles
  (`.4bpp.lz`) and the palette (`.gbapal.lz`) from the same PNG. So the spec carries an inline
  16-colour `palette:` list; index 0 is transparent. Use multiples of 8 per channel (the GBA
  keeps 5 bits), and no two colours that collapse to the same GBA colour.
- Shown at centre (176, 40) in battle, also on the trainer card, Hall of Fame and Frontier.
- Replacing a PNG at the same path needs no code change.

Measured on the 93 vanilla pics (`corpus/trainer64.json`): full body, feet on row 62-63, head
at row 1-17, 29-57 px wide, ~1,075 opaque pixels, 13-15 colours, near-black outline on most
edges, plenty of single-pixel highlights (orphans 11-23%).

## Drawing a new trainer pic (repaint)

1. Find the asset in `emerald-sw-db/database/pending_art.csv` (`kind = trainers`) and the
   Star Wars character in `swap_map.csv`.
2. **Pick a base**: the vanilla pic in `graphics/trainers/front_pics/` whose pose *and* costume
   cut are closest (long coat -> cape, gown -> gown, robe -> robe). Make a contact sheet
   (STYLE-GUIDE, last section) and choose by silhouette, not by the character it replaces.
   Bases used so far: see the reference specs above.
3. `python -m trainer_sprite inspect $EMERALD_DIR/graphics/trainers/front_pics/<base>.png
   /tmp/insp.png` and look at it: a false-colour map of which palette index is which material
   (skin, hair, each cloth ramp, outline). Watch for one index used by two materials (Glacia's
   belt shares the hair colours); fix those with a `recolour` region.
4. Write `art/<name>.yaml` (copy `leia.yaml`): inline `palette` (index 0 transparent,
   outline, then 3-4 step ramps), `legend`, and a frame with
   `repaint: {pic: <base path>, remap: {<vanilla index>: <legend char>, ...}}` (every index the
   base uses must be mapped; `flip: true` mirrors it). Map whole ramps to whole ramps so the
   vanilla shading survives.
5. Kitbash with `rig: layers:` on top of the base, in order:
   - `erase: true` shapes remove what goes (old head, hat, held ball);
   - `recolour: "a:b c:d"` shapes split one vanilla material into two of ours (sleeves grey,
     chest green);
   - shaded shapes (`poly`, `ellipse`, `capsule` with a `ramp`) build new parts (helmet, buns,
     saber); `behind: true` paints only empty pixels, for parts behind the body (jetpack);
   - `shape: pixels` places faces, visors, emblems by hand, before anything held in front;
   - `shape: edge` with `chars`/`to` gives a light material a selective (non-black) outline.
6. `python -m trainer_sprite build art/<name>.yaml`, then **look at**
   `output/<name>/preview/zoom.png` (8x with coordinates) and `showcase.png`
   (in battle at 1x and 2x next to the pic it replaces). Fix until it reads at 1x.
7. `python -m trainer_sprite verify art/<name>.yaml`: 2048 bytes of 4bpp, a 32-byte
   palette, identical round trip. Then a `compare` sheet for the owner.

There is no from-scratch mode: a frame made only of rig shapes is rejected (D14, the owner
rated rig drawings "about 70%"). Rig layers are only for kitbashing a repaint; the layer
reference is the docstring in `trainer_sprite/rig.py`.

## Known gaps

- Pose variety is limited to the 93 vanilla bases plus what kitbashing can change; each pic
  is visibly derived from its base.
- Lint flags slightly too few single-pixel highlights where large drawn parts (helmets)
  replace hand-pixelled ones.
- `symmetry` (share of pixels equal to their mirror) is linted against vanilla's 0.06-0.33;
  a front-on mirrored figure scores ~0.65.
- `install` copies the PNG only; nothing else is needed for an existing pic.
