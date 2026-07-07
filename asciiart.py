#!/usr/bin/env python3
"""asciiart.py — convert an image to dot-matrix (halftone dither) or classic ASCII art.

Usage:
  python asciiart.py input.jpg --mode dots  --out out.png
  python asciiart.py input.jpg --mode chars --out out.txt
  python asciiart.py input.jpg --mode chars --png --out out.png

Modes:
  dots   Ordered (Bayer) dithering rendered as white dots on black — matches
         the dotted halftone-portrait look.
  chars  Brightness-mapped characters (" .:-=+*#%@"). Text by default,
         or rendered to PNG with --png.

Requires: Pillow  (pip install pillow)
"""

import argparse
import sys

from PIL import Image, ImageDraw, ImageEnhance

# 8x8 Bayer matrix, values 0..63
BAYER8 = [
    [ 0, 32,  8, 40,  2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44,  4, 36, 14, 46,  6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [ 3, 35, 11, 43,  1, 33,  9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47,  7, 39, 13, 45,  5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
]

CHAR_RAMP = " .:-=+*#%@"


def load_gray(path, columns, char_aspect=1.0, contrast=1.0, invert=False):
    """Load image, optionally boost contrast, resize to a grid of `columns`
    cells wide, return as grayscale Image. char_aspect squashes height
    (chars are ~2x taller than wide)."""
    img = Image.open(path).convert("L")
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if invert:
        img = Image.eval(img, lambda v: 255 - v)
    w, h = img.size
    rows = max(1, int(h / w * columns * char_aspect))
    return img.resize((columns, rows), Image.LANCZOS)


def render_dots(gray, cell=6, dot_radius=None, bg=(0, 0, 0), fg=(255, 255, 255)):
    """Bayer-dither the grid; each 'on' cell becomes a dot of radius dot_radius
    inside a cell x cell block."""
    if dot_radius is None:
        dot_radius = max(1, cell // 3)
    cols, rows = gray.size
    px = gray.load()
    out = Image.new("RGB", (cols * cell, rows * cell), bg)
    draw = ImageDraw.Draw(out)
    for y in range(rows):
        for x in range(cols):
            threshold = (BAYER8[y % 8][x % 8] + 0.5) * 4  # 0..255
            if px[x, y] > threshold:
                cx = x * cell + cell // 2
                cy = y * cell + cell // 2
                draw.ellipse(
                    (cx - dot_radius, cy - dot_radius,
                     cx + dot_radius, cy + dot_radius),
                    fill=fg,
                )
    return out


def render_chars(gray):
    """Map each cell's brightness to a character. Returns list of strings."""
    cols, rows = gray.size
    px = gray.load()
    n = len(CHAR_RAMP)
    lines = []
    for y in range(rows):
        lines.append("".join(
            CHAR_RAMP[min(n - 1, px[x, y] * n // 256)] for x in range(cols)
        ))
    return lines


def chars_to_png(lines, cell_w=8, cell_h=14, bg=(0, 0, 0), fg=(230, 230, 230)):
    """Render text lines to a PNG using a monospace bitmap font."""
    from PIL import ImageFont
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", cell_h)
    except OSError:
        font = ImageFont.load_default()
    cols = max(len(l) for l in lines)
    out = Image.new("RGB", (cols * cell_w, len(lines) * cell_h), bg)
    draw = ImageDraw.Draw(out)
    for y, line in enumerate(lines):
        draw.text((0, y * cell_h), line, fill=fg, font=font)
    return out


def main():
    p = argparse.ArgumentParser(description="Image → dot-matrix or ASCII art")
    p.add_argument("input", help="input image (jpg/png/…)")
    p.add_argument("--mode", choices=["dots", "chars"], default="dots")
    p.add_argument("--width", type=int, default=160,
                   help="output grid width in cells/characters (default 160)")
    p.add_argument("--cell", type=int, default=6,
                   help="dots mode: pixel size of each cell (default 6)")
    p.add_argument("--contrast", type=float, default=1.3,
                   help="contrast boost, 1.0 = none (default 1.3)")
    p.add_argument("--invert", action="store_true",
                   help="invert brightness (for dark-on-light sources)")
    p.add_argument("--png", action="store_true",
                   help="chars mode: render to PNG instead of text")
    p.add_argument("--out", default=None, help="output file path")
    args = p.parse_args()

    if args.mode == "dots":
        gray = load_gray(args.input, args.width, 1.0, args.contrast, args.invert)
        out = args.out or "out_dots.png"
        render_dots(gray, cell=args.cell).save(out)
    else:
        # chars are ~2x taller than wide → squash rows by 0.5
        gray = load_gray(args.input, args.width, 0.5, args.contrast, args.invert)
        lines = render_chars(gray)
        if args.png:
            out = args.out or "out_chars.png"
            chars_to_png(lines).save(out)
        else:
            out = args.out or "out_chars.txt"
            with open(out, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
