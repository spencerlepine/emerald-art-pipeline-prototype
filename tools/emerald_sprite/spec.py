"""Sprite spec files (YAML) -> indexed frames.

A spec is what the LLM writes. It never contains RGB: every character in a grid maps to a
palette *index* through `legend`, so the output cannot leave the palette.

Grids are 16 characters wide and BOTTOM-anchored: the last line of a grid is row 31 of the
frame. Write the stand frames with an empty last line so the feet land on row 30, as every
Emerald walker does.

Step frames are usually derived, not redrawn (a step is ~20% of the pixels):

    down_a:
      base: down        # start from this frame
      shift: 1          # move everything down 1 px (Emerald's step bob)
      patch_y: 24       # replace rows from here down with `rows`
      rows: |
        ...
    down_b:
      mirror_of: down_a # horizontal mirror of another frame

Front-facing art is mostly symmetric, so a frame can be drawn as its left half and mirrored:

    front:
      half: |           # lines are right-aligned to the centre line and may be shorter than
        ....KKKK        #   w/2 (missing pixels on the left are transparent)
      mirror_shade: "h:m m:d"  # optional: recolour the mirrored half (light from the left)
      patches:          # then redraw the asymmetric parts; `_` keeps the pixel underneath
        - {x: 20, y: 30, rows: "KK_K"}

A frame can also be posed with a `rig:` (layered shaded shapes on joints, see rig.py) and then
finished with `patches:`; this is how trainer pics get organic 3/4 poses.

`palette:` is either the name of a file in palettes/ (shared palettes) or an inline list of up
to 16 [r, g, b] colours (own-palette art such as trainer pics); index 0 is transparent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import rig as rig_mod

# Frame layout of sAnimTable_Standard (src/data/object_events/object_event_anims.h):
# 0 face down, 1 face up, 2 face left, 3/4 walk down, 5/6 walk up, 7/8 walk left.
# East is frame 2/7/8 drawn with hFlip, so there is no right-facing art.
KITS = {
    "person16x32": {
        "frame": (16, 32),
        "order": ["down", "up", "left", "down_a", "down_b", "up_a", "up_b", "left_a", "left_b"],
        "stand": ["down", "up", "left"],
        "walk": {  # direction -> (step, stand, step, stand) as sAnim_Go* plays it
            "down": ["down_a", "down", "down_b", "down"],
            "up": ["up_a", "up", "up_b", "up"],
            "left": ["left_a", "left", "left_b", "left"],
        },
    },
    # Trainer battle pic: one 64x64 frame (src/data/trainer_graphics/front_pic_anims.h plays
    # frame 0 only). The palette is the PNG's own (INCGFX ".gbapal" reads it from the PNG).
    "trainer64": {
        "frame": (64, 64),
        "order": ["front"],
        "stand": ["front"],
        "walk": {},
    },
}

Grid = list[list[int]]


@dataclass
class Spec:
    name: str
    kit: str
    palette: str | list
    legend: dict[str, int]
    frames: dict[str, Grid]
    path: Path
    replaces: str | None = None
    palette_tag: str | None = None
    notes: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def w(self) -> int:
        return KITS[self.kit]["frame"][0]

    @property
    def h(self) -> int:
        return KITS[self.kit]["frame"][1]


class SpecError(ValueError):
    pass


def _parse_rows(text: str, legend: dict[str, int], w: int, where: str) -> Grid:
    lines = [ln.rstrip("\n") for ln in text.strip("\n").split("\n")]
    rows = []
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if len(ln) != w:
            raise SpecError(f"{where}: line {i + 1} is {len(ln)} wide, expected {w}: {ln!r}")
        try:
            rows.append([legend[ch] for ch in ln])
        except KeyError as e:
            raise SpecError(f"{where}: line {i + 1}: character {e} is not in the legend") from None
    return rows


def _repaint(rp: dict, legend: dict[str, int], w: int, h: int, where: str) -> Grid:
    """Start from a vanilla pic's pixels, every palette index mapped to one of our characters.

        repaint:
          pic: graphics/trainers/front_pics/expert_m.png   # relative to EMERALD_DIR
          flip: false                                      # mirror horizontally
          offset: [0, 0]                                   # move the whole figure
          remap: {1: K, 2: f, 3: e, ...}                   # vanilla index -> legend character

    Every index the pic uses must be mapped (`python -m emerald_sprite inspect <png>` shows
    which index is which material). Map an index to the transparent character to delete it.
    """
    import os

    from PIL import Image

    emerald = Path(os.environ.get("EMERALD_DIR", Path(__file__).resolve().parents[3] / "pokeemerald"))
    src = emerald / rp["pic"]
    if not src.exists():
        raise SpecError(f"{where}: repaint pic {src} not found (set EMERALD_DIR)")
    im = Image.open(src)
    if im.mode != "P" or im.size != (w, h):
        raise SpecError(f"{where}: repaint pic must be a {w}x{h} indexed PNG")
    remap = {int(k): str(v) for k, v in (rp.get("remap") or {}).items()}
    px = im.load()
    used = {px[x, y] for y in range(h) for x in range(w)} - {0}
    missing = sorted(used - set(remap))
    if missing:
        raise SpecError(f"{where}: repaint remap is missing vanilla indices {missing}")
    for k, ch in remap.items():
        if ch not in legend:
            raise SpecError(f"{where}: repaint remap {k} -> {ch!r}: not in the legend")
    ox, oy = rp.get("offset", [0, 0])
    g = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            v = px[w - 1 - x if rp.get("flip") else x, y]
            tx, ty = x + int(ox), y + int(oy)
            if v and 0 <= tx < w and 0 <= ty < h:
                g[ty][tx] = legend[remap[v]]
    return g


def _transparent(legend: dict[str, int]) -> str:
    for ch, idx in legend.items():
        if idx == 0:
            return ch
    raise SpecError("legend needs a character for index 0 (transparent)")


def _bottom_anchor(rows: Grid, w: int, h: int, where: str) -> Grid:
    if len(rows) > h:
        raise SpecError(f"{where}: {len(rows)} rows, frame is {h} tall")
    return [[0] * w for _ in range(h - len(rows))] + rows


def load(path: str | Path) -> Spec:
    path = Path(path)
    d = yaml.safe_load(path.read_text())
    kit = d.get("kit", "person16x32")
    if kit not in KITS:
        raise SpecError(f"unknown kit {kit!r}; known: {', '.join(KITS)}")
    w, h = KITS[kit]["frame"]
    legend = {str(k): int(v) for k, v in d["legend"].items()}
    for ch, idx in legend.items():
        if len(ch) != 1 or not 0 <= idx <= 15:
            raise SpecError(f"legend entry {ch!r}: {idx} must be one character -> index 0..15")

    if isinstance(d["palette"], list):
        if not 2 <= len(d["palette"]) <= 16 or any(len(c) != 3 or not all(0 <= v <= 255 for v in c) for c in d["palette"]):
            raise SpecError("inline palette: 2-16 entries of [r, g, b], 0-255")
    raw = d["frames"]
    frames: dict[str, Grid] = {}

    def resolve(name: str, stack: tuple[str, ...] = ()) -> Grid:
        if name in frames:
            return frames[name]
        if name in stack:
            raise SpecError(f"frame {name}: circular reference {' -> '.join(stack + (name,))}")
        if name not in raw:
            raise SpecError(f"frame {name} is required by kit {kit} but missing")
        f = raw[name]
        where = f"frame {name}"
        if isinstance(f, str):
            g = _bottom_anchor(_parse_rows(f, legend, w, where), w, h, where)
        elif "repaint" in f:
            g = _repaint(f["repaint"], legend, w, h, where)
            if "rig" in f:
                try:
                    g = rig_mod.render(f["rig"], legend, w, h, where, base=g)
                except rig_mod.RigError as e:
                    raise SpecError(str(e)) from None
        elif "rig" in f:
            try:
                g = rig_mod.render(f["rig"], legend, w, h, where)
            except rig_mod.RigError as e:
                raise SpecError(str(e)) from None
        elif "half" in f:
            lines = [ln.rstrip() for ln in f["half"].strip("\n").split("\n")]
            half = w // 2
            if any(len(ln.strip()) > half for ln in lines):
                raise SpecError(f"{where}: a `half` line is wider than {half}")
            left = _parse_rows("\n".join(ln.strip().rjust(half, _transparent(legend)) for ln in lines), legend, half, where)
            # `mirror_shade` recolours the mirrored (right) half, e.g. "h:m m:d", so light
            # can come from the upper left even though the shape is mirrored.
            shade = {}
            for pair in str(f.get("mirror_shade", "")).split():
                a_, b_ = pair.split(":")
                if a_ not in legend or b_ not in legend:
                    raise SpecError(f"{where}: mirror_shade {pair!r} uses a character not in the legend")
                shade[legend[a_]] = legend[b_]
            g = _bottom_anchor([row + [shade.get(v, v) for v in row[::-1]] for row in left], w, h, where)
        elif "mirror_of" in f:
            g = [row[::-1] for row in resolve(f["mirror_of"], stack + (name,))]
        elif "base" in f:
            base = resolve(f["base"], stack + (name,))
            s = int(f.get("shift", 0))
            g = [[0] * w for _ in range(h)]
            for y in range(h):
                if 0 <= y - s < h:
                    g[y] = list(base[y - s])
            if "rows" in f:
                py = int(f["patch_y"])
                patch = _parse_rows(f["rows"], legend, w, where)
                if py + len(patch) > h:
                    raise SpecError(f"{where}: patch runs past the bottom of the frame")
                for i, row in enumerate(patch):
                    g[py + i] = row
        else:
            raise SpecError(f"{where}: give a grid, `rig:`, `half:`, `base:` or `mirror_of:`")
        if isinstance(f, dict):
            for i, pt in enumerate(f.get("patches") or []):
                px, py = int(pt["x"]), int(pt["y"])
                for dy, ln in enumerate(pt["rows"].strip("\n").split("\n")):
                    for dx, ch in enumerate(ln.strip()):
                        if ch == "_":
                            continue
                        if ch not in legend:
                            raise SpecError(f"{where}: patch {i}: character {ch!r} is not in the legend")
                        if not (0 <= px + dx < w and 0 <= py + dy < h):
                            raise SpecError(f"{where}: patch {i} runs outside the frame at ({px + dx}, {py + dy})")
                        g[py + dy][px + dx] = legend[ch]
        frames[name] = g
        return g

    for name in KITS[kit]["order"]:
        resolve(name)

    return Spec(
        name=d["name"],
        kit=kit,
        palette=d["palette"],
        legend=legend,
        frames=frames,
        path=path,
        replaces=d.get("replaces"),
        palette_tag=d.get("palette_tag"),
        notes=d.get("notes", ""),
        meta=d,
    )
