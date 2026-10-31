# Tool: `walker` (overworld walkers)

**Status: READY** for the 16x32 people kit (category B3). Other kits (32x32 big, 16x16 small,
bike/surf/fishing/field-move sheets, creature walkers A6, dolls/cushions C4) are not built.

Reference: `art/walkers/vader.yaml` -> `output/walkers/vader/` (approved, helmet variant A).

## Drawing a new 16x32 walker

1. Find the asset in `emerald-sw-db/database/pending_art.csv` (`kind = object_events`) to get
   the vanilla file it replaces and the Star Wars character.
2. Pick the NPC palette (`palettes/npc_1..4.pal`) that already holds the character's colours
   (D6). Write `art/walkers/<name>.yaml`, copying `vader.yaml`'s structure: `replaces`,
   `graphics_info`, `palette`, `palette_tag`, `legend`, frames.
3. Draw `down`, `up`, `left` as 16-wide grids, bottom-anchored, feet on row 30 (empty last
   line), top no higher than row 10. Pure black outline; clothes in a 3-step ramp
   (shadow/base/highlight), light from the upper left (D7). Derive step frames with
   `base/shift/patch_y/rows` (D4). For helmeted characters start from Vader's helmet language
   (round dome, pinch at the temples, flare past the shoulders).
4. `cd tools && python -m emerald_sprite build ../art/walkers/<name>.yaml`, then **look at**
   `output/walkers/<name>/preview/zoom.png` and `scene.png` (the sprite next to vanilla walkers
   at 1x-3x). Fix and rebuild until it reads at 1x. Address every lint warning or note in the
   spec why it is accepted.
5. `python -m emerald_sprite verify ../art/walkers/<name>.yaml` must report an identical round trip.
6. Uncertain part (helmet, hair, silhouette)? Draw 2-4 variants and make a review sheet with
   `python -m emerald_sprite compare ../output/walkers/<name>-variants.png a.yaml b.yaml ...`.
7. Commit the spec with `output/walkers/<name>/`. Show the owner `showcase.png` and record
   feedback in `docs/DECISIONS.md`.
