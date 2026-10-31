# emerald-art-pipeline-prototype

Tools for drawing every piece of Star Wars replacement art for the pokeemerald fork
(`spencerlepine/pokeemerald`) with an LLM, so that each image drops into the game unchanged.
The LLM writes art as grids of palette indices in YAML; the `emerald_sprite` tool turns them
into the exact indexed PNG the game builds from, lints them against measured Emerald style,
and renders previews to iterate on with the owner.

![Vader walker](output/walkers/vader/preview/showcase.png)

## Start here (agents)

1. Read `docs/DECISIONS.md` (why the pipeline is shaped this way) and
   `docs/EMERALD-ART-REQUIREMENTS.md` (what the game accepts).
2. Find the asset's category in **[CHECKLIST.md](CHECKLIST.md)**. It lists every category of
   art in the game, the tool that draws it, and that tool's status.
3. Follow the tool's guide in `pipelines/<tool>/README.md`. Only tools marked **READY** may be
   used at scale; **IN-REVIEW** tools are still being iterated with the owner;
   **TODO-NEED-TO-BUILD** tools don't exist yet.
4. The per-file mapping (which vanilla file becomes which Star Wars character) is in
   `emerald-sw-db/database/pending_art.csv`.

| I need to draw... | Category | Guide | Status |
| --- | --- | --- | --- |
| An overworld walker (16x32 person) | B3 | [pipelines/walker](pipelines/walker/README.md) | READY |
| A trainer battle pic (64x64) | B1 | [pipelines/trainer-front](pipelines/trainer-front/README.md) | READY |
| Anything else | see [CHECKLIST.md](CHECKLIST.md) | - | TODO-NEED-TO-BUILD |

## Layout

| Path | What |
| --- | --- |
| `CHECKLIST.md` | Master list: every asset category, its tool, status, remaining work |
| `catalog/categories.yaml` | Source of the checklist tables (categories, globs into pokeemerald, tools) |
| `pipelines/<tool>/README.md` | Step-by-step guide for one tool / art category |
| `art/<category>/<name>.yaml` | Art sources: what the LLM writes |
| `output/<category>/<name>/` | Built game-ready PNG, `lint.txt`, `metrics.json`, `preview/` |
| `palettes/` | Copies of Emerald's shared palettes |
| `corpus/` | Style metrics measured on vanilla art, one file per kit |
| `tools/emerald_sprite/` | The Python tool (one package, one module per concern) |
| `docs/` | Decisions and the game's format requirements |

## Commands

```bash
pip install -r requirements.txt            # pillow, pyyaml
git clone https://github.com/spencerlepine/pokeemerald ../pokeemerald   # corpus, previews, gbagfx, audit
cd tools
python -m emerald_sprite build   ../art/walkers/vader.yaml    # PNG + previews + lint
python -m emerald_sprite verify  ../art/walkers/vader.yaml    # round-trip through pokeemerald's gbagfx
python -m emerald_sprite install ../art/walkers/vader.yaml    # copy into ../pokeemerald
python -m emerald_sprite compare ../output/x.png a.yaml b.yaml # variant review sheet
python -m emerald_sprite corpus                               # re-measure vanilla walkers
python -m emerald_sprite audit --write                        # re-count every asset, regenerate CHECKLIST.md
```

`EMERALD_DIR` overrides the pokeemerald path (default `../pokeemerald`).

## Workflow with the owner

The owner reviews and approves in chat; the repo is the checkpoint. For each tool: build it,
draw 2-4 mockup variants of a Star Wars character, show the `showcase.png`/`compare` sheet,
iterate, record the pick and the reason in `docs/DECISIONS.md`, then mark the tool READY in
`catalog/categories.yaml` and run `audit --write`.
