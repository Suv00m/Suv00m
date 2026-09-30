#!/usr/bin/env python3
"""Generate a neofetch-style ASCII-art SVG for the GitHub profile README.

Reads assets/avatar.png, renders monospace ASCII art on the left and a
neofetch-style info panel on the right, then writes light_mode.svg and
dark_mode.svg as UTF-8 encoded XML.

Run:  python3 generate.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "assets" / "avatar.png"

CROP = (75, 6, 405, 335)
CONTRAST = 1.05
ART_COLS = 60
CELL_W = 9.6
LINE_H = 20
FONT_SIZE = 16
PAD_X = 16
PAD_Y = 30
PANEL_GAP = 36
RAMP = "@%#*+=-:. "  # darkest -> lightest

TITLE = "shuvom@mandal"

INFO = [
    ("OS", "Ex CTO @ BeHooked.ai"),
    ("Host", "India"),
    ("Kernel", "AI Systems Builder"),
    ("Uptime", "Ex Data Science @ videodubber.ai"),
    ("Shell", "Python, C"),
    ("Resolution", "ML · Applied Research · Infra"),
    ("Terminal", "shuvam.in"),
    ("CPU", "Machine Learning"),
    ("Memory", "production-grade AI products"),
    ("GitHub", "github.com/Suv00m"),
    ("LinkedIn", "shuvam-mandal"),
    ("HuggingFace", "shuvom"),
    ("Contact", "shuvom@behooked.co"),
]

PALETTE = [
    "#cf222e", "#bc4c00", "#6e7781", "#1a7f37",
    "#0969da", "#8250df", "#bf3989", "#57606a",
]

THEMES = {
    "light_mode.svg": {
        "bg": "#f6f8fa",
        "fg": "#24292f",
        "key": "#953800",
        "value": "#0a3069",
        "cc": "#8c959f",
        "invert": True,
    },
    "dark_mode.svg": {
        "bg": "#0d1117",
        "fg": "#adbac7",
        "key": "#f0883e",
        "value": "#79c0ff",
        "cc": "#545d68",
        "invert": True,
    },
}


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_ascii(path: Path, cols: int, invert: bool) -> list[str]:
    img = Image.open(path).convert("L")
    if CROP:
        img = img.crop(CROP)
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Contrast(img).enhance(CONTRAST)
    width, height = img.size
    rows = max(1, round(cols * height / width * 0.5))
    img = img.resize((cols, rows), Image.Resampling.LANCZOS)
    ramp = RAMP[::-1] if invert else RAMP
    last = len(ramp) - 1
    pixels = img.tobytes()
    lines = []
    for r in range(rows):
        row = pixels[r * cols:(r + 1) * cols]
        lines.append("".join(ramp[p * last // 255] for p in row).rstrip())
    return lines


def panel_lines() -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = [(TITLE, "")]
    key_width = max(len(k) for k, _ in INFO)
    for key, value in INFO:
        lines.append((f"{key:<{key_width}}", value))
    return lines


def build_svg(theme: dict, art: list[str]) -> str:
    panel = panel_lines()
    rows = max(len(art), len(panel) + 1)

    art_w = ART_COLS * CELL_W
    panel_x = PAD_X + art_w + PANEL_GAP
    width = int(panel_x + 60 * CELL_W + PAD_X)
    height = int(PAD_Y + rows * LINE_H + PAD_Y)

    out: list[str] = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}px" '
        f'height="{height}px" font-family="ui-monospace,SFMono-Regular,'
        f'Menlo,Consolas,monospace" font-size="{FONT_SIZE}px">'
    )
    out.append("  <style>")
    out.append("    text { white-space: pre; }")
    out.append(f"    .art {{ fill: {theme['fg']}; }}")
    out.append(f"    .title {{ fill: {theme['fg']}; font-weight: 700; }}")
    out.append(f"    .key {{ fill: {theme['key']}; }}")
    out.append(f"    .value {{ fill: {theme['value']}; }}")
    out.append(f"    .cc {{ fill: {theme['cc']}; }}")
    out.append("  </style>")
    out.append(
        f'  <rect width="{width}px" height="{height}px" '
        f'fill="{theme["bg"]}" rx="12"/>'
    )

    out.append(f'  <text x="{PAD_X}" y="{PAD_Y}" class="art">')
    for i, line in enumerate(art):
        out.append(f'    <tspan x="{PAD_X}" y="{PAD_Y + i * LINE_H}">{escape(line)}</tspan>')
    out.append("  </text>")

    out.append(f'  <text x="{panel_x}" y="{PAD_Y}">')
    y = PAD_Y
    out.append(
        f'    <tspan x="{panel_x}" y="{y}" class="title">{escape(TITLE)}</tspan>'
        f'<tspan x="{int(panel_x + len(TITLE) * CELL_W + CELL_W)}" y="{y}" '
        f'class="cc">────────────────────────────</tspan>'
    )
    for key, value in panel[1:]:
        y += LINE_H
        out.append(
            f'    <tspan x="{panel_x}" y="{y}" class="cc">. </tspan>'
            f'<tspan class="key">{escape(key)}</tspan>'
            f'<tspan class="cc">: </tspan>'
            f'<tspan class="value">{escape(value)}</tspan>'
        )

    y += LINE_H + 4
    x = panel_x
    for color in PALETTE:
        out.append(f'    <tspan x="{int(x)}" y="{y}" fill="{color}">███</tspan>')
        x += 3 * CELL_W + 2
    out.append("  </text>")

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    for filename, theme in THEMES.items():
        art = load_ascii(SOURCE, ART_COLS, theme["invert"])
        (ROOT / filename).write_text(build_svg(theme, art), encoding="utf-8")
        print("wrote", filename)


if __name__ == "__main__":
    main()
