# CLAUDE.md

Read `output-analysis/DECISIONS.md` and `output-analysis/EMERALD-ART-REQUIREMENTS.md` first.
They record why the pipeline is shaped this way; don't re-litigate a decision without new evidence,
and add new decisions there (decision + reason, no history).

## Drawing a new overworld walker

1. Find the asset in `emerald-sw-db/database/pending_art.csv` (`kind = object_events`) to get
   the vanilla file it replaces and the Star Wars character.
2. Pick the NPC palette (`palettes/npc_1..4.pal`) that already holds the character's colours
   (D6). Write `sprites/people/<name>.yaml`, copying `vader.yaml`'s structure: `replaces`,
   `graphics_info`, `palette`, `palette_tag`, `legend`, frames.
3. Draw `down`, `up`, `left` as 16-wide grids, bottom-anchored, feet on row 30 (empty last
   line), top no higher than row 10. Pure black outline; clothes in a 3-step ramp
   (shadow/base/highlight), light from the upper left (D7). Derive step frames with
   `base/shift/patch_y/rows` (D4).
4. `python -m emerald_sprite build ...`, then **look at** `output/<name>/preview/zoom.png` and
   `scene.png` (the sprite next to vanilla walkers at 1x-3x). Fix and rebuild until it reads at
   1x. Address every lint warning or note in the spec why it is accepted.
5. `python -m emerald_sprite verify ...` must report an identical round trip.
6. Commit the spec with `output/<name>/`. Show the owner `showcase.png` and record feedback.
