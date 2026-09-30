#!/usr/bin/env python3
"""Generate a neofetch-style ASCII-art SVG for the GitHub profile README.

Reads assets/avatar.png, renders monospace ASCII art on the left and a
neofetch-style info panel on the right, then writes light_mode.svg and
dark_mode.svg as UTF-8 encoded XML.

Run:  python3 generate.py
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import requests
from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "assets" / "avatar.png"
LOGIN = "Suv00m"
API = "https://api.github.com"

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
    ("Role", "Ex CTO @ BeHooked.ai"),
    ("Location", "India"),
    ("Focus", "AI Systems Builder"),
    ("Experience", "Ex Data Science @ videodubber.ai"),
    ("Languages", "Python · C"),
    ("ML", "scikit-learn · TensorFlow · PyTorch"),
    ("Data", "NumPy · pandas · Matplotlib"),
    ("Tools", "Git · Docker"),
    ("Website", "shuvam.in"),
    ("GitHub", "github.com/Suv00m"),
    ("LinkedIn", "shuvam-mandal"),
    ("Hugging Face", "shuvom"),
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


def gh(path: str, session: requests.Session) -> requests.Response:
    return session.get(f"{API}{path}", timeout=30)


def link_last_page(response: requests.Response) -> int:
    match = re.search(r'[?&]page=(\d+)>; rel="last"', response.headers.get("Link", ""))
    return int(match.group(1)) if match else 0


def fetch_stats(session: requests.Session) -> list[tuple[str, int]]:
    stats: list[tuple[str, int]] = []

    def add(label: str, value: int) -> None:
        stats.append((label, value))

    try:
        user = gh(f"/users/{LOGIN}", session).json()
        add("repos", int(user.get("public_repos", 0)))
        add("followers", int(user.get("followers", 0)))
        add("following", int(user.get("following", 0)))
        add("gists", int(user.get("public_gists", 0)))
    except Exception as error:
        print("stats: user lookup failed:", error)

    try:
        stars = 0
        page = 1
        while True:
            repos = gh(f"/users/{LOGIN}/repos?per_page=100&type=owner&page={page}", session).json()
            if not isinstance(repos, list) or not repos:
                break
            stars += sum(int(r.get("stargazers_count", 0)) for r in repos)
            if len(repos) < 100:
                break
            page += 1
        add("stars", stars)
    except Exception as error:
        print("stats: repo stars failed:", error)

    try:
        starred = link_last_page(gh(f"/users/{LOGIN}/starred?per_page=1", session))
        add("starred", starred)
    except Exception as error:
        print("stats: starred repos failed:", error)

    for label, kind in (("pull requests", "pr"), ("issues", "issue")):
        try:
            query = f"author:{LOGIN}+type:{kind}"
            data = gh(f"/search/issues?q={query}&per_page=1", session).json()
            add(label, int(data.get("total_count", 0)))
        except Exception as error:
            print(f"stats: {label} failed:", error)

    return stats


def activity_lines(stats: list[tuple[str, int]]) -> list[tuple[str, int, int]]:
    label_width = max((len(label) for label, _ in stats), default=0)
    peak = max((value for _, value in stats), default=0) or 1
    lines = []
    for label, value in stats:
        filled = round(value / peak * 16)
        lines.append((f". {label:<{label_width}}: {value:>5}  ", value, filled))
    return lines


def build_svg(theme: dict, art: list[str], activity: list[tuple[str, int, int]]) -> str:
    panel = panel_lines()

    art_w = ART_COLS * CELL_W
    panel_x = PAD_X + art_w + PANEL_GAP

    out: list[str] = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')

    body: list[str] = []
    y = PAD_Y

    body.append(
        f'    <tspan x="{panel_x}" y="{y}" class="title">{escape(TITLE)}</tspan>'
        f'<tspan x="{int(panel_x + len(TITLE) * CELL_W + CELL_W)}" y="{y}" '
        f'class="cc">────────────────────────────</tspan>'
    )
    for key, value in panel[1:]:
        y += LINE_H
        body.append(
            f'    <tspan x="{panel_x}" y="{y}" class="cc">. </tspan>'
            f'<tspan class="key">{escape(key)}</tspan>'
            f'<tspan class="cc">: </tspan>'
            f'<tspan class="value">{escape(value)}</tspan>'
        )

    y += LINE_H + 4
    x = panel_x
    for color in PALETTE:
        body.append(f'    <tspan x="{int(x)}" y="{y}" fill="{color}">███</tspan>')
        x += 3 * CELL_W + 2

    if activity:
        y += LINE_H + 6
        body.append(
            f'    <tspan x="{panel_x}" y="{y}" class="title">activity</tspan>'
            f'<tspan x="{int(panel_x + len("activity") * CELL_W + CELL_W)}" y="{y}" '
            f'class="cc">──────────────────────</tspan>'
        )
        for head, _value, filled in activity:
            y += LINE_H
            body.append(
                f'    <tspan x="{panel_x}" y="{y}" class="cc">{escape(head)}</tspan>'
                f'<tspan class="key">{"█" * filled}</tspan>'
            )

    rows = max(len(art), (y - PAD_Y) // LINE_H + 1)
    width = int(panel_x + 60 * CELL_W + PAD_X)
    height = int(PAD_Y + rows * LINE_H + PAD_Y)

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
    out.extend(body)
    out.append("  </text>")

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    session = requests.Session()
    session.headers["User-Agent"] = f"{LOGIN}-profile"
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("ACCESS_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    stats = fetch_stats(session)
    if not stats:
        stats = [("stats", 0)]
        print("warning: no stats fetched (rate limited?); wrote placeholder")
    activity = activity_lines(stats)

    for filename, theme in THEMES.items():
        art = load_ascii(SOURCE, ART_COLS, theme["invert"])
        (ROOT / filename).write_text(build_svg(theme, art, activity), encoding="utf-8")
        print("wrote", filename)


if __name__ == "__main__":
    main()
