"""emerald_sprite CLI.

    python -m emerald_sprite build   ../art/walkers/vader.yaml      # PNG + previews + lint report
    python -m emerald_sprite lint    path/to/any_sheet.png          # lint an existing sheet
    python -m emerald_sprite corpus                                 # re-measure vanilla walkers
    python -m emerald_sprite verify  ../art/walkers/vader.yaml      # round-trip through pokeemerald's gbagfx
    python -m emerald_sprite install ../art/walkers/vader.yaml      # copy into a pokeemerald checkout
    python -m emerald_sprite audit [--write]                        # asset categories -> CHECKLIST.md

Outputs go to output/<category>/<name>/, where <category> is the spec's folder under art/.

EMERALD_DIR (default ../pokeemerald next to this repo) points at a pokeemerald checkout; it is
read for the style corpus, scene previews and gbagfx, and written only by `install`.
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

from . import audit as audit_mod
from . import lint as lint_mod
from . import creature, preview, sheet, spec as spec_mod, trainer

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "output"
SCENE_NEIGHBOURS = [  # vanilla walkers shown beside ours, same palette family where possible
    "graphics/object_events/pics/people/steven.png",
    "graphics/object_events/pics/people/team_aqua/aqua_member_m.png",
    "graphics/object_events/pics/people/expert_m.png",
]


def out_dir(s) -> Path:
    return OUT / s.path.resolve().parent.name / s.name


def emerald_dir() -> Path:
    return Path(os.environ.get("EMERALD_DIR", REPO.parent / "pokeemerald")).resolve()


def report(errors, warnings, m, corpus=None) -> str:
    lines = [f"ERROR   {e}" for e in errors] + [f"warning {w}" for w in warnings]
    corpus = corpus if corpus is not None else lint_mod.load_corpus()
    lines.append("")
    lines.append(f"{'metric':<14}{'this':>8}{'Emerald p5':>12}{'median':>8}{'p95':>8}")
    for k, v in m["summary"].items():
        if corpus and k in corpus["median"]:
            lines.append(f"{k:<14}{v:>8}{corpus['p5'][k]:>12}{corpus['median'][k]:>8}{corpus['p95'][k]:>8}")
        else:
            lines.append(f"{k:<14}{v:>8}")
    return "\n".join(lines)


def build_trainer(s, out: Path, png: Path) -> int:
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
    text = report(errors, warnings, {"summary": m}, trainer.load_corpus() or {})
    (out / "lint.txt").write_text(text + "\n")
    (out / "metrics.json").write_text(json.dumps(m, indent=1))
    print(f"wrote {png.relative_to(REPO)} and previews in {(out / 'preview').relative_to(REPO)}")
    print(text)
    return 1 if errors else 0


def shiny_palette(s):
    sh = s.meta.get("shiny")
    if not sh:
        return None
    cols = [tuple(int(v) for v in c) for c in sh]
    return cols + [(0, 0, 0)] * (16 - len(cols))


def build_creature(s, out: Path) -> int:
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
    creature.showcase(out / "preview", creature.shiny_strip(s.frames, colours, shiny))
    text = report(errors, warnings, {"summary": m}, creature.load_corpus() or {})
    (out / "lint.txt").write_text(text + "\n")
    (out / "metrics.json").write_text(json.dumps(m, indent=1))
    print(f"wrote {', '.join(sorted(paths))} and previews in {(out / 'preview').relative_to(REPO)}")
    print(text)
    return 1 if errors else 0


def cmd_build(a) -> int:
    s = spec_mod.load(a.spec)
    out = out_dir(s)
    (out / "preview").mkdir(parents=True, exist_ok=True)
    if s.kit == "creature64":
        return build_creature(s, out)
    im = sheet.build_sheet(s)
    png = out / f"{s.name}.png"
    im.save(png, optimize=False)
    if s.kit == "trainer64":
        return build_trainer(s, out, png)
    colours = sheet.spec_palette(s)
    errors, warnings, m = lint_mod.lint(s.frames, colours, s.kit)
    preview.zoom_sheet(s.frames, colours, s.kit, out / "preview" / "zoom.png")
    preview.walk_gif(s.frames, colours, s.kit, out / "preview" / "walk.gif")
    em = emerald_dir()
    if (em / "data/tilesets/primary/general/tiles.png").exists():
        preview.scene(s.frames, colours, s.kit, out / "preview" / "scene.png", em, SCENE_NEIGHBOURS)
    else:
        print(f"note: no pokeemerald at {em}; skipped scene.png (set EMERALD_DIR)")
    preview.showcase(out / "preview")
    text = report(errors, warnings, m)
    (out / "lint.txt").write_text(text + "\n")
    (out / "metrics.json").write_text(json.dumps(m, indent=1))
    print(f"wrote {png.relative_to(REPO)} and previews in {(out / 'preview').relative_to(REPO)}")
    print(text)
    return 1 if errors else 0


def cmd_lint(a) -> int:
    frames, colours = sheet.read_frames(a.png)
    order = spec_mod.KITS["person16x32"]["order"]
    errors, warnings, m = lint_mod.lint(dict(zip(order, frames)), colours)
    print(report(errors, warnings, m))
    return 1 if errors else 0


def cmd_corpus(a) -> int:
    for what, mod in (("vanilla walkers", lint_mod), ("vanilla trainer pics", trainer), ("vanilla creature fronts", creature)):
        c = mod.build_corpus(emerald_dir())
        print(f"measured {c['count']} {what} -> {mod.CORPUS_FILE.relative_to(REPO)}")
        for k in c["median"]:
            print(f"  {k:<14} p5 {c['p5'][k]:>7}  median {c['median'][k]:>7}  p95 {c['p95'][k]:>7}")
    return 0


def _gbagfx() -> Path:
    g = emerald_dir() / "tools/gbagfx/gbagfx"
    if not g.exists():
        subprocess.run(["make", "-s", "-C", str(g.parent)], check=True)
    return g


def cmd_verify(a) -> int:
    """PNG -> .4bpp exactly as pokeemerald's build does, then back to PNG; indices must match."""
    s = spec_mod.load(a.spec)
    png = out_dir(s) / f"{s.name}.png"
    g = _gbagfx()
    if s.kit == "trainer64":
        return verify_trainer(g, png)
    if s.kit == "creature64":
        return verify_creature(g, out_dir(s))
    with tempfile.TemporaryDirectory() as t:
        bpp = Path(t) / "x.4bpp"
        back = Path(t) / "back.png"
        subprocess.run([str(g), str(png), str(bpp), "-mwidth", "2", "-mheight", "4"], check=True)
        pal_file = Path(t) / "p.gbapal"
        subprocess.run([str(g), str(sheet.PALETTE_DIR / f"{s.palette}.pal"), str(pal_file)], check=True)
        subprocess.run(
            [str(g), str(bpp), str(back), "-mwidth", "2", "-mheight", "4", "-width", str(png_w(png) // 8), "-palette", str(pal_file)],
            check=True,
        )
        a_frames, _ = sheet.read_frames(png)
        b_frames, _ = sheet.read_frames(back)
        size = bpp.stat().st_size
    ok = a_frames == b_frames
    expect = 9 * 256
    print(f"gbagfx: {png.name} -> {size} bytes of 4bpp (expect {expect} = 9 frames x .size 256); round-trip {'identical' if ok else 'DIFFERS'}")
    return 0 if ok and size == expect else 1


def verify_trainer(g: Path, png: Path) -> int:
    """As src/data/graphics/trainers.h: png -> .4bpp (no metatile args) and png -> .gbapal."""
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


def verify_creature(g: Path, out: Path) -> int:
    """As src/data/graphics/pokemon.h: each PNG -> .4bpp, normal/shiny.pal -> .gbapal."""
    ok_all = True
    with tempfile.TemporaryDirectory() as t:
        for name, frames, expect in (("anim_front.png", 2, 4096), ("front.png", 1, 2048), ("back.png", 1, 2048)):
            bpp, back = Path(t) / (name + ".4bpp"), Path(t) / (name + ".back.png")
            gp = Path(t) / "n.gbapal"
            subprocess.run([str(g), str(out / "normal.pal"), str(gp)], check=True)
            subprocess.run([str(g), str(out / name), str(bpp)], check=True)
            subprocess.run([str(g), str(bpp), str(back), "-width", "8", "-palette", str(gp)], check=True)
            from PIL import Image
            a_, b_ = Image.open(out / name), Image.open(back)
            same = list(a_.getdata()) == list(b_.getdata())
            size = bpp.stat().st_size
            print(f"gbagfx: {name} -> {size} bytes of 4bpp (expect {expect}); round-trip {'identical' if same else 'DIFFERS'}")
            ok_all &= same and size == expect
        for p in ("normal.pal", "shiny.pal"):
            gp = Path(t) / (p + ".gbapal")
            subprocess.run([str(g), str(out / p), str(gp)], check=True)
            print(f"gbagfx: {p} -> {gp.stat().st_size} bytes (expect 32)")
            ok_all &= gp.stat().st_size == 32
    return 0 if ok_all else 1


def install_creature(s) -> int:
    """Copy the five files into graphics/pokemon/<replaces>/ and set its y_offsets."""
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


def png_w(p: Path) -> int:
    from PIL import Image

    return Image.open(p).width


def cmd_install(a) -> int:
    """Copy the sheet over the vanilla file it replaces and point its graphics info at our palette."""
    s = spec_mod.load(a.spec)
    if not s.replaces:
        print("spec has no `replaces:`")
        return 1
    if s.kit == "creature64":
        return install_creature(s)
    em = emerald_dir()
    shutil.copyfile(out_dir(s) / f"{s.name}.png", em / s.replaces)
    print(f"copied -> {em / s.replaces}")
    if s.palette_tag:
        gi = em / "src/data/object_events/object_event_graphics_info.h"
        src = gi.read_text()
        sym = s.meta["graphics_info"]
        pat = re.compile(rf"(gObjectEventGraphicsInfo_{sym} = \{{.*?\.paletteTag = )(\w+)(,.*?\.paletteSlot = )(\w+)", re.S)
        slot = s.palette_tag.replace("OBJ_EVENT_PAL_TAG_", "PALSLOT_")
        new, n = pat.subn(rf"\g<1>{s.palette_tag}\g<3>{slot}", src)
        if n != 1:
            print(f"could not find gObjectEventGraphicsInfo_{sym} in {gi}")
            return 1
        gi.write_text(new)
        print(f"set gObjectEventGraphicsInfo_{sym}.paletteTag = {s.palette_tag}, paletteSlot = {slot}")
    return 0


def cmd_compare(a) -> int:
    """Side-by-side review sheet for variants: python -m emerald_sprite compare out.png a.yaml b.yaml ..."""
    specs = [spec_mod.load(p) for p in a.specs]
    em = emerald_dir()
    if specs[0].kit == "creature64":
        creature.compare(specs, Path(a.out), em if (em / "graphics/battle_environment").exists() else None, sheet.spec_palette)
        print(f"wrote {a.out}")
        return 0
    if specs[0].kit == "trainer64":
        trainer.compare(specs, Path(a.out), em if (em / "graphics/battle_environment").exists() else None, sheet.spec_palette)
        print(f"wrote {a.out}")
        return 0
    preview.compare(specs, Path(a.out), em if (em / "data/tilesets").exists() else None)
    print(f"wrote {a.out}")
    return 0


def cmd_audit(a) -> int:
    r = audit_mod.run(emerald_dir())
    audit_mod.print_report(r)
    if a.write:
        audit_mod.write_checklist(r)
        print(f"rewrote the generated tables in {audit_mod.CHECKLIST.relative_to(REPO)}")
    return 1 if r["unassigned"] else 0


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
    p = argparse.ArgumentParser(prog="emerald_sprite")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, arg in (
        ("build", cmd_build, "spec"),
        ("lint", cmd_lint, "png"),
        ("verify", cmd_verify, "spec"),
        ("install", cmd_install, "spec"),
    ):
        sp = sub.add_parser(name)
        sp.add_argument(arg)
        sp.set_defaults(fn=fn)
    sub.add_parser("corpus").set_defaults(fn=cmd_corpus)
    ip = sub.add_parser("inspect")
    ip.add_argument("png")
    ip.add_argument("out")
    ip.set_defaults(fn=cmd_inspect)
    ap = sub.add_parser("audit")
    ap.add_argument("--write", action="store_true")
    ap.set_defaults(fn=cmd_audit)
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
