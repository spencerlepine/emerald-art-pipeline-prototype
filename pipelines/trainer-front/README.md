# Tool: `trainer-front` (trainer battle pics)

**Status: IN-REVIEW.** Vader mockups (3 poses) are with the owner. Category B1 (93 pics) and
B4 (professor portrait).

Reference: `art/trainers/vader.yaml` -> `output/trainers/vader/`; pose variants
`vader_b.yaml`, `vader_c.yaml`; review sheet `output/trainers/vader-pose-variants.png`.

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
2. Write `art/trainers/<name>.yaml` (copy `vader.yaml`): `name`, `kit: trainer64`,
   `replaces`, inline `palette` (outline, 3-4 step ramp per material, accents), `legend`.
3. Draw the figure. Most front poses are near-symmetric, so draw the **left half** with
   `half:` (lines right-aligned to the centre line), add `mirror_shade` so the right half is a
   step darker (light from the upper left), then draw everything asymmetric with `patches:`
   (`_` keeps the pixel underneath): face details, chest panels, held items, a raised arm.
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

- Lint flags bulk (area) for caped/robed characters and too few single-pixel highlights;
  both mean "less detailed than vanilla", worth fixing before READY.
- `install` copies the PNG only; nothing else is needed for an existing pic.
