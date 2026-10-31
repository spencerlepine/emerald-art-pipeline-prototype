"""Guard rails: format rules (errors) and style metrics measured against Emerald (warnings).

Format rules come from how pokeemerald loads a walker (see README.md, "Format").
Style metrics are measured on all 90 vanilla 16x32 people walkers; a value outside the
corpus's 5th-95th percentile is a warning, because it means "no Emerald artist did this".
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

from . import palette as pal
from .spec import KITS

CORPUS_FILE = Path(__file__).resolve().parents[1] / "corpus" / "people16x32.json"

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _opaque(g):
    return [(x, y) for y, row in enumerate(g) for x, v in enumerate(row) if v != 0]


def _edge(g, x, y):
    h, w = len(g), len(g[0])
    return any(not (0 <= x + dx < w and 0 <= y + dy < h) or g[y + dy][x + dx] == 0 for dx, dy in N4)


def frame_metrics(g, colours) -> dict:
    px = _opaque(g)
    if not px:
        return {"empty": True}
    xs = [p[0] for p in px]
    ys = [p[1] for p in px]
    edge = [(x, y) for x, y in px if _edge(g, x, y)]
    dark_edge = sum(1 for x, y in edge if pal.luma(colours[g[y][x]]) <= 100) / len(edge)
    h, w = len(g), len(g[0])
    orphans = sum(
        1
        for x, y in px
        if not any(0 <= x + dx < w and 0 <= y + dy < h and g[y + dy][x + dx] == g[y][x] for dx, dy in N4)
    )
    return {
        "top": min(ys),
        "feet": max(ys),
        "height": max(ys) - min(ys) + 1,
        "width": max(xs) - min(xs) + 1,
        "area": len(px),
        "dark_outline": round(dark_edge, 3),
        "orphans": round(orphans / len(px), 3),
    }


def step_change(a, b) -> float:
    """Share of pixels that differ between two frames, over the union of opaque pixels."""
    union = diff = 0
    for ra, rb in zip(a, b):
        for va, vb in zip(ra, rb):
            if va or vb:
                union += 1
                diff += va != vb
    return diff / union if union else 0.0


def sheet_metrics(frames: dict, colours, kit="person16x32") -> dict:
    k = KITS[kit]
    stand = {n: frame_metrics(frames[n], colours) for n in k["stand"]}
    used = {v for g in frames.values() for row in g for v in row} - {0}
    steps = []
    for seq in k["walk"].values():
        steps += [step_change(frames[seq[1]], frames[seq[0]]), step_change(frames[seq[1]], frames[seq[2]])]
    agg = {m: round(st.median(s[m] for s in stand.values()), 3) for m in ("top", "feet", "height", "width", "area", "dark_outline", "orphans")}
    agg["colours"] = len(used)
    agg["step_change"] = round(st.median(steps), 3)
    return {"stand": stand, "summary": agg}


def load_corpus() -> dict | None:
    return json.loads(CORPUS_FILE.read_text()) if CORPUS_FILE.exists() else None


def lint(frames: dict, colours, kit="person16x32") -> tuple[list[str], list[str], dict]:
    errors, warnings = [], []
    w, h = KITS[kit]["frame"]
    for n in KITS[kit]["order"]:
        g = frames[n]
        if len(g) != h or any(len(r) != w for r in g):
            errors.append(f"{n}: frame must be {w}x{h}")
    m = sheet_metrics(frames, colours, kit)
    if m["summary"]["colours"] > 15:
        errors.append(f"{m['summary']['colours']} colours used; a 4bpp sprite has 15 + transparent")
    for n, s in m["stand"].items():
        if s.get("empty"):
            errors.append(f"{n}: empty frame")
            continue
        if s["feet"] != h - 2:
            warnings.append(f"{n}: feet on row {s['feet']}, Emerald stands on row {h - 2} (shadow and grass overlap assume it)")
        if s["top"] < 8:
            warnings.append(f"{n}: art starts on row {s['top']}; vanilla people start on rows 10-15 (taller reads as a giant)")
    corpus = load_corpus()
    if corpus:
        for key, v in m["summary"].items():
            if key not in corpus["p5"]:
                continue
            lo, hi = corpus["p5"][key], corpus["p95"][key]
            if not lo <= v <= hi:
                warnings.append(f"style: {key} = {v} is outside Emerald's p5-p95 range [{lo}, {hi}]")
    return errors, warnings, m


def build_corpus(emerald_dir: str | Path) -> dict:
    """Measure every vanilla 16x32 people walker (9-frame standard layout)."""
    from .sheet import read_frames

    order = KITS["person16x32"]["order"]
    rows = {}
    for f in sorted(Path(emerald_dir, "graphics/object_events/pics/people").rglob("*.png")):
        try:
            frames, colours = read_frames(f)
        except ValueError:
            continue
        if len(frames) != 9:
            continue
        rows[str(f.relative_to(emerald_dir))] = sheet_metrics(dict(zip(order, frames)), colours)["summary"]
    keys = next(iter(rows.values())).keys()

    def pct(vals, p):
        vals = sorted(vals)
        return vals[min(len(vals) - 1, max(0, round(p / 100 * (len(vals) - 1))))]

    out = {"count": len(rows), "p5": {}, "median": {}, "p95": {}, "sprites": rows}
    for k in keys:
        vals = [r[k] for r in rows.values()]
        out["p5"][k], out["median"][k], out["p95"][k] = (round(v, 3) for v in (pct(vals, 5), st.median(vals), pct(vals, 95)))
    CORPUS_FILE.parent.mkdir(exist_ok=True)
    CORPUS_FILE.write_text(json.dumps(out, indent=1))
    return out
