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
from . import preview, sheet, spec as spec_mod, trainer

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


def cmd_build(a) -> int:
    s = spec_mod.load(a.spec)
    out = out_dir(s)
    (out / "preview").mkdir(parents=True, exist_ok=True)
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
    for what, mod in (("vanilla walkers", lint_mod), ("vanilla trainer pics", trainer)):
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


def png_w(p: Path) -> int:
    from PIL import Image

    return Image.open(p).width


def cmd_install(a) -> int:
    """Copy the sheet over the vanilla file it replaces and point its graphics info at our palette."""
    s = spec_mod.load(a.spec)
    if not s.replaces:
        print("spec has no `replaces:`")
        return 1
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
