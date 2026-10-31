# CLAUDE.md

`README.md` is the entry point. In short:

- Read `docs/DECISIONS.md` and `docs/EMERALD-ART-REQUIREMENTS.md` first. They record why the
  pipeline is shaped this way; don't re-litigate a decision without new evidence, and add new
  decisions there (decision + reason, no history).
- Every tool is a standalone folder in `tools/<tool>/` (D16): its own package, requirements,
  README, corpus, `art/` and `output/`. Tools share no code; copy rather than import across
  tools. Run a tool from inside its folder and follow its `README.md` exactly.
- `CHECKLIST.md` is the master list of art categories, tools and remaining work. Its tables are
  generated from `tools/asset-checklist/catalog/categories.yaml` by
  `python -m asset_checklist --write` (run from `tools/asset-checklist/`); edit the YAML, not
  the tables. Update the checklist in the same commit as the work.
- **Look at** every preview you produce before showing it to the owner.
