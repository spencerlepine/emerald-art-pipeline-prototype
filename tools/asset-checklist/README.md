# asset-checklist

Counts every PNG in a pokeemerald checkout, assigns each to exactly one art category from
`catalog/categories.yaml`, and regenerates the tables in the repo's master `CHECKLIST.md`
(between the `<!-- audit:... -->` markers). It fails if any PNG fits no category, so a
category cannot be forgotten. "Drawn" counts the specs in any `tools/*/art/` whose
`replaces:` path falls in the category.

```bash
pip install -r requirements.txt     # pyyaml
export EMERALD_DIR=/path/to/pokeemerald/game   # or a pokeemerald clone beside the repo
python -m asset_checklist            # print counts
python -m asset_checklist --write    # also rewrite CHECKLIST.md
```

Edit `catalog/categories.yaml` (categories, globs, tools and their status), never the
generated tables.
