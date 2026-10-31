"""JASC-PAL palettes and the GBA colour rules.

The GBA stores colours as 15-bit BGR (5 bits per channel). pokeemerald keeps palettes as
JASC-PAL text files with 8-bit values, and gbagfx drops the low 3 bits when it builds
.gbapal. So every colour we emit must already be a multiple of 8 per channel (after the
>>3 truncation) or it will shift in game.
"""
from __future__ import annotations

from pathlib import Path


def load_jasc(path: str | Path) -> list[tuple[int, int, int]]:
    lines = Path(path).read_text().split()
    if lines[0] != "JASC-PAL":
        raise ValueError(f"{path}: not a JASC-PAL file")
    n = int(lines[2])
    vals = list(map(int, lines[3 : 3 + 3 * n]))
    return [tuple(vals[i : i + 3]) for i in range(0, 3 * n, 3)]


def write_jasc(path: str | Path, colours: list[tuple[int, int, int]]) -> None:
    body = "\n".join(f"{r} {g} {b}" for r, g, b in colours)
    Path(path).write_text(f"JASC-PAL\r\n0100\r\n{len(colours)}\r\n" + body.replace("\n", "\r\n") + "\r\n")


def gba15(c: tuple[int, int, int]) -> tuple[int, int, int]:
    """The colour the GBA actually shows (each channel truncated to 5 bits)."""
    return tuple((v >> 3) << 3 for v in c)


def luma(c: tuple[int, int, int]) -> float:
    r, g, b = c
    return 0.299 * r + 0.587 * g + 0.114 * b


def flat(colours: list[tuple[int, int, int]]) -> list[int]:
    """Pillow putpalette() format, padded to 256 entries."""
    out = [v for c in colours for v in c]
    return out + [0] * (768 - len(out))
