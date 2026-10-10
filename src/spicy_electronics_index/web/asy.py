"""LTspice symbols drawn: an .asy read and rendered as SVG, on the maintainer's machine.

The site shows a model's symbol as a drawing, never as the .asy itself: the file is its publisher's, so
the page links it where it is published (`models/symbols.py`) and shows only the picture made from it,
the way it quotes a data sheet by a crop (CLAUDE.md rule 1). The drawings are made from the private tree
by `sei web symbol-drawings`, one SVG per symbol named by the .asy's sha256, and travel as a release
asset the Pages workflow unpacks; deleting the asset withdraws them.

A symbol is a list of primitives in LTspice's own units (a grid of 16, y growing down, as in SVG): LINE,
RECTANGLE, CIRCLE and ARC, each `Normal` and an optional line style; TEXT; PIN with its PINATTRs; WINDOW,
where the schematic writes the instance's name, value or model; SYMATTR. An ARC is its ellipse's bounding
box, then a start and an end point whose directions from the centre say where it begins and ends; LTspice
draws it counter-clockwise as seen on screen. Ported from the browser's former `asy.ts`.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from html import escape
from pathlib import Path

# LTspice's line styles: solid, dash, dot, dash-dot, dash-dot-dot.
DASH = ["", "6 4", "1.5 3", "6 3 1.5 3", "6 3 1.5 3 1.5 3"]
# LTspice's text sizes 0–7 as multiples of its normal one, in symbol units (a normal letter is about 12).
SIZE = [0.625, 1, 1.5, 2, 2.5, 3.5, 5, 7]
# Longer than this, a symbol's Value is its list of default parameters, which would dwarf the drawing.
LONG_VALUE = 24
TEXT = re.compile(r"^TEXT\s+(-?\d+)\s+(-?\d+)\s+(\S+)\s+(\d+)\s?(.*)$")


def num(s: str | None) -> float:
    try:
        return float(s or 0)
    except ValueError:
        return 0.0


def parse(src: str) -> dict:
    out: dict = {"shapes": [], "arcs": [], "texts": [], "pins": [], "windows": [], "attrs": {}}
    pin = None
    for raw in src.splitlines():
        line = raw.strip()
        w = line.split()
        if not w:
            continue
        if w[0] in ("LINE", "RECTANGLE", "CIRCLE"):
            out["shapes"].append({"kind": {"LINE": "line", "RECTANGLE": "rect", "CIRCLE": "circle"}[w[0]],
                                  "x1": num(w[2] if len(w) > 2 else None), "y1": num(w[3] if len(w) > 3 else None),
                                  "x2": num(w[4] if len(w) > 4 else None), "y2": num(w[5] if len(w) > 5 else None),
                                  "style": int(num(w[6] if len(w) > 6 else None))})
        elif w[0] == "ARC":
            v = [num(w[i]) if len(w) > i else 0.0 for i in range(2, 11)]
            out["arcs"].append(dict(zip(("x1", "y1", "x2", "y2", "sx", "sy", "ex", "ey", "style"), v)))
        elif w[0] == "TEXT":
            # TEXT x y justification size text…; a leading ; or ! says comment or directive, not drawn
            m = TEXT.match(line)
            if m:
                out["texts"].append({"x": num(m[1]), "y": num(m[2]), "just": m[3], "size": int(num(m[4])),
                                     "text": re.sub(r"^[;!]", "", m[5] or "")})
        elif w[0] == "WINDOW":
            out["windows"].append({"n": int(num(w[1] if len(w) > 1 else None)), "x": num(w[2] if len(w) > 2 else None),
                                   "y": num(w[3] if len(w) > 3 else None), "just": w[4] if len(w) > 4 else "Left",
                                   "size": int(num(w[5] if len(w) > 5 else None))})
        elif w[0] == "PIN":
            pin = {"x": num(w[1] if len(w) > 1 else None), "y": num(w[2] if len(w) > 2 else None), "name": "", "order": 0}
            out["pins"].append(pin)
        elif w[0] == "PINATTR" and pin is not None and len(w) > 2:
            if w[1] == "PinName":
                pin["name"] = " ".join(w[2:])
            elif w[1] == "SpiceOrder":
                pin["order"] = int(num(w[2]))
        elif w[0] == "SYMATTR" and len(w) > 1:
            out["attrs"][w[1]] = " ".join(w[2:])
    return out


def on_ellipse(cx, cy, rx, ry, px, py):
    """The point of an ellipse in the direction of (px, py) from its centre."""
    dx, dy = px - cx, py - cy
    h = math.hypot(dx / (rx or 1), dy / (ry or 1))
    k = 1 / h if h else 0
    return cx + dx * k, cy + dy * k


def f(v: float) -> str:
    return f"{round(v, 2):g}"


def arc_path(a: dict) -> str:
    """An ARC as an SVG path: counter-clockwise on screen from its start to its end."""
    cx, cy = (a["x1"] + a["x2"]) / 2, (a["y1"] + a["y2"]) / 2
    rx, ry = abs(a["x2"] - a["x1"]) / 2, abs(a["y2"] - a["y1"]) / 2
    sx, sy = on_ellipse(cx, cy, rx, ry, a["sx"], a["sy"])
    ex, ey = on_ellipse(cx, cy, rx, ry, a["ex"], a["ey"])
    # screen angles grow clockwise (y down), so counter-clockwise is the start's angle minus the end's
    span = (math.atan2(sy - cy, sx - cx) - math.atan2(ey - cy, ex - cx)) % (2 * math.pi)
    if span < 1e-9:
        # start and end the same: the whole ellipse, as two halves (one SVG arc cannot close on itself)
        return (f"M {f(cx - rx)} {f(cy)} A {f(rx)} {f(ry)} 0 1 0 {f(cx + rx)} {f(cy)} "
                f"A {f(rx)} {f(ry)} 0 1 0 {f(cx - rx)} {f(cy)}")
    return f"M {f(sx)} {f(sy)} A {f(rx)} {f(ry)} 0 {1 if span > math.pi else 0} 0 {f(ex)} {f(ey)}"


def font_size(s: int) -> float:
    return max(7.0, 9 * (SIZE[s] if 0 <= s < len(SIZE) else 1))


def placement(just: str) -> tuple[str, str, bool]:
    """SVG's text anchor and baseline for an LTspice justification, and whether it is turned upright."""
    vertical = bool(re.match(r"^V", just, re.I))
    j = re.sub(r"^V", "", just, flags=re.I).lower()
    anchor = "start" if j == "left" else "end" if j == "right" else "middle"
    baseline = "hanging" if j == "top" else "alphabetic" if j == "bottom" else "middle"
    return anchor, baseline, vertical


def window_texts(a: dict) -> list[dict]:
    """What the schematic writes in each window: the instance's name and the model, as LTspice would."""
    prefix = a["attrs"].get("Prefix") or "X"
    model = a["attrs"].get("SpiceModel", "")
    value = a["attrs"].get("Value") or model
    say = {0: f"{prefix}1", 3: "" if len(value) > LONG_VALUE else value, 38: model}
    return [{"x": w["x"], "y": w["y"], "just": w["just"], "size": w["size"], "text": say[w["n"]], "window": True}
            for w in a["windows"] if say.get(w["n"])]


def bounds(a: dict, texts: list[dict]) -> tuple[float, float, float, float]:
    """The box that holds everything drawn, texts at a rough width, padded: x, y, width, height."""
    xs, ys = [], []
    for s in a["shapes"] + a["arcs"]:
        xs += [s["x1"], s["x2"]]
        ys += [s["y1"], s["y2"]]
    for p in a["pins"]:
        xs.append(p["x"])
        ys.append(p["y"])
    for t in texts:
        size = font_size(t["size"])
        w = len(t["text"]) * size * 0.6
        anchor, _, vertical = placement(t["just"])
        lo = 0 if anchor == "start" else -w if anchor == "end" else -w / 2
        if vertical:
            xs += [t["x"] - size / 2, t["x"] + size / 2]
            ys += [t["y"] - lo, t["y"] - lo - w]
        else:
            xs += [t["x"] + lo, t["x"] + lo + w]
            ys += [t["y"] - size / 2, t["y"] + size / 2]
    if not xs:
        return 0, 0, 16, 16
    pad = 8
    x0, y0 = min(xs) - pad, min(ys) - pad
    return x0, y0, max(xs) + pad - x0, max(ys) + pad - y0


def svg(src: str, title: str = "") -> str:
    """The drawing of one .asy, in `currentColor` so the page's ink draws it; pins as small squares that
    say their netlist order and name."""
    a = parse(src)
    texts = a["texts"] + window_texts(a)
    x, y, w, h = bounds(a, texts)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="asy" viewBox="{f(x)} {f(y)} {f(w)} {f(h)}" '
           f'role="img" aria-label="{escape(title or a["attrs"].get("SpiceModel") or "symbol")}">',
           '<g fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">']
    ns = ' vector-effect="non-scaling-stroke"'
    for s in a["shapes"]:
        dash = f' stroke-dasharray="{DASH[s["style"]]}"' if 0 < s["style"] < len(DASH) else ""
        if s["kind"] == "line":
            out.append(f'<line x1="{f(s["x1"])}" y1="{f(s["y1"])}" x2="{f(s["x2"])}" y2="{f(s["y2"])}"{dash}{ns}/>')
        elif s["kind"] == "rect":
            out.append(f'<rect x="{f(min(s["x1"], s["x2"]))}" y="{f(min(s["y1"], s["y2"]))}" '
                       f'width="{f(abs(s["x2"] - s["x1"]))}" height="{f(abs(s["y2"] - s["y1"]))}"{dash}{ns}/>')
        else:
            out.append(f'<ellipse cx="{f((s["x1"] + s["x2"]) / 2)}" cy="{f((s["y1"] + s["y2"]) / 2)}" '
                       f'rx="{f(abs(s["x2"] - s["x1"]) / 2)}" ry="{f(abs(s["y2"] - s["y1"]) / 2)}"{dash}{ns}/>')
    for r in a["arcs"]:
        style = int(r["style"])
        dash = f' stroke-dasharray="{DASH[style]}"' if 0 < style < len(DASH) else ""
        out.append(f'<path d="{arc_path(r)}"{dash}{ns}/>')
    out.append('</g><g fill="currentColor" font-family="var(--body, sans-serif)">')
    for t in texts:
        anchor, baseline, vertical = placement(t["just"])
        rot = f' transform="rotate(-90 {f(t["x"])} {f(t["y"])})"' if vertical else ""
        cls = ' class="asy-window"' if t.get("window") else ""
        out.append(f'<text x="{f(t["x"])}" y="{f(t["y"])}" font-size="{f(font_size(t["size"]))}" text-anchor="{anchor}" '
                   f'dominant-baseline="{baseline}"{rot}{cls}>{escape(t["text"])}</text>')
    out.append('</g><g class="asy-pins">')
    for p in a["pins"]:
        out.append(f'<rect x="{f(p["x"] - 3)}" y="{f(p["y"] - 3)}" width="6" height="6">'
                   f'<title>{p["order"]}: {escape(p["name"])}</title></rect>')
    out.append("</g></svg>")
    return "".join(out)


def linked_symbols(parts_dir: Path) -> dict[str, str]:
    """{sha256: model name} for every symbol a recipe links (`get.symbol`)."""
    import yaml
    out = {}
    for p in sorted(parts_dir.rglob("*.yaml")):
        for m in (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("models") or []:
            s = (m.get("get") or {}).get("symbol") or {}
            if s.get("sha256"):
                out.setdefault(s["sha256"], m["name"])
    return out


def main(argv=None) -> int:
    from spicy_electronics_index.core.config import (
        model_part,
        spice_models_root,
        spice_symbols,
        web_symbol_drawings,
    )
    ap = argparse.ArgumentParser(description="draw every symbol a recipe links, as SVG, for the site")
    ap.parse_args(argv)
    wanted = linked_symbols(model_part("x", "y").parent.parent)
    files = {}
    if spice_symbols().exists():
        for line in spice_symbols().read_text(encoding="utf-8").splitlines():
            s = json.loads(line)
            files.setdefault(s["sha256"], s["file"])
    out = web_symbol_drawings()
    out.mkdir(parents=True, exist_ok=True)
    drawn, missing = 0, []
    for sha, name in sorted(wanted.items()):
        rel = files.get(sha)
        if not rel:
            missing.append(name)
            continue
        src = (spice_models_root() / rel).read_text(encoding="latin-1")
        (out / f"{sha}.svg").write_text(svg(src, name), encoding="utf-8")
        drawn += 1
    print(f"{drawn:,} symbols drawn into {out}" + (f"; {len(missing)} not found here: {missing[:5]}" if missing else ""))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
