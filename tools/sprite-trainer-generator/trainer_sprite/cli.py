"""trainer_sprite CLI (run from the tool folder).

    python -m trainer_sprite build   art/vader.yaml              # PNG + previews + lint report
    python -m trainer_sprite verify  art/vader.yaml              # round-trip through pokeemerald's gbagfx
    python -m trainer_sprite install art/vader.yaml              # copy into a pokeemerald checkout
    python -m trainer_sprite inspect <vanilla.png> out.png       # material map of a pic's palette indices
    python -m trainer_sprite compare output/x.png a.yaml b.yaml  # side-by-side review sheet
    python -m trainer_sprite corpus                              # re-measure the vanilla trainer pics

Outputs go to output/<name>/ (name from the spec).

EMERALD_DIR (default: a pokeemerald clone beside any parent folder) points at a pokeemerald checkout; it is
read for repaint bases, the style corpus, battle previews and gbagfx, and written only by
`install`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import sheet, spec as spec_mod, trainer

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


def cmd_build(a) -> int:
    s = spec_mod.load(a.spec)
    out = out_dir(s)
    (out / "preview").mkdir(parents=True, exist_ok=True)
    png = out / f"{s.name}.png"
    sheet.build_sheet(s).save(png, optimize=False)
    colours = sheet.spec_palette(s)
    g = s.frames["front"]
    errors, warnings, m = trainer.lint(g, colours)
    trainer.zoom(g, colours, out / "preview" / "zoom.png")
    em = emerald_dir()
    if (em / "graphics/battle_environment").exists():
        trainer.battle(g, colours, out / "preview" / "battle.png", em, s.replaces)
    else:
        print(f"note: no pokeemerald at {em}; skipped battle.png (set EMERALD_DIR)")
    trainer.showcase(out / "preview")
    text = report(errors, warnings, m, trainer.load_corpus() or {})
    (out / "lint.txt").write_text(text + "\n")
    (out / "metrics.json").write_text(json.dumps(m, indent=1))
    print(f"wrote {png.relative_to(TOOL)} and previews in {(out / 'preview').relative_to(TOOL)}")
    print(text)
    return 1 if errors else 0


def cmd_corpus(a) -> int:
    c = trainer.build_corpus(emerald_dir())
    print(f"measured {c['count']} vanilla trainer pics -> {trainer.CORPUS_FILE.relative_to(TOOL)}")
    for k in c["median"]:
        print(f"  {k:<14} p5 {c['p5'][k]:>7}  median {c['median'][k]:>7}  p95 {c['p95'][k]:>7}")
    return 0


def _gbagfx() -> Path:
    g = emerald_dir() / "tools/gbagfx/gbagfx"
    if not g.exists():
        subprocess.run(["make", "-s", "-C", str(g.parent)], check=True)
    return g


def cmd_verify(a) -> int:
    """As src/data/graphics/trainers.h: png -> .4bpp (no metatile args) and png -> .gbapal,
    then back to PNG; indices and GBA colours must match."""
    s = spec_mod.load(a.spec)
    png = out_dir(s) / f"{s.name}.png"
    g = _gbagfx()
    with tempfile.TemporaryDirectory() as t:
        bpp, gpal, back = Path(t) / "x.4bpp", Path(t) / "x.gbapal", Path(t) / "back.png"
        subprocess.run([str(g), str(png), str(bpp)], check=True)
        subprocess.run([str(g), str(png), str(gpal)], check=True)
        subprocess.run([str(g), str(bpp), str(back), "-width", "8", "-palette", str(gpal)], check=True)
        a_g, a_c = trainer.read_pic(png)
        b_g, b_c = trainer.read_pic(back)
        size, psize = bpp.stat().st_size, gpal.stat().st_size
    ok = a_g == b_g and [tuple(x >> 3 for x in c) for c in a_c] == [tuple(x >> 3 for x in c) for c in b_c]
    print(f"gbagfx: {png.name} -> {size} bytes of 4bpp (expect 2048) + {psize}-byte palette (expect 32); "
          f"round-trip {'identical' if ok else 'DIFFERS'}")
    return 0 if ok and size == 2048 and psize == 32 else 1


def cmd_install(a) -> int:
    """Copy the pic over the vanilla file it replaces (the palette travels inside the PNG)."""
    s = spec_mod.load(a.spec)
    if not s.replaces:
        print("spec has no `replaces:`")
        return 1
    em = emerald_dir()
    shutil.copyfile(out_dir(s) / f"{s.name}.png", em / s.replaces)
    print(f"copied -> {em / s.replaces}")
    return 0


def cmd_compare(a) -> int:
    """Side-by-side review sheet for variants: python -m trainer_sprite compare out.png a.yaml b.yaml ..."""
    specs = [spec_mod.load(p) for p in a.specs]
    em = emerald_dir()
    trainer.compare(specs, Path(a.out), em if (em / "graphics/battle_environment").exists() else None, sheet.spec_palette)
    print(f"wrote {a.out}")
    return 0


def cmd_inspect(a) -> int:
    """Material map of an indexed PNG: each palette index in a false colour with its number, so
    a repaint `remap:` can be written (which index is skin, hair, coat, outline...)."""
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
    p = argparse.ArgumentParser(prog="trainer_sprite")
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
