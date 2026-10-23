#!/bin/bash
# Typeset one bench circuit with LaTeX + circuitikz and publish it as data/bench/drawings/<name>.svg.
#   docker/circuitikz/draw.sh bjt-hfe-ic        (the source is docker/circuitikz/drawings/bjt-hfe-ic.tex)
# latex makes a DVI with pgf's dvisvgm driver and dvisvgm turns it into an SVG with every glyph as a path, so the
# page looks the same in every browser. (dvisvgm's PDF mode goes through Ghostscript 10 and drops most of the
# picture; hence the DVI route.) The SVG then gets the margin standalone gives the PDF, a width that shows its
# text at one size on every drawing, and is checked to be well-formed XML; pdflatex + gs make a PNG preview into private_material/scratch/. Build the image once:
# make circuitikz-image          (or TECTONIC=1 docker/circuitikz/draw.sh <name>, with neither Docker nor TeX Live)
set -euo pipefail
name=${1:?name}
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
src="$here/drawings/$name.tex"
[ -f "$src" ] || { echo "no $src" >&2; exit 1; }
work=$(mktemp -d)
[ -n "${KEEP:-}" ] && echo "work dir kept: $work" || trap 'rm -rf "$work"' EXIT
cp "$src" "$work/$name.tex"
cp "$here/bench.sty" "$work/bench.sty"
{ echo '\def\pgfsysdriver{pgfsys-dvisvgm.def}'; cat "$src"; } > "$work/$name-dvi.tex"
# TECTONIC=1: tectonic and PyMuPDF, for a machine with neither Docker nor TeX Live; the PDF's page is written as
# an SVG with every glyph as a path, the standalone border taken off and the size set as dvisvgm's zoom sets it
if [ -n "${TECTONIC:-}" ]; then
  (cd "$work" && tectonic -X compile "$name.tex" > tectonic.log 2>&1) || { tail -20 "$work/tectonic.log"; exit 2; }
  (cd "$root" && uv run --quiet python - "$work/$name.pdf" "$work/$name.svg" "$work/$name.png") <<'PY'
import sys, pymupdf
page = pymupdf.open(sys.argv[1])[0]
svg = page.get_svg_image(text_as_path=True)
b, w, h = 10.0, page.rect.width, page.rect.height     # the standalone border; the margin is put back below
svg = svg.replace(f'width="{w:g}" height="{h:g}" viewBox="0 0 {w:g} {h:g}"',
                  f'width="{(w - 2 * b) * 1.4:.2f}pt" height="{(h - 2 * b) * 1.4:.2f}pt" viewBox="{b} {b} {w - 2 * b:g} {h - 2 * b:g}"', 1)
assert 'pt" viewBox=' in svg, svg[:300]
open(sys.argv[2], "w", encoding="utf-8").write(svg)
page.get_pixmap(dpi=110).save(sys.argv[3])
PY
# the TeX Live image, or the machine's own TeX Live when there is no Docker (LOCAL=1, or none on the PATH)
elif [ -n "${LOCAL:-}" ] || ! docker info > /dev/null 2>&1; then
  run() { bash -c "cd '$work' && $1"; }
else
  run() { docker run --rm -u "$(id -u):$(id -g)" -v "$work":/w -e HOME=/tmp spicy-electronics-index-circuitikz bash -c "cd /w && $1"; }
fi
[ -n "${TECTONIC:-}" ] || run 'latex -interaction=batchmode -halt-on-error '"$name"'-dvi.tex > /dev/null 2>&1 || { grep -A6 "^!" '"$name"'-dvi.log | head -40; exit 2; }
  dvisvgm --no-fonts --exact-bbox --bbox=min --zoom=1.4 -o '"$name"'.svg '"$name"'-dvi.dvi > dvisvgm.log 2>&1 || { cat dvisvgm.log; exit 2; }
  pdflatex -interaction=batchmode -halt-on-error '"$name"'.tex > /dev/null 2>&1 || { grep -A6 "^!" '"$name"'.log | head -40; exit 2; }
  gs -q -sDEVICE=png16m -r110 -o '"$name"'.png '"$name"'.pdf'
[ -n "${PNG:-}" ] && cp "$work/$name.png" "$PNG/$name.png"
# the margin: the DVI bounding box is tight; width and height (dvisvgm's zoom of the natural size, so that every
# drawing shows its text at one size) grow with it
python3 - "$work/$name.svg" <<'PY'
import sys, xml.etree.ElementTree as ET
p = sys.argv[1]
ET.register_namespace("", "http://www.w3.org/2000/svg"); ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
root = ET.parse(p).getroot()
x, y, w, h = (float(v) for v in root.get("viewBox").split())
zoom = float(root.get("width").rstrip("pt")) / w
m = 10.0
root.set("viewBox", f"{x - m:.3f} {y - m:.3f} {w + 2 * m:.3f} {h + 2 * m:.3f}")
root.set("width", f"{(w + 2 * m) * zoom:.2f}pt"); root.set("height", f"{(h + 2 * m) * zoom:.2f}pt")
ET.ElementTree(root).write(p, encoding="utf-8", xml_declaration=True)
ET.parse(p)
PY
cp "$work/$name.svg" "$root/data/bench/drawings/$name.svg"
cp "$work/$name.png" "${SEI_MATERIAL:-$root/private_material}/scratch/$name.png" 2>/dev/null || true
echo "data/bench/drawings/$name.svg ($(wc -c < "$root/data/bench/drawings/$name.svg") bytes)"
