"""Measure the vanilla creature sprites that an image model would be trained on, and join them
with the Star Wars mapping. Research only: no GPU, no model.

    python measure.py $EMERALD_DIR /path/to/emerald-sw-db/database

Writes vanilla-stats.json (numbers quoted in the research docs) and sw-creature-jobs.csv (one
row per species folder: what replaces it and the facts a prompt/caption can use).
"""
import csv, json, math, re, statistics as st, sys
from collections import Counter
from pathlib import Path
from PIL import Image

E = Path(sys.argv[1]); DB = Path(sys.argv[2]); OUT = Path(__file__).parent


def pal(p):
    v = list(map(int, p.read_text().split()[3:]))
    return [tuple(v[i:i + 3]) for i in range(0, 48, 3)]


def frames(d):
    a = Image.open(d / "anim_front.png"); b = Image.open(d / "back.png")
    ap, bp = a.load(), b.load()
    f = lambda px, yo: [[px[x, y + yo] for x in range(64)] for y in range(64)]
    return f(ap, 0), (f(ap, 64) if a.height >= 128 else None), f(bp, 0)


def box(g):
    pts = [(x, y) for y, r in enumerate(g) for x, v in enumerate(r) if v]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys), len(pts)


def pct(v, p):
    v = sorted(v); return v[min(len(v) - 1, max(0, round(p / 100 * (len(v) - 1))))]


def summ(v):
    return {"p5": pct(v, 5), "p25": pct(v, 25), "median": st.median(v), "p75": pct(v, 75), "p95": pct(v, 95), "min": min(v), "max": max(v)}


species, rows = [], {}
all_cols = set()
for d in sorted((E / "graphics/pokemon").iterdir()):
    if not all((d / f).exists() for f in ("anim_front.png", "back.png", "normal.pal")):
        continue
    fr, f2, bk = frames(d)
    cols = pal(d / "normal.pal"); sh = pal(d / "shiny.pal") if (d / "shiny.pal").exists() else cols
    used = {v for g in (fr, f2 or fr, bk) for r in g for v in r} - {0}
    all_cols |= {cols[i] for i in used} | {sh[i] for i in used}
    bf, bb = box(fr), box(bk)
    change = None
    if f2:
        u = dd = 0
        for ra, rb in zip(fr, f2):
            for a, b in zip(ra, rb):
                if a or b:
                    u += 1; dd += a != b
        change = dd / u
    rows[d.name] = {
        "colours_used": len(used),
        "front_used": len({v for r in fr for v in r} - {0}),
        "back_used": len({v for r in bk for v in r} - {0}),
        "front_w": bf[2] - bf[0] + 1, "front_h": bf[3] - bf[1] + 1, "front_area": bf[4],
        "front_bottom": bf[3], "front_cx": (bf[0] + bf[2]) / 2,
        "back_w": bb[2] - bb[0] + 1, "back_h": bb[3] - bb[1] + 1, "back_area": bb[4],
        "back_touches_bottom": bb[3] == 63,
        "front2_change": None if change is None else round(change, 3),
        "front2_identical": change == 0,
        "back_to_front_area": round(bb[4] / bf[4], 2),
    }

R = list(rows.values())
num = lambda k: [r[k] for r in R if r[k] is not None]
stats = {"species_folders_measured": len(R)}
for k in ("colours_used", "front_used", "back_used", "front_w", "front_h", "front_area", "front_bottom", "front_cx",
          "back_w", "back_h", "back_area", "front2_change", "back_to_front_area"):
    stats[k] = summ(num(k))
stats["back_touches_bottom_share"] = round(sum(r["back_touches_bottom"] for r in R) / len(R), 3)
stats["front2_identical_count"] = sum(r["front2_identical"] for r in R)
stats["distinct_rgb_colours_in_all_creature_palettes"] = len(all_cols)

# Key colour for a training canvas: the candidate furthest (RGB) from every colour Emerald uses.
cands = {"#0000FF": (0, 0, 255), "#FF00FF": (255, 0, 255), "#00FF00": (0, 255, 0), "#00FFFF": (0, 255, 255),
         "#FF0000": (255, 0, 0), "#808080": (128, 128, 128)}
stats["key_colour_min_rgb_distance"] = {
    n: round(min(math.dist(c, x) for x in all_cols), 1) for n, c in cands.items()}

# Facing: compare opaque mass left vs right of the art's centre is not reliable; skipped.

(OUT / "vanilla-stats.json").write_text(json.dumps({"summary": stats, "per_species": rows}, indent=1))

# ---- Star Wars jobs ---------------------------------------------------------------------
ents = {r["id"]: r for r in csv.DictReader(open(DB / "entities.csv")) if r["id"].startswith("species:")}
def folder_of(eid, title):
    n = eid.split(":", 1)[1].replace("-", "_")
    return n
fields = ["species_folder", "national_dex", "emerald_name", "sw_name", "sw_kind", "sw_basis", "planet",
          "description", "datapad_text", "type1", "type2", "body_color", "egg_groups", "height_m", "weight_kg",
          "vanilla_front_w", "vanilla_front_h", "vanilla_front_area", "vanilla_size_class"]
out = []
for eid, r in ents.items():
    f = folder_of(eid, r["emerald_title"])
    v = rows.get(f)
    if not v:
        continue
    basis = r.get("sw_basis", "")
    kind = basis.split(":")[0] if basis else ""
    side = max(v["front_w"], v["front_h"])
    out.append({
        "species_folder": f, "national_dex": r.get("national_dex", ""), "emerald_name": r.get("emerald_title", ""),
        "sw_name": r.get("sw_name", ""), "sw_kind": kind, "sw_basis": basis, "planet": r.get("planet", ""),
        "description": r.get("description", ""), "datapad_text": r.get("datapad_text", "").replace("\\n", " "),
        "type1": r.get("type1", "").replace("type:", ""), "type2": r.get("type2", "").replace("type:", ""),
        "body_color": r.get("body_color", ""), "egg_groups": r.get("egg_groups", ""),
        "height_m": r.get("height_m", ""), "weight_kg": r.get("weight_kg", ""),
        "vanilla_front_w": v["front_w"], "vanilla_front_h": v["front_h"], "vanilla_front_area": v["front_area"],
        "vanilla_size_class": "small" if side < 40 else ("medium" if side < 56 else "large"),
    })
out.sort(key=lambda x: int(x["national_dex"] or 9999))
with open(OUT / "sw-creature-jobs.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(out)
print(json.dumps(stats, indent=1))
print("jobs:", len(out), Counter(o["sw_kind"] for o in out))
