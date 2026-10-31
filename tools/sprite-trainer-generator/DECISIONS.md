# sprite-trainer-generator: decisions and why

Why this tool is built the way it is. Read it before changing the tool; don't re-litigate a
decision without new evidence, and add new ones at the bottom (decision + reason). Format facts
are in `README.md`.

## Goal

Draw the Star Wars replacement art for the pokeemerald fork (list: `emerald-sw-db`
`database/pending_art.csv`, every image is `PENDING_ART`) at scale with AI, and have every
output drop into the game unchanged: right size, right frame layout, right palette indices,
and Emerald's hand-pixelled look.

## D1. Pipeline choice: LLM + Python tool first; diffusion LoRA deferred (2026-10-31)

Two options were on the table:

1. **LLM + Python tool.** The LLM writes the sprite as data, a tool renders, enforces and
   checks it, and the LLM iterates from the previews.
2. **Stable Diffusion LoRA** trained on Emerald art, plus a finisher (the design in
   `spencerlepine/black` `.docs/2D-SPRITE-LoRA-PIPELINE-DESIGN.md` and
   `WALKER-SPRITE-PIPELINE-DESIGN.md`, written for Pokémon Black).

We start with option 1. Reasons:

- **Size decides it.** A walker frame is 16x32 with ~226 opaque pixels, a tile is 8x8, an item
  icon 24x24. At that size every pixel is a deliberate choice, which is where an LLM writing
  an index grid is strong and where diffusion is weakest (it paints at 1024 px and has to be
  snapped down, which is what the Black design's whole finisher exists to repair).
- **The constraints are exact, not stylistic.** Shared 16-colour NPC palettes, fixed frame
  order, feet on row 30. A grid of palette indices meets them by construction.
- **Option 2's guard rails are option 1's tool.** Any LoRA output still needs palette
  snapping, layout, lint and previews. Building those first is not throwaway work; it becomes
  the LoRA finisher if we ever need one.
- **Data is thin for a LoRA here.** Emerald has 90 people walkers. The Black design had 758
  walker sets and still chose diffusion only for keyframes.
- **No GPU or SD setup exists yet**, so option 2 cannot be tested now.

When to revisit: if the 64x64 categories (Pokémon fronts/backs, trainer pics: about 400
species + 101 trainers) fail human review with option 1. Larger, painterly sprites are where
diffusion has a real edge.

## D2. The LLM writes palette-index grids, not RGB and not code (2026-10-31)

A sprite is a YAML spec (`art/<name>.yaml`): a `legend` mapping one character
to one palette index, and one 16-wide text grid per frame. Reasons: it is impossible to leave
the palette; the grid is readable and diffable; the LLM sees exactly what it is placing.

## D3. Lint against measured Emerald, not against taste (2026-10-31)

`build` errors on format breaks (size, >15 colours) and warns when a style
metric falls outside the 5th-95th percentile of the 90 vanilla walkers (`corpus/`). These are
warnings, not errors: a big armoured character may legitimately be wider than any Emerald
NPC. Each accepted deviation is noted in the sprite's spec.

## D4. "Black" clothing uses Emerald's blue-grey ramp (2026-10-31)

First Vader draft used the near-black `8 16 32` as the armour base: outline and armour merged
into one blob. Emerald draws dark clothes as a blue-grey ramp (`57 74 98` base, `106 139 172`
highlight, `8 16 32` shadow) inside a pure black outline. The second draft follows that and
reads as a helmet at 1x.

## D5. The tool enforces; a human judges likeness (2026-10-31)

What the tool guarantees by construction or check: size, frame order, palette indices, colour
count, gbagfx round trip, and Emerald's measurable style ranges. What it cannot judge: whether
the character reads as *that* character, and taste calls (helmet shape, proportions). Those
stay with a human, but cheaply: the LLM produces 2-4 variants of the uncertain part, the human
picks from a `compare` sheet, and the pick plus the reason is recorded here so later sprites
inherit it instead of being asked again.

## D6. Trainer pics: inline palette, mirrored halves, battle-scene preview (2026-10-31)

Trainer front pics (kit `trainer64`) carry their own 16-colour palette in the PNG, because
pokeemerald builds the `.gbapal` from the PNG itself. So the spec's `palette:` may be an
inline list instead of a shared file. A 64x64 grid is 4,096 cells, too many to place one by
one reliably, and front poses are near-symmetric: a frame can be written as its left half
(`half:`), mirrored, darkened one ramp step on the right (`mirror_shade`, keeps light from the
upper left), then corrected with `patches:` for everything asymmetric. Lint compares against
the 93 vanilla pics (`corpus/trainer64.json`). The deciding preview is `battle.png`: the pic in
a rendered Emerald battle (real tall-grass background, player back pic, text box) next to the
vanilla pic it replaces, at 1x and 2x.

## Trainer prototype 1: Vader battle pic, round 1 (2026-10-31)

Replaces `magma_leader_maxie.png` (matches the Vader walker that replaces Maxie's). Three pose
variants on one body: A saber lit and held down at his side, B Force choke with the arm raised,
C two-handed guard with the blade raised. Sheet: `output/vader-pose-variants.png`.
All three round-trip through gbagfx (2048 bytes + 32-byte palette). A first draft with a
tent-shaped cape and a 50 px wide helmet was discarded before review: it read as a box. Known
gaps: still bulkier than vanilla (area 1,822 vs p95 1,534, cape) and fewer single-pixel
highlights than Emerald artists use.

Owner review of round 1: "about 60%... very flat, looks very unnatural in this perspective...
they're not gonna be standing perfectly straight up facing the camera... I like the lightsaber
on A". Round 1 specs were removed (sheet kept as `output/vader-poses-r1.png`).

## D7. Trainer pics are posed with a rig, then hand-patched; `half:` is not for trainers (2026-10-31)

Vanilla trainer pics are 3/4 views in organic poses (lint `symmetry` 0.06-0.33); writing 4,096
cells by hand pushed the LLM to a mirrored, front-on figure (0.65) that the owner rejected.
A frame can now be a `rig:`: named joints plus layered capsule/ellipse/poly shapes, each
filled, shaded from the upper left with its 2-3 colour ramp and outlined, back to front, so
overlapping near limbs get Emerald's interior lines for free. The LLM then hand-places the
identity details with `patches:`. This keeps D2 (the LLM writes data, the tool cannot leave the
palette) while letting a pose be changed by moving a few joints, which is what owner iteration
on poses needs. The judgement that the tool cannot make lives in
`STYLE-GUIDE.md` (pose, perspective, craft rules from all 93 vanilla
pics, review checklist, feedback log). `symmetry` was added to lint so a flat front-on figure
is flagged before the owner sees it.

## Trainer prototype 1: Vader battle pic, round 2 (2026-10-31)

Four rig-posed 3/4 poses, all turned toward the player: P1 advance with the lit saber angled
low toward the player (round 1 A's saber, which the owner liked), P2 Force grip with the saber
low behind, P3 lunging high guard, P4 salute with the blade raised. Sheet:
`output/vader-poses-r2.png`. Palette brightened (D4 again: dark armour needs a strong
blue-grey highlight to separate from the cape). Known gaps: area over vanilla's p95 (the cape),
few single-pixel accents, rig shading still smoother than hand-pixelled vanilla.

## Trainer prototype 1: Vader battle pic, round 3 (2026-10-31)

Owner picked P4 (salute) but: "the feet are perfectly level... still feels like the camera is
orthogonal". Measured vanilla: the two feet's lowest pixels differ by only 0-2 px in 3 of 4
pics, so the fix is not a height offset; depth is drawn with foot orientation (one in profile,
one toe-on), sloped and curved bands (belt, brim, hem), a centre line pushed to the far side,
and overlaps. Recorded as perspective cues in the style guide. The rig's ellipse gained
`angle`. Round 3: 4b (subtle) and 4c (mid-stride toward the player), with 4 for reference.
P1-P3 removed. Sheet: `output/vader-poses-r3.png`.

## Trainer prototype 1: round 4, style check (2026-10-31)

Owner: "4b is okay, closer to what I'm thinking. Make sure the saber goes over his helmet... get
the layering right." Patches are always applied after the rig, so the face patch had covered
the blade. Rig layers can now be `shape: pixels` (hand-placed pixels at a depth), and faces go
there, before held props. P4 and P4c removed. To confirm the style generalises before marking
the tool READY: Boba Fett (replaces `aqua_admin_m`, Matt), Leia (`steven`), Obi-Wan
(`champion_wallace`), all 3/4 with profile + toe-on feet and sloped bands, symmetry 0.15-0.20.
Sheet: `output/style-check-r4.png`.

## D8. Trainer pics are repaints of vanilla pics, not drawings from scratch (2026-10-31)

Round 4 (rig drawings) was judged "about 70%... still looks really bad". The rig output fell
short of vanilla for reasons a better rig would not fix: capsule-and-ellipse mannequins with
black outlines all round, no cloth folds, no selective outlines, generic hands and faces, and
bulky proportions next to Emerald's slim figures. Those are the things vanilla's artists drew by
hand, and an LLM placing shapes does not reproduce them. So a trainer pic now starts from the
vanilla pic whose pose and costume are closest to the character (`repaint:` in the spec):
every vanilla palette index is remapped to one of our colours (which keeps all of its
shading, folds and anti-aliasing), then rig layers kitbash it: `erase` removes the old head or
prop, `recolour` swaps materials inside a region (sleeves vs chest), shaded shapes and
`pixels` layers add the helmet, buns or saber, `behind: true` tucks a part behind the figure,
and `shape: edge` adds selective outline. `inspect` shows which index is which material.
Trade-offs accepted: poses are limited to the 93 vanilla pics plus what kitbashing can change,
and each pic is visibly a derivative of one vanilla pic (the bases are recorded in the spec).
If the owner needs poses vanilla does not have, that is the case for an image model (see the
round 5 assessment) rather than more rig work.

## Trainer prototype 1: round 5, repaint tool (2026-10-31)

All four redrawn as repaints: Vader from Drake (coat -> cape, hat -> helmet, red saber low),
Boba Fett from Pyramid King Brandon (fatigues -> green chest armour and grey flight suit,
T-visor helmet, rangefinder, jetpack behind), Leia from Glacia (gown -> white, side buns,
silver belt, ball -> blaster), Obi-Wan from Expert M (robes -> beige tunic and brown robe,
blue saber). Sheets: `output/style-check-r5.png`, `repaint-bases-r5.png` (base next to
result). Each spec takes 10-20 layers and a handful of builds; all verify. The old rig specs are
not kept (git history has them). Owner: "those are perfect. You nailed it. Ship that tool!"
The tool is READY, and this category needs no image model.

## D9. No shape-based drawing for final art (2026-10-31)

Owner, after round 5: "the overall finding is that we shouldn't use shape based drawing." Rig
output (capsules, ellipses, polys shaded and outlined by the tool) is not Emerald quality, so no
tool ships art built that way. Shapes may still be used inside a repaint to add a small part
(a saber blade, a bun), but whole figures are either repaints of vanilla art (D8) or drawn
by other means. Creatures cannot be repainted (Star Wars creatures do not share Pokémon
shapes), so the `creature` tool needs its own drawing approach, decided before mockups.

## D10. This tool is standalone (2026-10-31)

Owner: "each tool is standalone... Each tool will be its own thing and have its own pipeline."
This folder holds everything the tool needs: its Python package, `requirements.txt`, this
decision log, the format facts (`README.md`), its corpus, `art/` and `output/`. Nothing is
imported or read from outside it except a pokeemerald checkout (`EMERALD_DIR`). Code it has in
common with other art tools (spec parsing, palette rules, gbagfx verify, metrics) is a copy
trimmed to what this category uses, so this tool can be changed or rewritten on its own.
