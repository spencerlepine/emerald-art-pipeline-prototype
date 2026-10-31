"""Trainer battle pics (kit `trainer64`): lint, corpus and previews.

Format (pokeemerald `src/data/graphics/trainers.h`): one 64x64 indexed PNG per trainer pic,
converted with `INCGFX_U32(png, ".4bpp.lz")` for the tiles and `INCGFX_U32(png, ".gbapal.lz")`
for the palette, so unlike walkers the colours stored in the PNG ARE the game's palette.
The pic is shown once at (176, 40) centre in battle (`battle_controller_opponent.c`) and on
the trainer card / Hall of Fame / Frontier screens.

Previews:
- zoom.png     the frame at 8x with a grid and row/column numbers (the LLM's editor view)
- battle.png   our pic in a mock Emerald battle (tall-grass background, text box, player back
               pic) next to the vanilla pic it replaces, at 1x and 2x
- showcase.png zoom at 5x + battle at 2x, for the owner
"""
from __future__ import annotations

import json
import statistics as st
import struct
from pathlib import Path

from PIL import Image, ImageDraw

from . import palette as pal
from .metrics import frame_metrics, rgba_frame

REPO = Path(__file__).resolve().parents[1]
CORPUS_FILE = REPO / "corpus" / "trainer64.json"
KEYS = ("top", "feet", "height", "width", "area", "dark_outline", "orphans", "colours", "symmetry")
OPP_TOPLEFT = (144, 8)  # centre (176, 40) - 32 for a size-8 (64x64) pic
PLAYER_TOPLEFT = (48, 48)  # back pic centre (80, 80)


def read_pic(path: Path) -> tuple[list[list[int]], list[tuple[int, int, int]]]:
    im = Image.open(path)
    if im.mode != "P" or im.size != (64, 64):
        raise ValueError(f"{path}: not a 64x64 indexed PNG")
    raw = im.getpalette()[:48]
    px = im.load()
    return [[px[x, y] for x in range(64)] for y in range(64)], [tuple(raw[i : i + 3]) for i in range(0, len(raw), 3)]


def metrics(g, colours) -> dict:
    m = frame_metrics(g, colours)
    m["colours"] = len({v for row in g for v in row} - {0})
    m["symmetry"] = symmetry(g)
    return {k: m[k] for k in KEYS if k in m}


def symmetry(g) -> float:
    """Share of opaque pixels whose mirror image (about the art's own centre) has the same index.
    Vanilla pics are posed in 3/4 view, so this is low; a flat, front-on, mirrored figure scores
    near 1. The metric that would have caught the first, rejected Vader draft."""
    px = [(x, y) for y, row in enumerate(g) for x, v in enumerate(row) if v]
    if not px:
        return 0.0
    xs = [x for x, _ in px]
    c = min(xs) + max(xs)
    same = sum(1 for x, y in px if 0 <= c - x < len(g[0]) and g[y][c - x] == g[y][x])
    return round(same / len(px), 3)


def load_corpus() -> dict | None:
    return json.loads(CORPUS_FILE.read_text()) if CORPUS_FILE.exists() else None


def build_corpus(emerald: Path) -> dict:
    rows = {}
    for f in sorted((emerald / "graphics/trainers/front_pics").glob("*.png")):
        g, cols = read_pic(f)
        rows[f.name] = metrics(g, cols)

    def pct(vals, p):
        vals = sorted(vals)
        return vals[min(len(vals) - 1, max(0, round(p / 100 * (len(vals) - 1))))]

    out = {"count": len(rows), "p5": {}, "median": {}, "p95": {}, "sprites": rows}
    for k in KEYS:
        vals = [r[k] for r in rows.values()]
        out["p5"][k], out["median"][k], out["p95"][k] = (round(v, 3) for v in (pct(vals, 5), st.median(vals), pct(vals, 95)))
    CORPUS_FILE.parent.mkdir(exist_ok=True)
    CORPUS_FILE.write_text(json.dumps(out, indent=1))
    return out


def lint(g, colours) -> tuple[list[str], list[str], dict]:
    errors, warnings = [], []
    if len(g) != 64 or any(len(r) != 64 for r in g):
        errors.append("frame must be 64x64")
    m = metrics(g, colours)
    if m.get("colours", 0) > 15:
        errors.append(f"{m['colours']} colours used; 4bpp allows 15 + transparent")
    for i, c in enumerate(colours):
        if i and pal.gba15(c) != tuple(c):
            warnings.append(f"palette[{i}] {tuple(c)} is not a multiple of 8 per channel; the GBA shows {pal.gba15(c)}")
    used = {v for row in g for v in row}
    for i in range(1, 16):
        for j in range(i + 1, 16):
            if i in used and j in used and pal.gba15(colours[i]) == pal.gba15(colours[j]):
                warnings.append(f"palette[{i}] and palette[{j}] are the same colour on the GBA")
    if m.get("feet", 0) < 60:
        warnings.append(f"art ends on row {m.get('feet')}; vanilla pics run to row 62-63 (cut off by the frame bottom)")
    corpus = load_corpus()
    if corpus:
        for k, v in m.items():
            lo, hi = corpus["p5"][k], corpus["p95"][k]
            if not lo <= v <= hi:
                warnings.append(f"style: {k} = {v} is outside Emerald's p5-p95 range [{lo}, {hi}]")
    return errors, warnings, m


# ---- previews ------------------------------------------------------------------------------

def zoom(g, colours, out: Path, z: int = 8) -> Image.Image:
    pad, lab = 22, 14
    im = Image.new("RGB", (pad + 64 * z + 2, lab + 64 * z + 2), (40, 40, 48))
    d = ImageDraw.Draw(im)
    fr = Image.new("RGB", (64, 64), (115, 197, 164))
    rgba = rgba_frame(g, colours)
    fr.paste(rgba, (0, 0), rgba)
    im.paste(fr.resize((64 * z, 64 * z), Image.NEAREST), (pad, lab))
    for i in range(65):
        c = (60, 110, 90) if i % 8 == 0 else (90, 150, 125)
        if z >= 6 or i % 8 == 0:
            d.line([(pad + i * z, lab), (pad + i * z, lab + 64 * z)], fill=c)
            d.line([(pad, lab + i * z), (pad + 64 * z, lab + i * z)], fill=c)
    for i in range(0, 64, 4):
        d.text((2, lab + i * z + 1), str(i), fill=(160, 160, 170))
        d.text((pad + i * z + 1, 1), str(i), fill=(160, 160, 170))
    im.save(out)
    return im


def _battle_bg(emerald: Path, env: str = "tall_grass") -> Image.Image:
    d = emerald / "graphics/battle_environment" / env
    tiles = Image.open(d / "tiles.png")
    tp = tiles.load()
    vals = list(map(int, (d / "palette.pal").read_text().split()[3:]))
    pals = [[tuple(vals[j * 3 : j * 3 + 3]) for j in range(i * 16, i * 16 + 16)] for i in range(len(vals) // 48)]
    m = (d / "map.bin").read_bytes()
    backdrop = pals[0][1]
    im = Image.new("RGB", (256, 256), backdrop)
    for i in range(1024):
        v = struct.unpack_from("<H", m, i * 2)[0]
        idx, hf, vf, pi = v & 0x3FF, v >> 10 & 1, v >> 11 & 1, v >> 12
        tx, ty = (idx % 16) * 8, (idx // 16) * 8
        for y in range(8):
            for x in range(8):
                c = tp[tx + x, ty + y] if ty + y < tiles.height else 0
                if c:  # palette slots 2-4 hold the environment palette
                    im.putpixel(((i % 32) * 8 + (7 - x if hf else x), (i // 32) * 8 + (7 - y if vf else y)), pals[max(pi - 2, 0)][c])
    im = im.crop((0, 0, 240, 160))
    d2 = ImageDraw.Draw(im)  # Emerald's battle text box (rows 112-159)
    d2.rectangle([0, 112, 239, 159], fill=(40, 80, 104))
    d2.rectangle([2, 114, 237, 157], outline=(248, 248, 248))
    d2.rectangle([4, 116, 235, 155], fill=(40, 80, 104), outline=(208, 160, 64))
    return im


def _player_back(emerald: Path) -> Image.Image | None:
    p = emerald / "graphics/trainers/back_pics/brendan.png"
    if not p.exists():
        return None
    im = Image.open(p)
    cols = pal.load_jasc(emerald / "graphics/trainers/palettes/brendan.pal")
    px = im.load()
    return rgba_frame([[px[x, y] for x in range(64)] for y in range(64)], cols)


def battle_scene(g, colours, emerald: Path) -> Image.Image:
    bg = _battle_bg(emerald)
    pic = rgba_frame(g, colours)
    bg.paste(pic, OPP_TOPLEFT, pic)
    back = _player_back(emerald)
    if back:
        bg.paste(back, PLAYER_TOPLEFT, back)
    return bg


def battle(g, colours, out: Path, emerald: Path, replaces: str | None) -> Image.Image:
    """Ours vs the vanilla pic it replaces, in the same battle, at 2x; plus ours at 1x."""
    scenes = [("ours", battle_scene(g, colours, emerald))]
    if replaces and (emerald / replaces).exists():
        vg, vc = read_pic(emerald / replaces)
        scenes.append(("vanilla: " + Path(replaces).stem, battle_scene(vg, vc, emerald)))
    gap, lab = 8, 14
    W = gap + sum(240 * 2 + gap for _ in scenes) + 240 + gap
    H = lab + 160 * 2 + gap
    im = Image.new("RGB", (W, H), (24, 24, 30))
    d = ImageDraw.Draw(im)
    x = gap
    for name, sc in scenes:
        d.text((x, 1), f"{name} (2x)", fill=(230, 230, 230))
        im.paste(sc.resize((480, 320), Image.NEAREST), (x, lab))
        x += 480 + gap
    d.text((x, 1), "ours (1x)", fill=(230, 230, 230))
    im.paste(scenes[0][1], (x, lab))
    im.save(out)
    return im


def showcase(out_dir: Path) -> None:
    z = Image.open(out_dir / "zoom.png")
    z = z.resize((z.width * 5 // 8, z.height * 5 // 8), Image.NEAREST)
    parts = [z]
    if (out_dir / "battle.png").exists():
        parts.append(Image.open(out_dir / "battle.png"))
    W = sum(p.width for p in parts) + 8 * (len(parts) - 1)
    H = max(p.height for p in parts)
    im = Image.new("RGB", (W, H), (24, 24, 30))
    x = 0
    for p in parts:
        im.paste(p, (x, 0))
        x += p.width + 8
    im.save(out_dir / "showcase.png")


def compare(specs: list, out: Path, emerald: Path | None, colours_of) -> None:
    """Variant sheet: per variant, the pic at 4x and its battle scene at 1x."""
    z = 4
    lab = 16
    cells = []
    for s in specs:
        cols = colours_of(s)
        g = s.frames["front"]
        big = Image.new("RGB", (64 * z, 64 * z), (115, 197, 164))
        r = rgba_frame(g, cols).resize((64 * z, 64 * z), Image.NEAREST)
        big.paste(r, (0, 0), r)
        sc = battle_scene(g, cols, emerald) if emerald else None
        cells.append((s.name, big, sc))
    cw = 64 * z + 8
    W = len(cells) * cw + 8
    H = lab + 64 * z + 8 + (160 + 8 if emerald else 0)
    im = Image.new("RGB", (W, H), (24, 24, 30))
    d = ImageDraw.Draw(im)
    for i, (name, big, sc) in enumerate(cells):
        x = 8 + i * cw
        d.text((x, 2), name, fill=(230, 230, 230))
        im.paste(big, (x, lab))
        if sc:
            im.paste(sc.crop((120, 0, 240, 112)).resize((240, 224), Image.NEAREST).crop((0, 0, 64 * z, 160)), (x, lab + 64 * z + 8))
    im.save(out)
