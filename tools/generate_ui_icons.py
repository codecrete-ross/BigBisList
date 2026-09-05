"""Render Big BiS List's small, original utility icons into a deterministic TGA.

Run with the workspace Python (Pillow required); --check compares without writing.
The semantic cell order must match ICON_KEYS in Widgets.lua.
"""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw


ICON_KEYS = (
    "search", "clear", "starOutline", "starFilled", "sortAscending", "sortDescending",
    "chevronLeft", "chevronRight", "chevronDown", "chevronUp", "settings", "filter",
    "details", "check", "bag", "bank", "equipped", "clock", "warning", "info",
    "plus", "minus", "restore", "hide", "menu",
)
ATLAS_SIZE = 256
CELL_SIZE = 32
SCALE = 4
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "ui-icons.tga"


def draw_icon(key: str) -> Image.Image:
    image = Image.new("RGBA", (CELL_SIZE * SCALE, CELL_SIZE * SCALE))
    draw = ImageDraw.Draw(image)
    white = (255, 255, 255, 255)

    def points(values):
        return [(round(x * SCALE), round(y * SCALE)) for x, y in values]

    def line(values, width=2):
        coords = points(values)
        radius = width * SCALE / 2
        draw.line(coords, fill=white, width=round(width * SCALE), joint="curve")
        for x, y in (coords[0], coords[-1]):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=white)

    def ellipse(box, fill=None, width=2):
        draw.ellipse(tuple(round(value * SCALE) for value in box), fill=fill,
                     outline=white if fill is None else None, width=round(width * SCALE))

    def polygon(values, filled=False, width=2):
        if filled:
            draw.polygon(points(values), fill=white)
        else:
            line([*values, values[0]], width)

    if key == "search":
        ellipse((6, 5, 22, 21))
        line([(21, 20), (27, 26)], 2.5)
    elif key == "clear":
        line([(9, 9), (23, 23)])
        line([(23, 9), (9, 23)])
    elif key in ("starOutline", "starFilled"):
        vertices = []
        for index in range(10):
            angle = math.radians(-90 + 36 * index)
            radius = 11 if index % 2 == 0 else 5
            vertices.append((16 + math.cos(angle) * radius, 16 + math.sin(angle) * radius))
        polygon(vertices, key == "starFilled", 1.6)
    elif key == "sortAscending":
        polygon([(8, 21), (16, 11), (24, 21)], True)
    elif key == "sortDescending":
        polygon([(8, 11), (16, 21), (24, 11)], True)
    elif key == "chevronLeft":
        line([(20, 7), (11, 16), (20, 25)], 2.3)
    elif key == "chevronRight":
        line([(12, 7), (21, 16), (12, 25)], 2.3)
    elif key == "chevronDown":
        line([(7, 12), (16, 21), (25, 12)], 2.3)
    elif key == "chevronUp":
        line([(7, 20), (16, 11), (25, 20)], 2.3)
    elif key == "settings":
        ellipse((8, 8, 24, 24), width=3)
        ellipse((13, 13, 19, 19), width=1.5)
        for index in range(8):
            angle = math.radians(index * 45)
            line([(16 + math.cos(angle) * 8, 16 + math.sin(angle) * 8),
                  (16 + math.cos(angle) * 11, 16 + math.sin(angle) * 11)], 3)
    elif key == "filter":
        polygon([(6, 7), (26, 7), (19, 16), (19, 24), (13, 27), (13, 16)])
    elif key == "details":
        polygon([(5, 7), (27, 7), (27, 25), (5, 25)])
        line([(19, 8), (19, 24)])
    elif key == "check":
        line([(6, 16), (13, 23), (26, 9)], 2.8)
    elif key == "bag":
        polygon([(7, 11), (25, 11), (25, 26), (7, 26)])
        line([(12, 11), (12, 6), (20, 6), (20, 11)])
        line([(12, 16), (20, 16)], 1.5)
    elif key == "bank":
        polygon([(5, 11), (16, 5), (27, 11)], True)
        for x in (9, 16, 23):
            line([(x, 14), (x, 23)], 2.5)
        line([(6, 26), (26, 26)], 2.5)
    elif key == "equipped":
        polygon([(10, 6), (6, 10), (6, 17), (10, 17), (10, 26),
                 (22, 26), (22, 17), (26, 17), (26, 10), (22, 6), (19, 9), (13, 9)])
    elif key == "clock":
        ellipse((5, 5, 27, 27))
        line([(16, 10), (16, 16), (21, 19)])
    elif key == "warning":
        polygon([(16, 5), (28, 26), (4, 26)])
        line([(16, 12), (16, 18)], 2.4)
        ellipse((14.8, 21.5, 17.2, 23.9), white)
    elif key == "info":
        ellipse((5, 5, 27, 27))
        ellipse((14.5, 9, 17.5, 12), white)
        line([(16, 15), (16, 23)], 2.4)
    elif key == "plus":
        line([(7, 16), (25, 16)], 2.5)
        line([(16, 7), (16, 25)], 2.5)
    elif key == "minus":
        line([(7, 16), (25, 16)], 2.5)
    elif key == "restore":
        draw.arc(tuple(value * SCALE for value in (6, 6, 26, 26)), 205, 515,
                 fill=white, width=2 * SCALE)
        line([(5, 6), (5, 14), (13, 14)])
    elif key == "hide":
        polygon([(4, 16), (10, 10), (16, 8), (22, 10), (28, 16),
                 (22, 22), (16, 24), (10, 22)], width=1.5)
        ellipse((12, 12, 20, 20), width=1.5)
        line([(6, 5), (26, 27)], 2.5)
    elif key == "menu":
        for x in (7, 16, 25):
            ellipse((x - 1.8, 14.2, x + 1.8, 17.8), white)
    else:
        raise ValueError(f"Unknown icon: {key}")
    icon = image.resize((CELL_SIZE, CELL_SIZE), Image.Resampling.LANCZOS)
    # Lanczos can leave a faint alpha fringe outside the drawn paths. Keep one
    # fully transparent texel around every cell so bilinear sampling cannot bleed.
    ImageDraw.Draw(icon).rectangle((0, 0, CELL_SIZE - 1, CELL_SIZE - 1),
                                  outline=(0, 0, 0, 0), width=1)
    return icon


def render_atlas() -> Image.Image:
    image = Image.new("RGBA", (ATLAS_SIZE, ATLAS_SIZE))
    for index, key in enumerate(ICON_KEYS):
        image.paste(draw_icon(key), ((index % 8) * CELL_SIZE, (index // 8) * CELL_SIZE))
    return image


def atlas_bytes() -> bytes:
    # Uncompressed true-color, top-left origin, 8 alpha bits. Writing this small
    # header ourselves avoids encoder metadata and preserves byte-for-byte output.
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0,
                         ATLAS_SIZE, ATLAS_SIZE, 32, 0x28)
    return header + render_atlas().tobytes("raw", "BGRA")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    expected = atlas_bytes()
    if args.check:
        if not args.output.exists() or args.output.read_bytes() != expected:
            print(f"UI icon atlas is out of date: {args.output}")
            return 1
        print("UI icon atlas is current.")
        return 0
    args.output.write_bytes(expected)
    print(f"Wrote {len(ICON_KEYS)} utility icons to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
