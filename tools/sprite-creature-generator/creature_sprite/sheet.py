"""Write and read Emerald-format sprite sheets (indexed PNG, frames side by side)."""
from __future__ import annotations

from PIL import Image

from . import palette as pal
from .spec import KITS, Spec

def spec_palette(spec: Spec) -> list[tuple[int, int, int]]:
    """16 colours: the spec's inline list padded with black."""
    cols = [tuple(int(v) for v in c) for c in spec.palette]
    return cols + [(0, 0, 0)] * (16 - len(cols))


def frames_to_image(frames: list[list[list[int]]], colours) -> Image.Image:
    h, w = len(frames[0]), len(frames[0][0])
    im = Image.new("P", (w * len(frames), h), 0)
    im.putpalette(pal.flat(colours))
    px = im.load()
    for i, g in enumerate(frames):
        for y in range(h):
            for x in range(w):
                px[i * w + x, y] = g[y][x]
    return im


def build_sheet(spec: Spec) -> Image.Image:
    """The exact PNG pokeemerald wants: indexed, 16-entry palette, index 0 = transparent."""
    order = KITS[spec.kit]["order"]
    im = frames_to_image([spec.frames[n] for n in order], spec_palette(spec))
    # Keep only 16 palette entries, as Emerald's own PNGs do (gbagfx reads indices only,
    # but a 16-entry palette keeps the file honest in image editors and in Porymap).
    im.putpalette(pal.flat(spec_palette(spec))[:48])
    return im
