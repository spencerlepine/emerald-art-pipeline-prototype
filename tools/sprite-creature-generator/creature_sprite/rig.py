"""Pose rig: a frame drawn as layered, shaded shapes on a joint skeleton, then hand-patched.

Writing a 64x64 figure pixel by pixel makes an LLM fall back to stiff, symmetric, front-on
figures. A rig lets it think like a figure artist first (where are the hips, which foot carries
the weight, which arm is near the camera) and like a pixel artist second (patches):

    front:
      rig:
        light: [-1, -1]          # upper left, as in every Emerald pic
        joints:                  # named points in frame pixels
          head: [27, 10]
          neck: [29, 17]
          ...
        layers:                  # back to front; each is filled, shaded and outlined
          - {shape: poly, pts: [cape_top, [48, 60], [36, 62]], ramp: cdm}
          - {shape: capsule, from: sh_far, to: el_far, r: [3, 3], ramp: cdm}
          - {shape: ellipse, at: head, r: [7, 8], angle: -10, ramp: dmh}
          - {shape: capsule, from: hilt, to: [6, 58], r: [1, 1], ramp: WWW, outline: R}
      patches: [...]             # pixel-level detail on top (face, emblems, highlights)

Repaint helpers (used on top of a `repaint:` vanilla base): `erase: true` on any shape cuts it
out; `recolour: "a:b c:d"` on any shape swaps characters inside it; `shape: edge` with
`chars: "jk"` and `to: d` darkens silhouette pixels of those characters (selective outline);
`behind: true` on a shaded shape paints only still-transparent pixels, so it tucks behind the
base figure (a jetpack over the shoulder, a cape, hair buns behind the head).

Shapes: `pixels` (x, y, rows: hand-placed pixels, `_` keeps; use it for details that must sit
*under* a later layer, e.g. a face the lightsaber passes in front of), `capsule` (from, to, r: [r_from, r_to]), `ellipse` (at, r: [rx, ry], angle: degrees
clockwise), `poly` (pts).
Points are joint names or [x, y]; `offset: [dx, dy]` shifts a whole layer.
`ramp` is 1-3 legend characters dark -> light: shadow, base, highlight. Pixels whose
light-side neighbour is outside the shape get the highlight, pixels near the far edge the
shadow, so every part is lit from `light` consistently. Sheen pixels, faces and emblems are
hand-placed with `patches:` (automatic sheen came out as noise). `outline` (default: the legend's `K`)
is drawn around each layer's silhouette, which also gives the interior lines where a near limb
crosses the body; `outline: none` merges a layer into what is under it.
"""
from __future__ import annotations

import math

LIGHT = (-1, -1)


class RigError(ValueError):
    pass


def _pt(p, joints, off, where):
    if isinstance(p, str):
        if p not in joints:
            raise RigError(f"{where}: unknown joint {p!r}")
        p = joints[p]
    if not (isinstance(p, (list, tuple)) and len(p) == 2):
        raise RigError(f"{where}: a point is a joint name or [x, y], got {p!r}")
    return (float(p[0]) + off[0], float(p[1]) + off[1])


def _seg_dist(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)), t


def _mask(layer, joints, w, h, where):
    off = layer.get("offset", [0, 0])
    shape = layer.get("shape")
    m = set()
    if shape == "capsule":
        a = _pt(layer["from"], joints, off, where)
        b = _pt(layer["to"], joints, off, where)
        r = layer.get("r", [2, 2])
        r0, r1 = (float(r), float(r)) if isinstance(r, (int, float)) else (float(r[0]), float(r[1]))
        for y in range(h):
            for x in range(w):
                d, t = _seg_dist(x + 0.5, y + 0.5, (a[0] + 0.5, a[1] + 0.5), (b[0] + 0.5, b[1] + 0.5))
                if d <= r0 + (r1 - r0) * t + 0.15:
                    m.add((x, y))
    elif shape == "ellipse":
        cx, cy = _pt(layer["at"], joints, off, where)
        rx, ry = (float(v) for v in layer["r"])
        an = math.radians(float(layer.get("angle", 0)))  # clockwise tilt, degrees
        ca, sa = math.cos(an), math.sin(an)
        for y in range(h):
            for x in range(w):
                dx, dy = x - cx, y - cy
                u, v = dx * ca + dy * sa, -dx * sa + dy * ca
                if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0 + 0.08:
                    m.add((x, y))
    elif shape == "poly":
        pts = [_pt(p, joints, off, where) for p in layer["pts"]]
        if len(pts) < 3:
            raise RigError(f"{where}: poly needs 3+ points")
        for y in range(h):
            for x in range(w):
                px, py = x + 0.5, y + 0.5
                inside = False
                j = len(pts) - 1
                for i in range(len(pts)):
                    xi, yi = pts[i][0] + 0.5, pts[i][1] + 0.5
                    xj, yj = pts[j][0] + 0.5, pts[j][1] + 0.5
                    if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                        inside = not inside
                    j = i
                if inside:
                    m.add((x, y))
    else:
        raise RigError(f"{where}: shape must be capsule, ellipse or poly")
    return m


def render(rig: dict, legend: dict[str, int], w: int, h: int, where: str, base=None) -> list[list[int]]:
    """Draw the layers onto `base` (a grid, e.g. a repainted vanilla pic) or an empty frame."""
    joints = rig.get("joints", {})
    lx, ly = rig.get("light", LIGHT)
    g = [list(r) for r in base] if base else [[0] * w for _ in range(h)]
    default_outline = "K" if "K" in legend else None
    for i, layer in enumerate(rig.get("layers", [])):
        lw = f"{where}: layer {i} ({layer.get('name', layer.get('shape'))})"
        if layer.get("shape") == "pixels":  # hand-placed pixels at this depth (`_` = keep)
            x0, y0 = int(layer["x"]), int(layer["y"])
            for dy, ln in enumerate(str(layer["rows"]).strip("\n").split("\n")):
                for dx, ch in enumerate(ln.strip()):
                    if ch == "_":
                        continue
                    if ch not in legend:
                        raise RigError(f"{lw}: character {ch!r} is not in the legend")
                    if 0 <= x0 + dx < w and 0 <= y0 + dy < h:
                        g[y0 + dy][x0 + dx] = legend[ch]
            continue
        if layer.get("shape") == "edge":  # silhouette pixels whose character is in `chars` -> `to`
            on = {legend[c] for c in str(layer["chars"]) if c in legend}
            to = legend[str(layer["to"])]
            src = [list(r) for r in g]
            for y in range(h):
                for x in range(w):
                    if src[y][x] in on and any(not (0 <= x + dx < w and 0 <= y + dy < h) or src[y + dy][x + dx] == 0
                                               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        g[y][x] = to
            continue
        if layer.get("erase"):  # cut the shape out (back to transparent)
            for (x, y) in _mask(layer, joints, w, h, lw):
                if 0 <= x < w and 0 <= y < h:
                    g[y][x] = 0
            continue
        if "recolour" in layer:  # inside the shape, swap characters: "a:b c:d"
            sw = {}
            for pair in str(layer["recolour"]).split():
                a_, b_ = pair.split(":")
                if a_ not in legend or b_ not in legend:
                    raise RigError(f"{lw}: recolour {pair!r} uses a character not in the legend")
                sw[legend[a_]] = legend[b_]
            for (x, y) in _mask(layer, joints, w, h, lw):
                if 0 <= x < w and 0 <= y < h:
                    g[y][x] = sw.get(g[y][x], g[y][x])
            continue
        ramp = layer.get("ramp", "")
        if isinstance(ramp, bool):
            raise RigError(f"{lw}: ramp parsed as a YAML boolean (no/yes/on/off); quote it or pick other characters")
        ramp = str(ramp)
        if not 1 <= len(ramp) <= 3 or any(ch not in legend for ch in ramp):
            raise RigError(f"{lw}: ramp must be 1-3 legend characters, dark -> light")
        outline = layer.get("outline", default_outline)
        if outline in (None, "none"):
            outline = None
        elif outline not in legend:
            raise RigError(f"{lw}: outline {outline!r} not in the legend")
        m = _mask(layer, joints, w, h, lw)
        behind = bool(layer.get("behind"))  # only fill pixels that are still transparent
        snap = [list(r) for r in g] if behind else None
        hl = int(layer.get("highlight", 1))  # px of lit edge
        sh = int(layer.get("shadow", 2))  # px of shaded edge
        shadow, base = ramp[0], ramp[min(1, len(ramp) - 1)]
        light = ramp[2] if len(ramp) > 2 else base
        for (x, y) in m:
            on_edge = outline and any((x + dx, y + dy) not in m for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if on_edge:
                ch = outline
            else:
                # distance (in steps) to the edge toward the light and away from it
                dl = next((t for t in range(1, hl + 2) if (x + lx * t, y + ly * t) not in m), None)
                dd = next((t for t in range(1, sh + 2) if (x - lx * t, y - ly * t) not in m), None)
                if dl is not None and dl <= (hl + 1 if outline else hl):
                    ch = light
                elif dd is not None:
                    ch = shadow
                else:
                    ch = base
            if 0 <= x < w and 0 <= y < h and not (behind and snap[y][x] != 0):
                g[y][x] = legend[ch]
    return g
