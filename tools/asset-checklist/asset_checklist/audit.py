"""Asset audit: every PNG in pokeemerald -> exactly one category of catalog/categories.yaml.

    python -m asset_checklist            # print counts, fail on unassigned PNGs
    python -m asset_checklist --write    # also regenerate the tables in CHECKLIST.md (repo root)

Counts come from the pokeemerald checkout (EMERALD_DIR), so the checklist cannot drift from
the game. "Drawn" counts the specs in tools/*/art/ whose `replaces:` falls in the category.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

TOOL = Path(__file__).resolve().parents[1]
REPO = TOOL.parents[1]
CATALOG = TOOL / "catalog" / "categories.yaml"
CHECKLIST = REPO / "CHECKLIST.md"
ROOTS = ("graphics", "data/tilesets")


def _glob_re(g: str) -> re.Pattern:
    out, i = "", 0
    while i < len(g):
        if g.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif g.startswith("**", i):
            out += ".*"
            i += 2
        elif g[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(g[i])
            i += 1
    return re.compile(out + "$")


def load_catalog() -> dict:
    d = yaml.safe_load(CATALOG.read_text())
    for c in d["categories"]:
        c["_res"] = [_glob_re(g) for g in c["files"]]
        c["_ex"] = [_glob_re(g) for g in c.get("exclude", [])]
        if c["tool"] not in d["tools"]:
            raise ValueError(f"{c['id']}: unknown tool {c['tool']}")
    return d


def classify(cat: dict, rel: str) -> str | None:
    for c in cat["categories"]:
        if any(r.match(rel) for r in c["_res"]) and not any(r.match(rel) for r in c["_ex"]):
            return c["id"]
    return None


def drawn_specs() -> dict[str, list[str]]:
    """replaces-path -> spec names, from every tool's specs in tools/<tool>/art/."""
    out: dict[str, list[str]] = defaultdict(list)
    for p in sorted((REPO / "tools").glob("*/art/**/*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        if d.get("replaces"):
            out[d["replaces"]].append(f"{p.relative_to(REPO / 'tools').parts[0]}/{d.get('name', p.stem)}")
    return out


def run(emerald: Path) -> dict:
    cat = load_catalog()
    files: dict[str, list[str]] = defaultdict(list)
    pals: dict[str, int] = defaultdict(int)
    unassigned = []
    for root in ROOTS:
        for p in sorted((emerald / root).rglob("*")):
            rel = p.relative_to(emerald).as_posix()
            if p.suffix == ".png":
                cid = classify(cat, rel)
                (files[cid].append(rel) if cid else unassigned.append(rel))
            elif p.suffix == ".pal":
                cid = classify(cat, rel)
                pals[cid or "?"] += 1
    drawn = drawn_specs()
    return {"catalog": cat, "files": files, "pals": pals, "unassigned": unassigned, "drawn": drawn}


def _tables(r: dict) -> tuple[str, str]:
    cat, files, drawn = r["catalog"], r["files"], r["drawn"]
    by_tool: dict[str, list[dict]] = defaultdict(list)
    for c in cat["categories"]:
        by_tool[c["tool"]].append(c)

    def ndrawn(c) -> int:
        return sum(1 for f in files.get(c["id"], []) if f in drawn)

    t = ["| Tool | Status | Covers | Categories | Files | Drawn | Guide |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for name, tool in cat["tools"].items():
        cs = by_tool.get(name, [])
        n = sum(len(files.get(c["id"], [])) for c in cs)
        d = sum(ndrawn(c) for c in cs)
        guide = f"[{tool['guide']}]({tool['guide']})" if tool.get("guide") else "-"
        t.append(f"| `{name}` | **{tool['status']}** | {tool['covers']} | {', '.join(c['id'] for c in cs) or '-'} | {n} | {d} | {guide} |")

    c_lines = []
    total = total_d = 0
    for fam, fam_name in cat["families"].items():
        cs = [c for c in cat["categories"] if c["family"] == fam]
        if not cs:
            continue
        c_lines += [f"\n### {fam}. {fam_name}\n", "| # | Category | Where it shows | Format | PNGs | .pal | Drawn | Tool | Tool status |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for c in cs:
            n, d = len(files.get(c["id"], [])), ndrawn(c)
            if c["tool"] != "none":
                total, total_d = total + n, total_d + d
            st = c.get("status") or cat["tools"][c["tool"]]["status"]
            c_lines.append(f"| {c['id']} | {c['name']} | {c['where']} | {c['format']} | {n} | {r['pals'].get(c['id'], 0) or ''} | {d} | `{c['tool']}` | {st} |")
    head = (f"**{total} PNGs to draw, {total_d} drawn** across {len(cat['categories'])} categories (unused art excluded). "
            f"{r['pals'].get('?', 0)} `.pal` files sit outside any category (shared UI/misc palettes, owned by the tool that edits that screen).\n")
    return "\n".join(t), head + "\n".join(c_lines)


def write_checklist(r: dict) -> None:
    tools, cats = _tables(r)
    text = CHECKLIST.read_text()
    for tag, body in (("tools", tools), ("categories", cats)):
        pat = re.compile(rf"(<!-- audit:{tag} -->).*?(<!-- /audit:{tag} -->)", re.S)
        text, n = pat.subn(lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), text)
        if n != 1:
            raise ValueError(f"CHECKLIST.md is missing the <!-- audit:{tag} --> markers")
    CHECKLIST.write_text(text)


def print_report(r: dict) -> None:
    cat = r["catalog"]
    for c in cat["categories"]:
        n = len(r["files"].get(c["id"], []))
        print(f"{c['id']:<4} {n:>5}  {c['tool']:<14} {c['name']}")
    print(f"total {sum(len(v) for v in r['files'].values())} PNGs; unassigned {len(r['unassigned'])}")
    for u in r["unassigned"][:50]:
        print(f"  UNASSIGNED {u}")
