"""Creature (Pokémon) battle sprites (kit `creature64`): files, lint, corpus and previews.

Format (pokeemerald `src/data/graphics/pokemon.h`), per species folder graphics/pokemon/<name>/:
- anim_front.png 64x128: front frame on top, the 2nd animation frame below (gMonFrontPic_*)
- front.png      64x64: the still front, identical to the top frame (gMonStillFrontPic_*)
- back.png       64x64: the player-side sprite (gMonBackPic_*)
- normal.pal / shiny.pal: JASC palettes; the PNGs' own colours are ignored by the build.
Placement in battle comes from front_pic_coordinates.h / back_pic_coordinates.h (`y_offset`:
empty rows under the art) and enemy_mon_elevation.h (floating creatures).

Previews:
- zoom.png     front, front2, back at 6x with a grid and coordinates (the LLM's editor view)
- battle.png   ours in a rendered Emerald battle (front on the opponent side, back on yours)
               next to the vanilla species it replaces, at 2x, plus ours at 1x
- anim.gif     front <-> front2 as the battle intro plays it, 4x
- showcase.png zoom + battle + normal/shiny strip, for the owner
"""
from __future__ import annotations

import json
import re
import statistics as st
import struct
from pathlib import Path

from PIL import Image, ImageDraw

from . import palette as pal
from .metrics import frame_metrics, rgba_frame

REPO = Path(__file__).resolve().parents[1]
CORPUS_FILE = REPO / "corpus" / "creature64.json"
KEYS = ("feet", "height", "width", "area", "dark_outline", "orphans", "colours", "symmetry")
OPP_CENTRE = (176, 40)
PLAYER_CENTRE = (72, 80)


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


def species_dir(emerald: Path, sp: str) -> Path:
    return emerald / "graphics/pokemon" / sp


def read_species(emerald: Path, sp: str) -> dict:
    d = species_dir(emerald, sp)
    a = Image.open(d / "anim_front.png")
    b = Image.open(d / "back.png")
    ap, bp = a.load(), b.load()
    fr = lambda px, yo: [[px[x, y + yo] for x in range(64)] for y in range(64)]  # noqa: E731
    out = {"front": fr(ap, 0), "back": fr(bp, 0), "colours": pal.load_jasc(d / "normal.pal")}
    out["front2"] = fr(ap, 64) if a.height >= 128 else out["front"]
    if (d / "shiny.pal").exists():
        out["shiny"] = pal.load_jasc(d / "shiny.pal")
    return out


def y_offsets(emerald: Path, sp: str) -> tuple[int, int, int]:
    """(front y_offset, back y_offset, elevation) of a vanilla species, 0 if unknown."""
    const = "SPECIES_" + re.sub(r"[^A-Z0-9]", "_", sp.upper())
    res = []
    for f in ("front_pic_coordinates.h", "back_pic_coordinates.h"):
        t = (emerald / "src/data/pokemon_graphics" / f).read_text() if (emerald / "src/data/pokemon_graphics" / f).exists() else ""
        m = re.search(rf"\[{const}\]\s*=\s*\{{[^}}]*\.y_offset\s*=\s*(\d+)", t)
        res.append(int(m.group(1)) if m else 0)
    t = (emerald / "src/data/pokemon_graphics/enemy_mon_elevation.h")
    m = re.search(rf"\[{const}\]\s*=\s*(\d+)", t.read_text()) if t.exists() else None
    res.append(int(m.group(1)) if m else 0)
    return tuple(res)


def art_yoff(frames: dict, elevation: int = 0) -> tuple[int, int, int]:
    """The y_offsets the game needs for our art: empty rows under the front / back frame
    (vanilla's front_pic_coordinates.h / back_pic_coordinates.h hold exactly that)."""
    def under(g):
        rows = [y for y, r in enumerate(g) if any(r)]
        return 63 - max(rows) if rows else 0
    return under(frames["front"]), under(frames["back"]), elevation


def metrics(g, colours) -> dict:
    m = frame_metrics(g, colours)
    if m.get("empty"):
        return m
    m["colours"] = len({v for row in g for v in row} - {0})
    m["symmetry"] = symmetry(g)
    return {k: m[k] for k in KEYS if k in m}


def load_corpus() -> dict | None:
    return json.loads(CORPUS_FILE.read_text()) if CORPUS_FILE.exists() else None


def build_corpus(emerald: Path) -> dict:
    rows = {}
    for d in sorted((emerald / "graphics/pokemon").iterdir()):
        if not all((d / f).exists() for f in ("anim_front.png", "back.png", "normal.pal")):
            continue
        s = read_species(emerald, d.name)
        rows[d.name] = metrics(s["front"], s["colours"])

    def pct(vals, p):
        vals = sorted(vals)
        return vals[min(len(vals) - 1, max(0, round(p / 100 * (len(vals) - 1))))]

    out = {"count": len(rows), "p5": {}, "median": {}, "p95": {}, "sprites": rows}
    for k in KEYS:
        vals = [r[k] for r in rows.values() if k in r]
        out["p5"][k], out["median"][k], out["p95"][k] = (round(v, 3) for v in (pct(vals, 5), st.median(vals), pct(vals, 95)))
    CORPUS_FILE.parent.mkdir(exist_ok=True)
    CORPUS_FILE.write_text(json.dumps(out, indent=1))
    return out


def lint(frames: dict, colours, shiny) -> tuple[list[str], list[str], dict]:
    errors, warnings = [], []
    used = set()
    for n, g in frames.items():
        if len(g) != 64 or any(len(r) != 64 for r in g):
            errors.append(f"{n}: frame must be 64x64")
        used |= {v for row in g for v in row}
    if len(used - {0}) > 15:
        errors.append(f"{len(used - {0})} colours used over all frames; 4bpp allows 15 + transparent")
    if shiny is not None and len(shiny) != len(colours):
        errors.append("shiny palette must have the same number of entries as the palette")
    for i, c in enumerate(colours):
        if i and pal.gba15(c) != tuple(c):
            warnings.append(f"palette[{i}] {tuple(c)} is not a multiple of 8 per channel; the GBA shows {pal.gba15(c)}")
    for i in range(1, 16):
        for j in range(i + 1, 16):
            if i in used and j in used and pal.gba15(colours[i]) == pal.gba15(colours[j]):
                warnings.append(f"palette[{i}] and palette[{j}] are the same colour on the GBA")
    m = metrics(frames["front"], colours)
    m["front2_change"] = _change(frames["front"], frames["front2"])
    if m["front2_change"] == 0:
        warnings.append("front2 is identical to front: the battle intro animation will not move")
    corpus = load_corpus()
    if corpus:
        for k, v in m.items():
            if k in corpus["p5"]:
                lo, hi = corpus["p5"][k], corpus["p95"][k]
                if not lo <= v <= hi:
                    warnings.append(f"style: {k} = {v} is outside Emerald's p5-p95 range [{lo}, {hi}]")
    return errors, warnings, m


def _change(a, b) -> float:
    union = diff = 0
    for ra, rb in zip(a, b):
        for va, vb in zip(ra, rb):
            if va or vb:
                union += 1
                diff += va != vb
    return round(diff / union, 3) if union else 0.0


# ---- files ---------------------------------------------------------------------------------

def _indexed(g, colours) -> Image.Image:
    im = Image.new("P", (64, len(g)), 0)
    im.putpalette(pal.flat(colours)[:48])
    px = im.load()
    for y, row in enumerate(g):
        for x, v in enumerate(row):
            px[x, y] = v
    return im


def write_files(frames: dict, colours, shiny, out: Path) -> dict[str, Path]:
    """The exact files a species folder holds."""
    files = {
        "anim_front.png": _indexed(frames["front"] + frames["front2"], colours),
        "front.png": _indexed(frames["front"], colours),
        "back.png": _indexed(frames["back"], colours),
    }
    paths = {}
    for n, im in files.items():
        im.save(out / n, optimize=False)
        paths[n] = out / n
    pal.write_jasc(out / "normal.pal", [tuple(c) for c in colours])
    pal.write_jasc(out / "shiny.pal", [tuple(c) for c in (shiny or colours)])
    paths["normal.pal"], paths["shiny.pal"] = out / "normal.pal", out / "shiny.pal"
    return paths


# ---- previews ------------------------------------------------------------------------------

def zoom(frames: dict, colours, out: Path, z: int = 6) -> Image.Image:
    pad, lab = 22, 16
    names = ["front", "front2", "back"]
    W = pad + len(names) * (64 * z + 12)
    im = Image.new("RGB", (W, lab + 64 * z + 2), (40, 40, 48))
    d = ImageDraw.Draw(im)
    for k, n in enumerate(names):
        x0 = pad + k * (64 * z + 12)
        fr = Image.new("RGB", (64, 64), (115, 197, 164))
        r = rgba_frame(frames[n], colours)
        fr.paste(r, (0, 0), r)
        im.paste(fr.resize((64 * z, 64 * z), Image.NEAREST), (x0, lab))
        for i in range(0, 65, 8 if z < 6 else 1):
            c = (60, 110, 90) if i % 8 == 0 else (95, 160, 135)
            d.line([(x0 + i * z, lab), (x0 + i * z, lab + 64 * z)], fill=c)
            d.line([(x0, lab + i * z), (x0 + 64 * z, lab + i * z)], fill=c)
        d.text((x0, 2), n, fill=(230, 230, 230))
        for i in range(0, 64, 8):
            d.text((x0 + i * z + 1, lab + 1), str(i), fill=(20, 40, 30))
    for i in range(0, 64, 4):
        d.text((2, lab + i * z + 1), str(i), fill=(160, 160, 170))
    im.save(out)
    return im


def battle_scene(front, back, colours, emerald: Path, yoff=(0, 0, 0)) -> Image.Image:
    bg = _battle_bg(emerald)
    f = rgba_frame(front, colours)
    bg.paste(f, (OPP_CENTRE[0] - 32, OPP_CENTRE[1] - 32 + yoff[0] - yoff[2]), f)
    b = rgba_frame(back, colours)
    bg.paste(b, (PLAYER_CENTRE[0] - 32, PLAYER_CENTRE[1] - 32 + yoff[1]), b)
    d = ImageDraw.Draw(bg)  # keep the text box on top, as the game's BG layer order does
    d.rectangle([0, 112, 239, 159], fill=(40, 80, 104))
    d.rectangle([2, 114, 237, 157], outline=(248, 248, 248))
    d.rectangle([4, 116, 235, 155], fill=(40, 80, 104), outline=(208, 160, 64))
    return bg


def battle(frames, colours, out: Path, emerald: Path, replaces: str | None, yoff) -> Image.Image:
    scenes = [("ours", battle_scene(frames["front"], frames["back"], colours, emerald, yoff))]
    if replaces and species_dir(emerald, replaces).exists():
        v = read_species(emerald, replaces)
        scenes.append(("vanilla: " + replaces, battle_scene(v["front"], v["back"], v["colours"], emerald, y_offsets(emerald, replaces))))
    gap, lab = 8, 14
    W = gap + len(scenes) * (480 + gap) + 240 + gap
    im = Image.new("RGB", (W, lab + 320 + gap), (24, 24, 30))
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


def anim_gif(frames, colours, out: Path, z: int = 4) -> None:
    imgs = []
    for n in ("front", "front2", "front", "front2", "front"):
        fr = Image.new("RGB", (64, 64), (115, 197, 164))
        r = rgba_frame(frames[n], colours)
        fr.paste(r, (0, 0), r)
        imgs.append(fr.resize((64 * z, 64 * z), Image.NEAREST))
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=[400, 250, 250, 250, 900], loop=0)


def shiny_strip(frames, colours, shiny, z: int = 3) -> Image.Image:
    cells = [("normal", colours), ("shiny", shiny or colours)]
    im = Image.new("RGB", (len(cells) * 2 * (64 * z + 6) + 6, 64 * z + 20), (24, 24, 30))
    d = ImageDraw.Draw(im)
    x = 6
    for name, cols in cells:
        for n in ("front", "back"):
            fr = Image.new("RGB", (64, 64), (115, 197, 164))
            r = rgba_frame(frames[n], cols)
            fr.paste(r, (0, 0), r)
            im.paste(fr.resize((64 * z, 64 * z), Image.NEAREST), (x, 16))
            d.text((x, 2), f"{name} {n}", fill=(230, 230, 230))
            x += 64 * z + 6
    return im


def showcase(out_dir: Path, strip: Image.Image) -> None:
    parts = [Image.open(out_dir / "zoom.png")]
    if (out_dir / "battle.png").exists():
        parts.append(Image.open(out_dir / "battle.png"))
    parts.append(strip)
    W = max(p.width for p in parts)
    H = sum(p.height for p in parts) + 8 * (len(parts) - 1)
    im = Image.new("RGB", (W, H), (24, 24, 30))
    y = 0
    for p in parts:
        im.paste(p, (0, y))
        y += p.height + 8
    im.save(out_dir / "showcase.png")


def compare(specs: list, out: Path, emerald: Path | None, colours_of, z: int = 3) -> None:
    """Variant sheet: per spec, front / front2 / back at z, and the battle scene at 1x."""
    lab = 16
    cw = 3 * 64 * z + 16
    W = 8 + len(specs) * cw
    H = lab + 64 * z + 8 + (160 * 2 + 8 if emerald else 0)
    im = Image.new("RGB", (W, H), (24, 24, 30))
    d = ImageDraw.Draw(im)
    for i, s in enumerate(specs):
        cols = colours_of(s)
        x = 8 + i * cw
        d.text((x, 2), s.name, fill=(230, 230, 230))
        for k, n in enumerate(("front", "front2", "back")):
            fr = Image.new("RGB", (64, 64), (115, 197, 164))
            r = rgba_frame(s.frames[n], cols)
            fr.paste(r, (0, 0), r)
            im.paste(fr.resize((64 * z, 64 * z), Image.NEAREST), (x + k * 64 * z, lab))
        if emerald:
            yo = art_yoff(s.frames, int(s.meta.get("elevation", 0)))
            sc = battle_scene(s.frames["front"], s.frames["back"], cols, emerald, yo)
            im.paste(sc.resize((480, 320), Image.NEAREST).crop((0, 0, min(480, cw - 8), 320)), (x, lab + 64 * z + 8))
    im.save(out)
