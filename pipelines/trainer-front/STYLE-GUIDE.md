# Trainer pic style guide (read before drawing)

What makes an Emerald trainer pic look like an Emerald trainer pic, from a study of all 93
vanilla pics in `graphics/trainers/front_pics/` (contact sheets: run the snippet at the end).
The tool checks format and measurable style; this guide is for everything it cannot check.
Every owner review adds to the feedback log at the bottom: read it, it is the most specific
guidance there is.

## 1. Pose: never stand them straight at the camera

The owner's first review of a front-on, mirrored Vader: "very flat, looks very unnatural...
they're not gonna be standing perfectly straight up facing the camera". Vanilla agrees:
lint's `symmetry` metric is 0.06-0.33 on vanilla pics, 0.65 on that draft.

- **Turn the body 3/4 toward the viewer's left** (the player stands bottom-left in battle).
  About 9 in 10 vanilla pics do this: Maxie, Archie, Steven, grunts, gym leaders. The face
  turns with the body or slightly more.
- **Near side vs far side.** Turned left, the character's *left* side (viewer's right) is
  nearer the camera: that shoulder is lower-forward and wider, that arm overlaps the torso.
  The far side (viewer's left) is narrower, partly hidden, drawn first (behind) and a ramp
  step darker.
- **Weight on one leg, feet staggered.** Feet are never side by side on one row: the near foot
  is lower in the frame and the far foot higher or kicked forward. Knees bend. Wide stances
  for fighters (Brawly, grunts, Black Belt), contrapposto for calm characters (Steven,
  Wallace, Lady).
- **Arms do something.** Throwing or holding a ball, fist raised, hand on hip, pointing at
  the player, holding a prop (net, fishing rod, umbrella, staff). One arm usually reaches
  toward the viewer's left; the other is bent. Never two arms hanging straight down.
- **Show the character's personality in one gesture.** Archie: hands on hips, chest out.
  Maxie: hand on hip, turned away, aloof. Black Belt: martial-arts stance. Battle Girl:
  mid-kick. Pick the single most recognisable gesture of the Star Wars character and build the
  pose around it (Vader: lightsaber, Force grip, cape).
- **Negative space.** Gaps between arms and torso and between the legs keep the silhouette
  readable at 1x. A pose where everything is glued together reads as a blob.

## 2. Perspective and proportion

- Camera slightly above eye level looking down a little: tops of shoulders and hats visible,
  the far foot sits higher on the page than the near foot.
- Adults are about 4-4.5 heads tall in 62 px: head 12-15 px, top of head on rows 1-8, feet on
  rows 60-63 (lint: `top`, `feet`). Kids and chibi characters are 3-3.5 heads.
- Use the frame: vanilla figures are 29-57 px wide (median 41). A prop or a flung arm may
  touch the frame edge; the figure itself is roughly centred, slightly right of centre.
- Hands and heads are drawn a little large; they carry the gesture and the identity.

## 3. Pixel craft

- **Outline**: near-black, about 88% of edge pixels (lint `dark_outline`). Interior lines
  where a near limb crosses the body are what make the 3/4 pose read; the rig draws them.
  Selective outline (a dark shade of the local colour instead of black) on lit edges is
  allowed and common in vanilla.
- **Light from the upper left**, always. Each material gets a 3-step ramp (shadow, base,
  highlight) plus an occasional sheen pixel on the most lit point (helmet top, knee, boot).
- **Single-pixel accents**: vanilla has 11-23% isolated pixels (lint `orphans`): eye glints,
  buttons, fabric folds, sparkle. Rig output is too smooth until these are patched in.
- **13-15 colours.** Budget: outline 1, transparent 1, two or three 3-step ramps for the main
  materials, then accents. Dark costumes (Archie, Steven, Vader) use a blue-grey ramp with a
  strong highlight, not near-black fills (see D7): a black figure is a blob in battle.
- **Colours multiples of 8**, and no two that collapse to the same GBA colour (lint warns).

## 4. How to draw one (with the tool)

1. Write a one-line **pose brief** in the spec comment: facing, weight, gesture, prop, mood.
2. Block the pose with a `rig:` (joints + layered shapes): place hips, feet, shoulders and
   head first, then the arms. Order layers back to front: cape/hair behind, far leg, far arm
   (if behind), torso, near leg, near arm, head, anything held toward the camera. Far-side
   layers use the darker ramp.
3. Build and look at `zoom.png` and `battle.png`. Fix the *pose* by moving joints until the
   silhouette alone (squint at the 1x battle view) says who it is and what they are doing.
4. Only then add `patches:` for identity details: face, emblems, buttons, glints, folds.
5. Check lint: `symmetry` must be in range; explain any other accepted warning in the spec.
6. Draw 3-4 **genuinely different** poses (not the same pose with a different arm) and send
   a `compare` sheet. Ask the owner a specific question, not "do you like it?".

## 5. Review checklist (before showing the owner)

- [ ] Turned 3/4, not front-on; `symmetry` within 0.06-0.33.
- [ ] Feet staggered, weight readable, at least one arm doing something.
- [ ] Silhouette identifies the character at 1x in `battle.png`.
- [ ] Light from the upper left on every part; far side darker than near side.
- [ ] Face/identity details hand-placed, not left to the rig.
- [ ] 13-15 colours, dark outline, a few single-pixel accents.
- [ ] `verify` round trip identical.

## Feedback log (owner reviews, newest last)

- **2026-10-31, Vader round 1** (front-on, mirrored half-grid; poses: saber down, Force choke,
  two-handed guard): "about 60%... very flat, looks very unnatural in this perspective...
  be more ambitious with the positioning... I like the lightsaber on A." Lessons: 3/4 turn,
  organic pose, the lit saber held low (round 1 A) is liked. Led to the rig, the `symmetry`
  lint and this guide.
- **2026-10-31, Vader round 2** (rig-posed 3/4): four poses sent (advance with saber low,
  Force grip, high guard, salute). Awaiting review.

## Contact sheet of the vanilla pics

```python
# from the pokeemerald root; writes vanilla_0..2.png, 32 pics each at 3x
from PIL import Image, ImageDraw; import glob
fs = sorted(glob.glob('graphics/trainers/front_pics/*.png'))
for part in range(0, len(fs), 32):
    im = Image.new('RGB', (8 * 196, 4 * 206), (115, 197, 164)); d = ImageDraw.Draw(im)
    for i, f in enumerate(fs[part:part + 32]):
        s = Image.open(f); x, y = (i % 8) * 196, (i // 8) * 206
        mask = Image.new('L', s.size); mask.putdata([255 if v else 0 for v in s.getdata()])
        rgba = s.convert('RGBA'); rgba.putalpha(mask); big = rgba.resize((192, 192), Image.NEAREST)
        im.paste(big, (x, y + 12), big)
        d.text((x + 2, y), f.split('/')[-1][:-4], fill=(0, 0, 0))
    im.save(f'vanilla_{part // 32}.png')
```
