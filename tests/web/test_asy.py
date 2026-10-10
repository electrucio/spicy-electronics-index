"""The drawing made from an .asy: what it draws, where its arcs go, and that its text cannot break out."""
from __future__ import annotations

from spicy_electronics_index.web import asy as A

POT = """Version 4
SymbolType CELL
LINE Normal 0 0 0 64
RECTANGLE Normal -16 16 16 48
ARC Normal -16 -16 16 16 16 0 -16 0
TEXT 24 32 Left 2 <A & B>
WINDOW 0 24 0 Left 2
SYMATTR Prefix X
SYMATTR Value log_pot
PIN 0 0 NONE 8
PINATTR PinName 1
PINATTR SpiceOrder 1
PIN 0 64 NONE 8
PINATTR PinName 3
PINATTR SpiceOrder 2
"""


def test_an_asy_is_read_as_its_primitives_pins_and_attributes():
    a = A.parse(POT)
    assert [s["kind"] for s in a["shapes"]] == ["line", "rect"] and len(a["arcs"]) == 1
    assert [(p["name"], p["order"]) for p in a["pins"]] == [("1", 1), ("3", 2)]
    assert a["attrs"]["Value"] == "log_pot" and a["texts"][0]["text"] == "<A & B>"


def test_an_arc_runs_counter_clockwise_on_screen_and_a_closed_one_is_a_whole_ellipse():
    # from the right (16, 0) to the left (-16, 0), counter-clockwise on screen: over the top, y < 0
    assert A.arc_path({"x1": -16, "y1": -16, "x2": 16, "y2": 16, "sx": 16, "sy": 0, "ex": -16, "ey": 0}) \
        == "M 16 0 A 16 16 0 0 0 -16 0"
    whole = A.arc_path({"x1": -16, "y1": -16, "x2": 16, "y2": 16, "sx": 16, "sy": 0, "ex": 16, "ey": 0})
    assert whole.count(" A ") == 2


def test_the_drawing_is_svg_in_the_page_ink_with_its_text_escaped():
    s = A.svg(POT, "log_pot")
    assert s.startswith('<svg xmlns="http://www.w3.org/2000/svg" class="asy"') and s.endswith("</svg>")
    assert 'stroke="currentColor"' in s and "&lt;A &amp; B&gt;" in s and "<A & B>" not in s
    assert s.count('<rect x=') == 3 and "<title>2: 3</title>" in s       # the rectangle and two pin squares
    assert '>X1</text>' in s                                             # the name window, as LTspice writes it
