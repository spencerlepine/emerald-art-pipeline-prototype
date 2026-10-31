# CLAUDE.md

`README.md` is the entry point. In short:

- Read `docs/DECISIONS.md` and `docs/EMERALD-ART-REQUIREMENTS.md` first. They record why the
  pipeline is shaped this way; don't re-litigate a decision without new evidence, and add new
  decisions there (decision + reason, no history).
- `CHECKLIST.md` is the master list of art categories, tools and remaining work. Its tables are
  generated from `catalog/categories.yaml` by `python -m emerald_sprite audit --write` (run from
  `tools/`); edit the YAML, not the tables. Update the checklist in the same commit as the work.
- Each tool has a guide in `pipelines/<tool>/README.md`. Follow it exactly.
- Art sources live in `art/<category>/`, builds in `output/<category>/<name>/`.
- **Look at** every preview you produce before showing it to the owner.
