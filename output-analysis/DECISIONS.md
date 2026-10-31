# Art pipeline: decisions and why

Source of truth for why the pipeline is built the way it is. Newest decisions at the bottom of
each section. Facts about the game's formats are in `EMERALD-ART-REQUIREMENTS.md`.

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

A sprite is a YAML spec (`sprites/<category>/<name>.yaml`): a `legend` mapping one character
to one palette index, and one 16-wide text grid per frame. Reasons: it is impossible to leave
the palette; the grid is readable and diffable; the LLM sees exactly what it is placing.

## D3. Hand-placed 2D grids, not z-day's 3D-model renderer (2026-10-31)

z-day's `characters/body-sheets` tool ray-marches a text-defined 3D model into sprites. It
works for z-day's 24-32 px chibi with many directions and animations. For Emerald we do not
use it: Emerald walkers are 3 directions x 3 poses of hand-pixelled 16x32 art, and a render
does not read as hand-drawn at that size (the Black walker design reached the same
conclusion). What we did keep from z-day: text-file sources, a fixed shared palette, a build
command that writes the game files plus previews, and "look at every image you produce".

## D4. Step frames are derived from the stand frames (2026-10-31)

A spec frame can be `base: <frame>, shift: 1, patch_y: N, rows: ...`: copy a frame, bob it
down 1 px as Emerald does, and redraw only the legs/arms rows. Or `mirror_of: <frame>`. This
cuts the drawing to 3 stand frames plus a few rows per step and keeps the body identical
across frames, which is what stops walk cycles from wobbling.

## D5. Lint against measured Emerald, not against taste (2026-10-31)

`emerald_sprite build` errors on format breaks (size, >15 colours) and warns when a style
metric falls outside the 5th-95th percentile of the 90 vanilla walkers (`corpus/`). These are
warnings, not errors: a big armoured character may legitimately be wider than any Emerald
NPC. Each accepted deviation is noted in the sprite's spec.

## D6. Characters keep a shared NPC palette; switch palettes before adding one (2026-10-31)

Walkers share four 16-colour NPC palettes. Adding palettes costs OBJ palette slots at runtime,
so a new character first picks the vanilla NPC palette that already has its colours, and the
spec's `palette_tag` moves it there (`install` edits `.paletteTag`/`.paletteSlot`). Vader moves
from Maxie's `NPC_2` (reds) to `NPC_4` (blue-blacks + greys, the palette of Steven and the Aqua
grunts). Recolouring the four NPC palettes themselves is a project-wide art-direction decision
for later (e.g. desert tones for Tatooine).

## D7. "Black" clothing uses Emerald's blue-grey ramp (2026-10-31)

First Vader draft used the near-black `8 16 32` as the armour base: outline and armour merged
into one blob. Emerald draws dark clothes as a blue-grey ramp (`57 74 98` base, `106 139 172`
highlight, `8 16 32` shadow) inside a pure black outline. The second draft follows that and
reads as a helmet at 1x.

## Prototype 1 result: Vader walker (2026-10-31)

`output/vader/vader.png` replaces `team_magma/maxie.png`. Verified: 9 frames, 2304 bytes of 4bpp
through pokeemerald's own gbagfx with an identical round trip; `install` into a scratch copy
of pokeemerald changes only the PNG and Maxie's two palette lines. Not verified: an actual ROM
build (no ARM toolchain in the cloud container).

Known gaps, by the linter and by eye:

- Bulkier than any Emerald NPC (area 274 vs p95 252): cape plus helmet flare. Accepted for
  Vader for now; human to judge.
- Only 9 colours vs Emerald's 10-15, and few single-pixel accents (`orphans` 0.07 vs
  0.10-0.23): reads flatter than vanilla sprites, which use more small highlights.
- Step frames change 40% of pixels vs Emerald's ~70%: arms barely swing under the cape.
- Up view is a plain dome + cape with little detail.

Owner reviewed it as about 90% there; the helmet was redrawn (next section).

## Helmet variants (2026-10-31)

Owner feedback on prototype 1: "about 90% there, the helmet looks a little odd". Three variants
change only the helmet rows (10-19) of the stand frames; body and step frames are inherited.
Review sheet: `output/vader-helmet-variants.png` (`python -m emerald_sprite compare`).

- `vader_a`: round dome, pinch at the temples, skirt flaring past the shoulders. Best
  silhouette, especially from behind.
- `vader_b`: original helmet plus face detail (lit brow ridge, grey cheeks, grill triangle).
  Reads most as Vader's mask from the front.
- `vader_c`: smaller helmet (12 wide, starts row 11) so shoulders show. Closest to vanilla
  proportions, and the only variant inside every size range of the corpus.

A first pass of A (pointed dome) and B (whole face plate in grey) was discarded before review:
the cone read as a hood and the grey plate as one big ring.

**Picked: A** (owner, 2026-10-31). `sprites/people/vader.yaml` is now variant A; B and C
were removed from the repo (they live in git history and in the comparison sheet). For later
helmeted characters, start from A's shape language: round dome, pinch at the temples, flare
past the shoulders, big dark lenses, grey grill.

## D8. The tool enforces; a human judges likeness (2026-10-31)

What the tool guarantees by construction or check: size, frame order, palette indices, colour
count, gbagfx round trip, and Emerald's measurable style ranges. What it cannot judge: whether
the character reads as *that* character, and taste calls (helmet shape, proportions). Those
stay with a human, but cheaply: the LLM produces 2-4 variants of the uncertain part, the human
picks from a `compare` sheet, and the pick plus the reason is recorded here so later sprites
inherit it instead of being asked again.
