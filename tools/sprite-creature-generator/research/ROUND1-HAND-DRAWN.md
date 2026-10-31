# Round 1: can the LLM draw a creature by hand? (2026-10-31)

Specs: `art/rancor_drawn.yaml` (Rhydon's slot), `art/mynock_drawn.yaml`
(Zubat's slot). Sheet: `output/creature-drawn-r1.png`.

## Method

D6 rules out shape-built figures and the owner ruled out repaints for creatures. So every
pixel was placed by the LLM: Rancor sketched at 32x32 (`sketch:` frame, doubled and
outline-thinned by the tool), then rewritten at 64x64 in row segments with two detail passes;
Mynock written once at 64x64.

## Result

| Creature | Self-rating | Reads as | Falls short on |
| --- | --- | --- | --- |
| Rancor | ~60% | Hunched beast, long arms, underbite, claws: recognisable at 1x | Flat single-tone areas, few form clusters, no texture (a mottling pass read as noise), bulky (area 2,544 vs p95 2,346) |
| Mynock | ~35% | A green ball with a sucker mouth | Wings came out as flat triangles with dotted ribs, not membranes |

Owner's call (D7): an image model for every creature.

## What carries over to the image-model pipeline

- The LLM is good at **layout**: silhouette, pose, where features go, proportions in the size
  class. That is exactly what an init image or ControlNet hint gives a diffusion model. A cheap
  LLM sketch (32x32 `sketch:` frame, 5 minutes) can be the img2img init for canon creatures that
  have no vanilla body to start from, at denoise ~0.6-0.7. Worth testing in phase 4.
- The `creature` tool (build, verify, install, battle preview, lint vs 384 vanilla fronts) is the
  exporter and checker for whatever the model draws.
- `splice:` frames (kitbash vanilla parts) remain available for small fixes after the model.
