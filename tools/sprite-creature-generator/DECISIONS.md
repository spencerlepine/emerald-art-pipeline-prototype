# sprite-creature-generator: decisions and why

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

## D4. The tool enforces; a human judges likeness (2026-10-31)

What the tool guarantees by construction or check: size, frame order, palette indices, colour
count, gbagfx round trip, and Emerald's measurable style ranges. What it cannot judge: whether
the character reads as *that* character, and taste calls (helmet shape, proportions). Those
stay with a human, but cheaply: the LLM produces 2-4 variants of the uncertain part, the human
picks from a `compare` sheet, and the pick plus the reason is recorded here so later sprites
inherit it instead of being asked again.

## D5. Trainer pics are repaints of vanilla pics, not drawings from scratch (2026-10-31)

_Context for this tool: why repainting worked for trainer pics, and (D6, D7) why it does not carry over to creatures._

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

## D6. No shape-based drawing for final art (2026-10-31)

Owner, after round 5: "the overall finding is that we shouldn't use shape based drawing." Rig
output (capsules, ellipses, polys shaded and outlined by the tool) is not Emerald quality, so no
tool ships art built that way. Shapes may still be used inside a repaint to add a small part
(a saber blade, a bun), but whole figures are either repaints of vanilla art (D5) or drawn
by other means. Creatures cannot be repainted (Star Wars creatures do not share Pokémon
shapes), so the `creature` tool needs its own drawing approach, decided before mockups.

## Creature prototype round 1: hand-drawn (2026-10-31)

The `creature` tool (kit `creature64`) writes all five species files (`anim_front.png`,
`front.png`, `back.png`, `normal.pal`, `shiny.pal`), computes the `y_offset`s and round-trips
through gbagfx. Per D6 and the owner's note that Star Wars creatures do not share Pokémon
shapes, round 1 drew two creatures pixel by pixel with no vanilla pixels: Rancor (Rhydon's slot,
~60%: reads at 1x but flat, clay-like rendering) and Mynock (Zubat's slot, ~35%: geometric
wings). Sheet: `output/creature-drawn-r1.png`; details in
`README.md`. The method for this category is open with the owner. Evidence
for that choice: in `emerald-sw-db` 193 of the 386 species map to "original" creatures written
after their Pokémon (BULBASAUR -> SPROUTLIZ "lizard with a seed bulb on its back"), so a
splice/repaint fits those; the 193 canon/databank creatures (Rancor, Bantha, Tauntaun, droids)
need new shapes. D1's trigger for an image model ("64x64 categories fail review with option 1")
is met for the second group.

## D7. Creatures are drawn by an image model; the build waits on a GPU (2026-10-31)

After round 1 the owner chose an image model for every creature ("we're gonna need stable
diffusion"), over hand-drawing and over a repaint/model hybrid. Reasons: hand-drawing reached
~60% at best; repaints don't fit new shapes; D1's revisit trigger (64x64 categories failing
review) is met. The plan reuses the owner's Black `spritegen` design (SDXL + a LoRA trained on
the game's own sprites + a deterministic finisher), adapted in
`research/EMERALD-PLAN.md`; our `creature` tool is its exporter and checker.
There is no GPU in the agent containers and the owner's machine is an M1 Mac, so the tool is
**PENDING**: research-only until a GPU (rented or owned) is available. All research, old and
new, lives in `research/`.

## D8. This tool is standalone (2026-10-31)

Owner: "each tool is standalone... Each tool will be its own thing and have its own pipeline."
This folder holds everything the tool needs: its Python package, `requirements.txt`, this
decision log, the format facts (`README.md`), its corpus, `art/` and `output/`. Nothing is
imported or read from outside it except a pokeemerald checkout (`EMERALD_DIR`). Code it has in
common with other art tools (spec parsing, palette rules, gbagfx verify, metrics) is a copy
trimmed to what this category uses, so this tool can be changed or rewritten on its own.
