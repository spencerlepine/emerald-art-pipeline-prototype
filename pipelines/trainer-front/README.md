# Tool: `trainer-front` (trainer battle pics)

**Status: IN-REVIEW.** Vader round 3 (the picked salute pose redrawn with perspective) is with the owner. Category B1
(93 pics) and B4 (professor portrait).

**Read [STYLE-GUIDE.md](STYLE-GUIDE.md) first**: pose, perspective and pixel rules from the 93
vanilla pics, a review checklist, and the owner's feedback log. Getting the pose right is the
hard part of this category; the format is handled by the tool.

Reference: `art/trainers/vader_p4b.yaml` and `vader_p4c.yaml` (round 3) next to `vader_p4.yaml`
(round 2 pick); review sheets `output/trainers/vader-poses-r3.png` (current), `-r2.png`,
`-r1.png` (rejected: front-on).

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

## Drawing a new trainer pic

1. Find the asset in `emerald-sw-db/database/pending_art.csv` (`kind = trainers`) and the
   Star Wars character in `swap_map.csv`.
2. Write `art/trainers/<name>.yaml` (copy `vader_p1.yaml`): `name`, `kit: trainer64`,
   `replaces`, inline `palette` (outline, 3-4 step ramp per material, accents), `legend`.
3. Write a one-line pose brief (STYLE-GUIDE section 1), then block the pose with a `rig:`:
   named joints plus layered `capsule`/`ellipse`/`poly` shapes, back to front, each with a
   2-3 colour ramp; the tool fills, shades (light from the upper left) and outlines each layer
   (see `tools/emerald_sprite/rig.py`). Move joints until the silhouette reads. Then add
   `patches:` (`_` keeps the pixel underneath) for the face, emblems, glints and folds.
   Do not draw trainer pics with `half:` mirroring: it produces flat front-on figures.
4. `cd tools && python -m emerald_sprite build ../art/trainers/<name>.yaml`, then **look at**
   `output/trainers/<name>/preview/zoom.png` (8x editor view with coordinates) and
   `battle.png` (in a battle next to the vanilla pic it replaces, 1x and 2x). Fix until it
   reads at 1x.
5. `python -m emerald_sprite verify ../art/trainers/<name>.yaml`: 2048 bytes of 4bpp, a 32-byte
   palette, identical round trip.
6. Draw 2-3 pose variants and make a review sheet:
   `python -m emerald_sprite compare ../output/trainers/<name>-variants.png a.yaml b.yaml c.yaml`.
   Show the owner, record the pick in `docs/DECISIONS.md`, keep only the picked spec.

## Known gaps

- Lint flags bulk (area) for caped/robed characters and too few single-pixel highlights
  (rig output is smooth; patch accents in).
- `symmetry` (share of pixels equal to their mirror) is linted against vanilla's 0.06-0.33;
  a front-on mirrored figure scores ~0.65.
- `install` copies the PNG only; nothing else is needed for an existing pic.
