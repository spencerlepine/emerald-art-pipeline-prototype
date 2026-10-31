"""creature_sprite CLI (run from the tool folder).

    python -m creature_sprite build   art/rancor_drawn.yaml          # 5 species files + previews + lint
    python -m creature_sprite verify  art/rancor_drawn.yaml          # round-trip through pokeemerald's gbagfx
    python -m creature_sprite install art/rancor_drawn.yaml          # copy into pokeemerald, set y_offsets
    python -m creature_sprite inspect <vanilla.png> out.png          # material map of palette indices
    python -m creature_sprite compare output/x.png a.yaml b.yaml     # side-by-side review sheet
    python -m creature_sprite corpus                                 # re-measure the vanilla fronts

Outputs go to output/<name>/ (name from the spec).

EMERALD_DIR (default: a pokeemerald clone beside any parent folder) points at a pokeemerald checkout; it is
read for splice parts, the style corpus, battle previews and gbagfx, and written only by
`install`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import creature, sheet, spec as spec_mod

TOOL = Path(__file__).resolve().parents[1]
OUT = TOOL / "output"


def out_dir(s) -> Path:
    return OUT / s.name


def emerald_dir() -> Path:
    """EMERALD_DIR, else the first `pokeemerald` folder found beside this tool or any parent
    folder (its game/ subfolder when it has one)."""
    env = os.environ.get("EMERALD_DIR")
    if env:
        return Path(env).resolve()
    for d in TOOL.parents:
        root = d / "pokeemerald"
        if root.is_dir():
            return (root / "game" if (root / "game" / "graphics").exists() else root).resolve()
    return (TOOL.parent / "pokeemerald").resolve()


def report(errors, warnings, m, corpus) -> str:
    lines = [f"ERROR   {e}" for e in errors] + [f"warning {w}" for w in warnings]
    lines.append("")
    lines.append(f"{'metric':<14}{'this':>8}{'Emerald p5':>12}{'median':>8}{'p95':>8}")
    for k, v in m.items():
        if corpus and k in corpus["median"]:
            lines.append(f"{k:<14}{v:>8}{corpus['p5'][k]:>12}{corpus['median'][k]:>8}{corpus['p95'][k]:>8}")
        else:
            lines.append(f"{k:<14}{v:>8}")
    return "\n".join(lines)


def shiny_palette(s):
    sh = s.meta.get("shiny")
    if not sh:
        return None
    cols = [tuple(int(v) for v in c) for c in sh]
    return cols + [(0, 0, 0)] * (16 - len(cols))


def cmd_build(a) -> int:
    s = spec_mod.load(a.spec)
    out = out_dir(s)
    (out / "preview").mkdir(parents=True, exist_ok=True)
    colours = sheet.spec_palette(s)
    shiny = shiny_palette(s)
    paths = creature.write_files(s.frames, colours, shiny, out)
    errors, warnings, m = creature.lint(s.frames, colours, shiny)
    if not shiny:
        warnings.append("no `shiny:` palette; shiny.pal is a copy of normal.pal")
    yo = creature.art_yoff(s.frames, int(s.meta.get("elevation", 0)))
    m["y_offset_front"], m["y_offset_back"] = yo[0], yo[1]
    creature.zoom(s.frames, colours, out / "preview" / "zoom.png")
    creature.anim_gif(s.frames, colours, out / "preview" / "anim.gif")
    em = emerald_dir()
    if (em / "graphics/battle_environment").exists():
        creature.battle(s.frames, colours, out / "preview" / "battle.png", em, s.replaces, yo)
    else:
        print(f"note: no pokeemerald at {em}; skipped battle.png (set EMERALD_DIR)")
    creature.showcase(out / "preview", creature.shiny_strip(s.frames, colours, shiny))
    text = report(errors, warnings, m, creature.load_corpus() or {})
    (out / "lint.txt").write_text(text + "\n")
    (out / "metrics.json").write_text(json.dumps(m, indent=1))
    print(f"wrote {', '.join(sorted(paths))} and previews in {(out / 'preview').relative_to(TOOL)}")
    print(text)
    return 1 if errors else 0


def cmd_corpus(a) -> int:
    c = creature.build_corpus(emerald_dir())
    print(f"measured {c['count']} vanilla creature fronts -> {creature.CORPUS_FILE.relative_to(TOOL)}")
    for k in c["median"]:
        print(f"  {k:<14} p5 {c['p5'][k]:>7}  median {c['median'][k]:>7}  p95 {c['p95'][k]:>7}")
    return 0


def _gbagfx() -> Path:
    g = emerald_dir() / "tools/gbagfx/gbagfx"
    if not g.exists():
        subprocess.run(["make", "-s", "-C", str(g.parent)], check=True)
    return g


def cmd_verify(a) -> int:
    """As src/data/graphics/pokemon.h: each PNG -> .4bpp, normal/shiny.pal -> .gbapal."""
    from PIL import Image

    s = spec_mod.load(a.spec)
    out = out_dir(s)
    g = _gbagfx()
    ok_all = True
    with tempfile.TemporaryDirectory() as t:
        for name, expect in (("anim_front.png", 4096), ("front.png", 2048), ("back.png", 2048)):
            bpp, back = Path(t) / (name + ".4bpp"), Path(t) / (name + ".back.png")
            gp = Path(t) / "n.gbapal"
            subprocess.run([str(g), str(out / "normal.pal"), str(gp)], check=True)
            subprocess.run([str(g), str(out / name), str(bpp)], check=True)
            subprocess.run([str(g), str(bpp), str(back), "-width", "8", "-palette", str(gp)], check=True)
            same = list(Image.open(out / name).getdata()) == list(Image.open(back).getdata())
            size = bpp.stat().st_size
            print(f"gbagfx: {name} -> {size} bytes of 4bpp (expect {expect}); round-trip {'identical' if same else 'DIFFERS'}")
            ok_all &= same and size == expect
        for p in ("normal.pal", "shiny.pal"):
            gp = Path(t) / (p + ".gbapal")
            subprocess.run([str(g), str(out / p), str(gp)], check=True)
            print(f"gbagfx: {p} -> {gp.stat().st_size} bytes (expect 32)")
            ok_all &= gp.stat().st_size == 32
    return 0 if ok_all else 1


def cmd_install(a) -> int:
    """Copy the five files into graphics/pokemon/<replaces>/ and set its y_offsets."""
    s = spec_mod.load(a.spec)
    if not s.replaces:
        print("spec has no `replaces:`")
        return 1
    em = emerald_dir()
    dst = em / "graphics/pokemon" / s.replaces
    for n in ("anim_front.png", "front.png", "back.png", "normal.pal", "shiny.pal"):
        shutil.copyfile(out_dir(s) / n, dst / n)
    yo = creature.art_yoff(s.frames)
    const = "SPECIES_" + re.sub(r"[^A-Z0-9]", "_", s.replaces.upper())
    for f, v in (("front_pic_coordinates.h", yo[0]), ("back_pic_coordinates.h", yo[1])):
        p = em / "src/data/pokemon_graphics" / f
        src = p.read_text()
        new, n = re.subn(rf"(\[{const}\]\s*=\s*\{{[^}}]*\.y_offset\s*=\s*)\d+", rf"\g<1>{v}", src)
        if n == 1:
            p.write_text(new)
            print(f"{f}: {const}.y_offset = {v}")
    if "elevation" in s.meta:
        p = em / "src/data/pokemon_graphics/enemy_mon_elevation.h"
        src = p.read_text()
        if re.search(rf"\[{const}\]", src):
            p.write_text(re.sub(rf"(\[{const}\]\s*=\s*)\d+", rf"\g<1>{int(s.meta['elevation'])}", src))
            print(f"enemy_mon_elevation.h: {const} = {s.meta['elevation']}")
    print(f"copied 5 files -> {dst}")
    return 0


def cmd_compare(a) -> int:
    """Side-by-side review sheet for variants: python -m creature_sprite compare out.png a.yaml b.yaml ..."""
    specs = [spec_mod.load(p) for p in a.specs]
    em = emerald_dir()
    creature.compare(specs, Path(a.out), em if (em / "graphics/battle_environment").exists() else None, sheet.spec_palette)
    print(f"wrote {a.out}")
    return 0


def cmd_inspect(a) -> int:
    """Material map of an indexed PNG: each palette index in a false colour with its number, so
    a splice `remap:` can be written (which index is skin, outline, highlight...)."""
    from PIL import Image, ImageDraw

    im = Image.open(a.png)
    pal = im.getpalette()[:48]
    px = im.load()
    counts = {}
    for y in range(im.height):
        for x in range(im.width):
            counts[px[x, y]] = counts.get(px[x, y], 0) + 1
    false = [(0, 0, 0), (255, 0, 0), (0, 200, 0), (0, 80, 255), (255, 200, 0), (255, 0, 255), (0, 220, 220), (255, 128, 0),
             (128, 0, 255), (0, 128, 64), (160, 80, 40), (255, 160, 200), (120, 120, 120), (200, 255, 120), (0, 0, 128), (255, 255, 255)]
    z = 6
    W = im.width * z * 2 + 260
    out = Image.new("RGB", (W, max(im.height * z, 16 * 22 + 10)), (30, 30, 36))
    real = Image.new("RGB", im.size, (115, 197, 164))
    fc = Image.new("RGB", im.size, (40, 40, 48))
    for y in range(im.height):
        for x in range(im.width):
            v = px[x, y]
            if v:
                real.putpixel((x, y), tuple(pal[v * 3 : v * 3 + 3]))
                fc.putpixel((x, y), false[v])
    out.paste(real.resize((im.width * z, im.height * z), Image.NEAREST), (0, 0))
    out.paste(fc.resize((im.width * z, im.height * z), Image.NEAREST), (im.width * z, 0))
    d = ImageDraw.Draw(out)
    x0 = im.width * z * 2 + 10
    for i in range(16):
        y = 6 + i * 22
        d.rectangle([x0, y, x0 + 16, y + 16], fill=false[i])
        d.rectangle([x0 + 20, y, x0 + 36, y + 16], fill=tuple(pal[i * 3 : i * 3 + 3]))
        d.text((x0 + 42, y + 3), f"{i:>2}  {tuple(pal[i * 3 : i * 3 + 3])}  {counts.get(i, 0)} px", fill=(230, 230, 230))
        print(f"{i:>2} {tuple(pal[i * 3 : i * 3 + 3])!s:<18} {counts.get(i, 0):>5} px")
    out.save(a.out)
    print(f"wrote {a.out}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="creature_sprite")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("build", cmd_build), ("verify", cmd_verify), ("install", cmd_install)):
        sp = sub.add_parser(name)
        sp.add_argument("spec")
        sp.set_defaults(fn=fn)
    sub.add_parser("corpus").set_defaults(fn=cmd_corpus)
    ip = sub.add_parser("inspect")
    ip.add_argument("png")
    ip.add_argument("out")
    ip.set_defaults(fn=cmd_inspect)
    cp = sub.add_parser("compare")
    cp.add_argument("out")
    cp.add_argument("specs", nargs="+")
    cp.set_defaults(fn=cmd_compare)
    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except spec_mod.SpecError as e:
        print(f"spec error: {e}", file=sys.stderr)
        return 2
