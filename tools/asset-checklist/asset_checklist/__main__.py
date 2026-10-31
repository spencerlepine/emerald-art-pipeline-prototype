"""python -m asset_checklist [--write]  (run from tools/asset-checklist/)

EMERALD_DIR (default: pokeemerald next to this repo) is the checkout whose PNGs are counted.
"""
import argparse
import os
import sys
from pathlib import Path

from . import audit


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="asset_checklist")
    p.add_argument("--write", action="store_true", help="regenerate the tables in CHECKLIST.md")
    a = p.parse_args(argv)
    root = audit.REPO.parent / "pokeemerald"
    em = Path(os.environ.get("EMERALD_DIR") or (root / "game" if (root / "game" / "graphics").exists() else root)).resolve()
    r = audit.run(em)
    audit.print_report(r)
    if a.write:
        audit.write_checklist(r)
        print(f"rewrote the generated tables in {audit.CHECKLIST.relative_to(audit.REPO)}")
    return 1 if r["unassigned"] else 0


sys.exit(main())
