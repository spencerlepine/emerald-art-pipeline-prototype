# sprite-trainer-back-generator (player battle back pics)

**Status: TODO-NEED-TO-BUILD.** Category B2: the player's and partner's back sprites shown on
your side when a battle starts (the ball-throw animation). 8 PNGs.

This folder is reserved so the tool is scoped from day one. When it is built it gets its own
Python package, `requirements.txt`, `DECISIONS.md`, corpus, `art/` and `output/`, and needs
nothing outside this folder except a pokeemerald checkout.

## Format (what the game needs)

- `graphics/trainers/back_pics/<name>.png` (brendan, may, red, leaf, steven, wally, and the
  old Ruby/Sapphire brendan_rs, may_rs): 4 or 5 frames of 64x64 stacked vertically (stand,
  wind-up, throw...), built with `INCGFX_U8(..., ".4bpp")` in `src/data/graphics/trainers.h`.
- One palette per character in `graphics/trainers/palettes/<name>.pal` (JASC, 16 colours,
  index 0 transparent); 6 palettes serve the 8 sheets.
- Frame order and timing: `src/data/trainer_graphics/back_pic_anims.h`.
- GBA rules: indexed PNG, max 16 colours, channels in multiples of 8, sizes in multiples of 8.

## Likely approach (to confirm with the owner on a first mockup)

Repaint: start from the vanilla back sheet closest in costume, remap every palette index to
the character's colours (this keeps the hand-pixelled shading and the throw animation), then
change the head, hair and costume details frame by frame. Drawing these 64x64 figures from
shapes or from scratch did not reach Emerald quality for the front pics, which is why repaint
is the starting point here.
