# Master asset checklist

Every image pokeemerald draws, grouped into categories, with the tool that will draw it and
that tool's status. This is the single list of remaining work: update it in the same commit
as the work.

- The tables between `audit` markers are **generated**. Edit `catalog/categories.yaml`, then
  run `cd tools && python -m emerald_sprite audit --write`. The audit walks every PNG under
  pokeemerald's `graphics/` and `data/tilesets/` and fails if one is in no category, so a
  category cannot be forgotten.
- Per-file Star Wars mapping (which file becomes which character) stays in
  `emerald-sw-db/database/pending_art.csv`; this file only tracks categories and tools.
- Counts verified against `spencerlepine/pokeemerald` @ 731ad5bf on 2026-10-31: 4,076 PNGs,
  the same number `pending_art.csv` lists as `PENDING_ART` (plus 5 move animations).

## Status legend

| Status | Meaning |
| --- | --- |
| **TODO-NEED-TO-BUILD** | No tool yet. The category is mapped and counted only |
| **PENDING** | Approach decided and researched; the build waits on something outside this repo (e.g. a GPU for an image model) |
| **IN-REVIEW** | Tool works end to end; mockups are with the owner for feedback in chat |
| **READY** | Owner approved the mockups; agents can draw this category at scale by following the guide |
| **OUT-OF-SCOPE** | Never shown in game, not redrawn |

## Tools

<!-- audit:tools -->
| Tool | Status | Covers | Categories | Files | Drawn | Guide |
| --- | --- | --- | --- | --- | --- | --- |
| `walker` | **READY** | 16x32 people walkers (9-frame standard sheet) | A6, B3, C4 | 207 | 1 | [pipelines/walker/README.md](pipelines/walker/README.md) |
| `trainer-front` | **READY** | 64x64 trainer battle pics with their own 16-colour palette | B1, B4 | 95 | 4 | [pipelines/trainer-front/README.md](pipelines/trainer-front/README.md) |
| `trainer-back` | **TODO-NEED-TO-BUILD** | Player/partner battle back sprites (4-5 frame throw sheets) | B2 | 8 | 0 | - |
| `creature` | **PENDING** | Creature (Pokémon) battle front + 2nd anim frame, back, normal/shiny palettes | A1, A2, A5 | 1262 | 0 | [pipelines/creature/README.md](pipelines/creature/README.md) |
| `icon` | **TODO-NEED-TO-BUILD** | Small fixed-size stills: item icons, berries, decorations, balls, type labels, creature party icons, footprints | A3, A4, C1, C2, C3, C5, C6 | 1144 | 0 | - |
| `obj-anim` | **TODO-NEED-TO-BUILD** | Small multi-frame OBJ sprite sheets: field effects, door anims, field objects, weather, battle-anim particles | D3, D4, D5, D6, E3, E4 | 513 | 0 | - |
| `tileset` | **TODO-NEED-TO-BUILD** | Overworld biome/building tile sheets, their palettes, metatiles and tile animations; battle backgrounds | D1, D2, E1 | 247 | 0 | - |
| `ui-skin` | **TODO-NEED-TO-BUILD** | Tile-based screens (tiles + tilemap + palette): menus, windows, battle HUD, minigames | D7, D8, E2, F1, F3, F4, F5, F6, F7, F8, F9, F10, H1, H2, H3, H4, H5 | 488 | 0 | - |
| `font` | **TODO-NEED-TO-BUILD** | Bitmap fonts and glyph sheets | F2 | 17 | 0 | - |
| `cutscene` | **TODO-NEED-TO-BUILD** | Title, intro, legendary/ending scenes, evolution and trade backgrounds | G1, G2, G3, G4 | 83 | 0 | - |
| `none` | **OUT-OF-SCOPE** | Unused vanilla art and Japanese-only leftovers: never shown, not redrawn | X1 | 12 | 0 | - |
<!-- /audit:tools -->

## Categories

<!-- audit:categories -->
**4064 PNGs to draw, 5 drawn** across 48 categories (unused art excluded). 3 `.pal` files sit outside any category (shared UI/misc palettes, owned by the tool that edits that screen).

### A. Creatures

| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Creature battle front (2 frames) | Battle (opponent side), Pokédex, summary | front.png 64x64 + anim_front.png 64x128 (2 frames), own palette | 838 | 783 | 0 | `creature` | PENDING |
| A2 | Creature battle back | Battle (your side) | back.png 64x64, same palette as the front | 418 |  | 0 | `creature` | PENDING |
| A3 | Creature party/PC icons | Party menu, PC boxes | icon.png 32x64 (2-frame wiggle), one of 3 shared icon palettes | 417 | 3 | 0 | `icon` | TODO-NEED-TO-BUILD |
| A4 | Creature footprints | Pokédex | 16x16, 1 colour | 387 |  | 0 | `icon` | TODO-NEED-TO-BUILD |
| A5 | Eggs, hatching and special-form extras | Daycare egg, hatch scene, Spinda spots, Unown/Castform/Deoxys forms | egg hatch/shard sheets, spot masks, per-form folders | 6 |  | 0 | `creature` | PENDING |
| A6 | Overworld creature walkers | Overworld (legendaries, follower-style NPC creatures) | 16x16 to 64x64 frames, shared NPC palettes | 23 |  | 0 | `walker` | TODO-NEED-TO-BUILD |

### B. People

| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Trainer battle front pics | Trainer battles, trainer card, Hall of Fame, Battle Frontier | 64x64, 1 frame, own 16-colour palette taken from the PNG | 93 |  | 4 | `trainer-front` | READY |
| B2 | Player battle back pics | Your side when a battle starts (ball throw) | 64x256/64x320 = 4-5 frames of 64x64, palette in graphics/trainers/palettes | 8 | 6 | 0 | `trainer-back` | TODO-NEED-TO-BUILD |
| B3 | People overworld walkers | Overworld NPCs, player, rivals | 16x32 x 9 frames (standard), plus 32x32 big, 16x16 small and special sheets (bike, surf, fish, field move) | 133 | 36 | 1 | `walker` | READY (16x32 kit); other kits TODO-NEED-TO-BUILD |
| B4 | Professor speech portrait | New-game intro | birch 64x64 still + shadow/unused frames | 2 |  | 0 | `trainer-front` | READY |

### C. Items and icons

| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Item icons | Bag, shops, PC | 24x24, own palette (graphics/items/icon_palettes) | 218 | 253 | 0 | `icon` | TODO-NEED-TO-BUILD |
| C2 | Berry pictures | Berry tag, berry blender | 48x48, own palette | 43 |  | 0 | `icon` | TODO-NEED-TO-BUILD |
| C3 | Decoration icons | Secret base decoration menu | 24x24 | 43 | 3 | 0 | `icon` | TODO-NEED-TO-BUILD |
| C4 | Placed dolls and cushions | Secret bases | 16x16 / 32x32 OBJ sprites | 51 |  | 0 | `walker` | TODO-NEED-TO-BUILD |
| C5 | Poké Ball battle sprites | Throw, send-out, capture | 16x48 = 3 frames of 16x16 | 13 |  | 0 | `icon` | TODO-NEED-TO-BUILD |
| C6 | Type and contest-category labels | Summary, Pokédex, move info | 32x16 | 23 | 3 | 0 | `icon` | TODO-NEED-TO-BUILD |

### D. Overworld world (biomes, objects, effects)

| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | Tilesets (biome and building tile sheets) | Every map | tiles.png 128 wide of 8x8 tiles; 16-colour palettes (primary 0-5, secondary 6-12); metatiles.bin + attributes | 89 | 1200 | 0 | `tileset` | TODO-NEED-TO-BUILD |
| D2 | Tileset animations | Water, flowers, waterfalls, lava, TVs, lights | frames of tiles swapped into the tileset at runtime | 137 |  | 0 | `tileset` | TODO-NEED-TO-BUILD |
| D3 | Door animations | Every enterable building | 16x96 (3 frames of 16x32), some 32-wide | 53 |  | 0 | `obj-anim` | TODO-NEED-TO-BUILD |
| D4 | Field effects | Grass rustle, ripples, footprints, sand, ash, emote bubbles, Cut, shadows | 8x8 to 32x32 OBJ frames | 59 | 22 | 0 | `obj-anim` | TODO-NEED-TO-BUILD |
| D5 | Field objects | Boulders, Cut trees, breakable rocks, truck, Mirage Tower, rotating gates, berry trees | 16x16 to 64x64 OBJ frames | 56 |  | 0 | `obj-anim` | TODO-NEED-TO-BUILD |
| D6 | Weather overlays | Rain, snow, ash, fog, sandstorm, bubbles | OBJ frames + scrolling layers | 10 | 4 | 0 | `obj-anim` | TODO-NEED-TO-BUILD |
| D7 | Map name popups | Entering a new area | 80x24 frame styles + outlines | 12 | 1 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| D8 | Region map | Town map, PokéNav map, Fly, Pokédex area | tiles + tilemap, map icons and cursors | 14 | 4 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |

### E. Battle

| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | Battle backgrounds | Behind every battle | tiles + tilemap + anim tiles + palette per environment | 21 | 23 | 0 | `tileset` | TODO-NEED-TO-BUILD |
| E2 | Battle HUD | Health boxes, HP/EXP bars, ball tray, status | OBJ/BG tiles | 32 | 4 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| E3 | Move animation sprites and backgrounds | Every move animation | particle sprites, BG overlays, masks (scripts in data/battle_anim_scripts.s are kept) | 312 | 47 | 0 | `obj-anim` | TODO-NEED-TO-BUILD |
| E4 | Battle transitions | Wild/trainer/leader battle start | BG tiles + OBJ pieces | 23 | 18 | 0 | `obj-anim` | TODO-NEED-TO-BUILD |

### F. Screens and UI

| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | Text windows and frames | Every dialogue/menu box (20 player-selectable frames) | 24x24 frame tiles + palette | 21 | 4 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| F2 | Fonts | All text | glyph sheets 1-2bpp, Latin + Japanese + Braille | 17 |  | 0 | `font` | TODO-NEED-TO-BUILD |
| F3 | Shared interface pieces | Cursors, scroll arrows, status icons, markings, menu info | small OBJ/BG tiles | 18 | 11 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| F4 | Bag, party and summary screens | Start menu screens | full-screen tiles + tilemap; bag pictures 64x64 x 6 pockets | 17 | 8 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| F5 | Pokédex screens | Pokédex | tiles + tilemaps | 9 | 5 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| F6 | PokéNav screens | PokéNav (condition, match call, ribbons) | tiles + tilemaps + OBJ | 48 | 17 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| F7 | PC storage and wallpapers | PC boxes | 16 wallpapers (tiles + tilemap) + menus | 89 | 10 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| F8 | Trainer card, Frontier Pass, diploma | Player ID screens | tiles + tilemaps, badge/medal icons | 13 | 23 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| F9 | Naming, Easy Chat, shop, mail, misc menus | Text entry, shops, mail, wall clock, picture frames | tiles + tilemaps | 50 | 29 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| F10 | Link, wireless and Mystery Gift screens | Trade/record mixing setup, Union Room chat, Wonder Card/News | tiles + tilemaps | 36 | 28 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |

### G. Cutscenes and story screens

| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G1 | Title screen | Boot | logo, version banner, legendary, clouds | 6 | 3 | 0 | `cutscene` | TODO-NEED-TO-BUILD |
| G2 | Intro and credits | Copyright/intro movie, staff roll | BG tiles + OBJ actors | 36 | 15 | 0 | `cutscene` | TODO-NEED-TO-BUILD |
| G3 | Legendary story scene | Rayquaza vs Groudon/Kyogre cutscene | BG tiles + large OBJ actors | 25 | 3 | 0 | `cutscene` | TODO-NEED-TO-BUILD |
| G4 | Evolution, trade and cable car scenes | Evolution, trading, cable car ride | BG tiles + OBJ | 16 | 18 | 0 | `cutscene` | TODO-NEED-TO-BUILD |

### H. Minigames and facilities

| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1 | Contests | Contest halls | audience, meters, interface tiles | 23 | 3 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| H2 | Berry Blender, Berry Crush, Pokéblocks | Berry minigames, Pokéblock case/feeding | tiles + OBJ | 20 | 19 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| H3 | Link minigames (Dodrio picking, Pokémon Jump) | Wireless minigames | tiles + OBJ actors | 14 | 4 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| H4 | Game Corner (slots, roulette) | Mauville Game Corner | reels, symbols, boards | 55 | 10 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |
| H5 | Battle Frontier screens | Frontier facilities | Factory rental screen, Arena judgment, Dome tourney | 17 | 11 | 0 | `ui-skin` | TODO-NEED-TO-BUILD |

### X. Not drawn

| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| X1 | Unused vanilla art | Nowhere (left in the source) | - | 12 | 7 | 0 | `none` | OUT-OF-SCOPE |
<!-- /audit:categories -->

## Not PNGs, but changed alongside the art

These are not drawn, but a tool has to write them so the art works in game.

| Data | Where | Written by |
| --- | --- | --- |
| Palettes (`.pal`, JASC) | next to most PNGs; shared NPC palettes in `graphics/object_events/palettes/` | Each tool writes the palette its art uses (counted in the `.pal` column) |
| Tilemaps (`.bin`, 435 files) | screens, battle backgrounds, wallpapers, region map | `ui-skin`, `tileset`, `cutscene` (layout kept, tiles redrawn) |
| Metatiles and attributes (`metatiles.bin`, `metatile_attributes.bin`) | `data/tilesets/**` | `tileset` |
| OBJ graphics info / pic tables | `src/data/object_events/*.h`, `src/data/graphics/*.h` | `walker` `install` (palette tag), later tools as needed |
| Move animation scripts | `data/battle_anim_scripts.s` (354 moves; 349 `KEEP_ANIM`) | Kept; only the sprites they draw (E3) change |
| Map layouts, events, text, music | `data/maps`, `data/layouts`, `src/data/text`, `sound/` | Out of this repo: `emerald-sw-db` and the game fork own them |

## Remaining work (in order)

Work one tool at a time: build it, show the owner mockups in chat, iterate, mark READY.

1. [x] Audit every asset category, generate this checklist (2026-10-31).
2. [x] Restructure the repo: `art/<category>/`, `output/<category>/`, `pipelines/<tool>/`, `catalog/`.
3. [x] `walker` 16x32 people kit: Vader approved.
4. [x] `trainer-front`: **READY**. Rebuilt as a repaint tool (D13) after the rig drawings were judged 70%; round 5 (Vader, Boba Fett, Leia, Obi-Wan) approved by the owner ("those are perfect"). No image model needed for this category. Style guide: `pipelines/trainer-front/STYLE-GUIDE.md`.
5. [ ] `trainer-back`: player throw sheets (needs the player character decided).
6. [ ] `creature`: battle front (2 frames) + back + shiny palette.
7. [ ] `icon`: item icons first (218), then berries, decorations, balls, type labels; derive party icons and footprints from creature fronts.
8. [ ] `walker` extra kits: 32x32 big, 16x16 small, bike/surf/fish/field-move sheets, creature walkers.
9. [ ] `tileset`: one biome first (e.g. a desert secondary tileset for Tatooine) with palettes, metatiles and animations; then battle backgrounds.
10. [ ] `obj-anim`: field effects, doors, field objects, weather, move-animation particles, transitions.
11. [ ] `ui-skin`: text windows and map popups first (seen constantly), then menus, battle HUD, minigames.
12. [ ] `font`: only if a Star Wars font style is wanted; otherwise keep vanilla.
13. [ ] `cutscene`: title screen, intro, legendary scene.
14. [ ] Draw every category at scale once its tool is READY.
