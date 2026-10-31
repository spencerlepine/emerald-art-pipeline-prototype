# sprite-trainer-back-generator (player battle back pics)

**Status: TODO-NEED-TO-BUILD.** Category B2: the player's and partner's back sprites shown on
your side when a battle starts (the ball-throw animation). 8 PNGs.

This folder is reserved so the tool is scoped from day one. When it is built it gets its own
package, `requirements.txt`, corpus, `art/` and `output/` like the other `sprite-*` tools, and
shares no code with them (copy what it needs from `tools/sprite-trainer-generator`).

## What the game needs

- `graphics/trainers/back_pics/<name>.png`: 64x256 or 64x320, i.e. 4 or 5 frames of 64x64
  stacked vertically (stand, wind-up, throw...), one shared palette in
  `graphics/trainers/palettes/<name>.pal` (6 palettes for 8 sheets).
- Frame order and timing come from `src/data/trainer_graphics/back_pic_anims.h`.

## Likely approach

Repaint, as the front tool does (D13): each sheet starts from the vanilla back sheet closest in
costume, every frame remapped through the same palette, then kitbashed per frame. The front
pic of the same character (from `sprite-trainer-generator`) fixes the costume and colours.
Decide this with the owner on a first mockup before building at scale.
