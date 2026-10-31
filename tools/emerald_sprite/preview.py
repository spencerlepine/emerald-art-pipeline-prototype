"""Previews for a human (and the LLM) to judge a sprite.

- zoom.png     every frame at 12x with a pixel grid and row/column numbers (the LLM's
               "editor view": it reads coordinates off this to fix pixels)
- walk.gif     the four directions walking exactly as sAnim_Go* plays them (8 ticks/frame
               at 60 fps, east = mirrored west), 4x
- scene.png    the sprite standing on real Emerald ground (metatiles from the primary
               "general" tileset) next to vanilla walkers, at 1x, 2x and 3x: the only view
               that answers "does it look like it belongs in Emerald?"
"""
from __future__ import annotations

import struct
from pathlib import Path

from PIL import Image, ImageDraw

from .sheet import read_frames
from .spec import KITS

BG = (115, 197, 164)  # Emerald's object-event transparent colour


def rgba_frame(g, colours) -> Image.Image:
    h, w = len(g), len(g[0])
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            if g[y][x]:
                im.putpixel((x, y), tuple(colours[g[y][x]]) + (255,))
    return im


def zoom_sheet(frames: dict, colours, kit: str, out: Path, z: int = 12) -> None:
    order = KITS[kit]["order"]
    w, h = KITS[kit]["frame"]
    pad, label = 24, 16
    W = pad + len(order) * (w * z + 8)
    H = label + h * z + 4
    im = Image.new("RGB", (W, H), (40, 40, 48))
    d = ImageDraw.Draw(im)
    for y in range(0, h, 2):
        d.text((2, label + y * z + 1), str(y), fill=(160, 160, 170))
    for i, n in enumerate(order):
        ox = pad + i * (w * z + 8)
        d.text((ox, 2), f"{i}:{n}", fill=(230, 230, 230))
        fr = Image.new("RGB", (w, h), BG)
        fr.paste(rgba_frame(frames[n], colours), (0, 0), rgba_frame(frames[n], colours))
        im.paste(fr.resize((w * z, h * z), Image.NEAREST), (ox, label))
        for x in range(w + 1):
            d.line([(ox + x * z, label), (ox + x * z, label + h * z)], fill=(90, 150, 125) if x % 4 else (60, 110, 90))
        for y in range(h + 1):
            d.line([(ox, label + y * z), (ox + w * z, label + y * z)], fill=(90, 150, 125) if y % 4 else (60, 110, 90))
    im.save(out)


def walk_gif(frames: dict, colours, kit: str, out: Path, z: int = 4) -> None:
    w, h = KITS[kit]["frame"]
    walk = KITS[kit]["walk"]
    dirs = ["down", "left", "up", "right"]
    imgs = []
    for t in range(4):
        canvas = Image.new("RGB", (len(dirs) * (w + 4) * z, (h + 2) * z), BG)
        for i, dname in enumerate(dirs):
            src = walk["left" if dname == "right" else dname][t]
            fr = rgba_frame(frames[src], colours)
            if dname == "right":
                fr = fr.transpose(Image.FLIP_LEFT_RIGHT)
            big = fr.resize((w * z, h * z), Image.NEAREST)
            canvas.paste(big, ((i * (w + 4) + 2) * z, z), big)
        imgs.append(canvas)
    # 8 ticks at 59.73 fps ~= 134 ms per frame
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=134, loop=0, disposal=2)


# ---- Emerald ground, for the in-context scene -------------------------------------------

def _metatile_renderer(emerald: Path, tileset="data/tilesets/primary/general"):
    ts = emerald / tileset
    tiles = Image.open(ts / "tiles.png")
    tp = tiles.load()
    pals = []
    for i in range(16):
        p = ts / "palettes" / f"{i:02d}.pal"
        vals = list(map(int, p.read_text().split()[3:])) if p.exists() else [0] * 48
        pals.append([tuple(vals[j : j + 3]) for j in range(0, 48, 3)])
    mt = (ts / "metatiles.bin").read_bytes()

    def tile(v, layer_bg):
        idx, hf, vf, pi = v & 0x3FF, v >> 10 & 1, v >> 11 & 1, v >> 12
        im = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        tx, ty = (idx % 16) * 8, (idx // 16) * 8
        for y in range(8):
            for x in range(8):
                if ty + y >= tiles.height:
                    continue
                c = tp[tx + x, ty + y]
                if c == 0 and not layer_bg:
                    continue
                im.putpixel((7 - x if hf else x, 7 - y if vf else y), pals[pi][c] + (255,))
        return im

    def meta(n):
        im = Image.new("RGBA", (16, 16))
        e = struct.unpack("<8H", mt[n * 16 : n * 16 + 16])
        for layer in (0, 1):
            for i, v in enumerate(e[layer * 4 : layer * 4 + 4]):
                t = tile(v, layer == 0)
                im.paste(t, ((i % 2) * 8, (i // 2) * 8), t)
        return im

    return meta


def scene(frames: dict, colours, kit: str, out: Path, emerald: Path, neighbours: list[str]) -> None:
    """Our sprite among vanilla walkers, on grass and on sand, at 1x / 2x / 3x."""
    meta = _metatile_renderer(emerald)
    ground = {"grass": meta(1), "sand": meta(127)}
    cast = []
    for rel in neighbours:
        fr, cols = read_frames(emerald / rel)
        cast.append(rgba_frame(fr[0], cols))
    # layout: vanilla walkers first, then ours (down, left, up), one metatile apart
    cast += [rgba_frame(frames[n], colours) for n in ("down", "left", "up")]
    cols_n = len(cast) + 2
    rows = []
    for gname, gtile in ground.items():
        strip = Image.new("RGB", (cols_n * 16, 48))
        for x in range(cols_n):
            for y in range(3):
                strip.paste(gtile, (x * 16, y * 16))
        for i, fr in enumerate(cast):
            strip.paste(fr, ((i + 1) * 16, 16), fr)  # frame bottom = bottom tile edge, as in game
        rows.append(strip)
    base = Image.new("RGB", (rows[0].width, 48 * len(rows)))
    for i, r in enumerate(rows):
        base.paste(r, (0, 48 * i))
    gap = 8
    W = base.width * (1 + 2 + 3) + gap * 4
    H = base.height * 3 + gap * 2
    final = Image.new("RGB", (W, H), (24, 24, 30))
    x = gap
    for z in (1, 2, 3):
        final.paste(base.resize((base.width * z, base.height * z), Image.NEAREST), (x, gap))
        x += base.width * z + gap
    final.save(out)


def showcase(out_dir: Path) -> None:
    """One image for a human review: frames at 6x on top, the 3x scene crop below."""
    zoom = Image.open(out_dir / "zoom.png")
    parts = [zoom]
    if (out_dir / "scene.png").exists():
        sc = Image.open(out_dir / "scene.png")
        # the 3x panel is the right-most third-ish of scene.png; take it whole
        third = sc.crop((sc.width - (sc.width - 4 * 8) // 2 - 8, 0, sc.width, sc.height))
        parts.append(third)
    W = max(p.width for p in parts)
    H = sum(p.height for p in parts) + 8 * (len(parts) - 1)
    im = Image.new("RGB", (W, H), (24, 24, 30))
    y = 0
    for p in parts:
        im.paste(p, (0, y))
        y += p.height + 8
    im.save(out_dir / "showcase.png")


def compare(specs: list, out: Path, emerald: Path | None = None, z: int = 6) -> None:
    """Variant review sheet: one row per spec, stand frames at z, then the same row at 1x/2x on grass."""
    from .sheet import spec_palette

    ground = _metatile_renderer(emerald)(1) if emerald else None
    rows = []
    for s in specs:
        cols = spec_palette(s)
        frs = [rgba_frame(s.frames[n], cols) for n in ("down", "left", "up")]
        w, h = s.w, s.h
        big = Image.new("RGB", (3 * (w * z + 6), h * z), BG)
        for i, f in enumerate(frs):
            big.paste(f.resize((w * z, h * z), Image.NEAREST), (i * (w * z + 6), 0), f.resize((w * z, h * z), Image.NEAREST))
        small = Image.new("RGB", (3 * 16 + 16, 48), BG)
        if ground:
            for x in range(0, small.width, 16):
                for y in range(0, 48, 16):
                    small.paste(ground, (x, y))
        for i, f in enumerate(frs):
            small.paste(f, (8 + i * 16, 16), f)
        rows.append((s.name, big, small))
    lab = 120
    W = lab + rows[0][1].width + 12 + rows[0][2].width * 3 + 12 + rows[0][2].width * 2
    H = sum(b.height + 10 for _, b, _ in rows)
    im = Image.new("RGB", (W, H), (24, 24, 30))
    d = ImageDraw.Draw(im)
    y = 0
    for name, big, small in rows:
        d.text((6, y + 6), name, fill=(230, 230, 230))
        im.paste(big, (lab, y))
        x = lab + big.width + 12
        s3 = small.resize((small.width * 3, small.height * 3), Image.NEAREST)
        im.paste(s3, (x, y))
        x += s3.width + 12
        im.paste(small.resize((small.width * 2, small.height * 2), Image.NEAREST), (x, y))
        im.paste(small, (x, y + small.height * 2 + 8))
        y += big.height + 10
    im.save(out)
