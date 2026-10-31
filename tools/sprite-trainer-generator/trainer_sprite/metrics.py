"""Pixel metrics shared by lint and previews: the measurements compared against vanilla."""
from __future__ import annotations

from PIL import Image

from . import palette as pal

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


def rgba_frame(g, colours) -> Image.Image:
    h, w = len(g), len(g[0])
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            if g[y][x]:
                im.putpixel((x, y), tuple(colours[g[y][x]]) + (255,))
    return im
