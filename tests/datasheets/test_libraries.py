"""The open EDA libraries, read for what their authors wrote beside each part: the sheet, the package, the
values. Written for these tests, shaped like the libraries' own files."""
from spicy_electronics_index.datasheets import libraries as lib

NAMES = {"BC547": "BC547", "LM317": "LM317", "NE5532": "NE5532", "1N4006": "1N4006", "53": "53", "LED": "LED"}
PAGE = "https://example.org/{ref}/{path}"

KICAD = '''(kicad_symbol_lib
	(symbol "Q_NPN_CBE"
		(property "Reference" "Q")
		(property "Datasheet" "~")
		(property "Description" "NPN transistor, collector/base/emitter")
	)
	(symbol "BC547"
		(extends "Q_NPN_CBE")
		(property "Value" "BC547")
		(property "Footprint" "Package_TO_SOT_THT:TO-92_Inline")
		(property "Datasheet" "https://www.onsemi.com/pub/Collateral/BC550-D.pdf")
		(property "Description" "0.1A Ic, 45V Vce, Small Signal NPN Transistor, TO-92")
		(property "ki_keywords" "NPN Transistor")
	)
	(symbol "LM317_TO-220"
		(property "Value" "LM317_TO-220")
		(property "Footprint" "")
		(property "Datasheet" "http://www.ti.com/lit/ds/symlink/lm317.pdf")
		(property "Description" "1.5A 37V Adjustable Linear Regulator, TO-220")
	)
	(symbol "LED"
		(property "Datasheet" "~")
	)
)'''


def test_kicad_gives_each_indexed_symbol_its_sheet_package_and_description_and_skips_the_generics():
    rows = list(lib.kicad_rows("Transistor_BJT", KICAD, NAMES, "kicad_symbols", "9.0.9.1", PAGE))
    assert [r["part"] for r in rows] == ["BC547", "LM317"]
    bc = rows[0]
    assert bc["url"] == "https://www.onsemi.com/pub/Collateral/BC550-D.pdf"
    assert bc["maker"] == "onsemi"                       # nobody named: the maker whose site serves the sheet
    assert bc["package"] == "Package_TO_SOT_THT:TO-92_Inline" and bc["keywords"] == "NPN Transistor"
    assert bc["name"] == "0.1A Ic, 45V Vce, Small Signal NPN Transistor, TO-92"
    assert bc["category"] == "Transistor_BJT" and bc["revision"] == "9.0.9.1"
    assert bc["page"] == "https://example.org/9.0.9.1/Transistor_BJT.kicad_sym"


def test_a_symbol_named_with_its_package_is_the_head_part_in_that_package():
    assert lib.kicad_name("LM317_TO-220", NAMES) == ("LM317", "TO-220")
    assert lib.kicad_name("BC547", NAMES) == ("BC547", "")
    assert lib.kicad_name("Q_NPN_CBE", NAMES) == ("", "")
    assert lib.kicad_name("LM317_Flavour", NAMES) == ("", "")     # a tail that is not a package is not split
    rows = list(lib.kicad_rows("Regulator_Linear", KICAD, NAMES, "kicad_symbols", "9.0.9.1", PAGE))
    lm = next(r for r in rows if r["part"] == "LM317")
    assert lm["package"] == "TO-220" and lm["maker"] == "texas-instruments"


def test_a_name_without_both_a_letter_and_a_digit_is_not_a_part_even_when_a_census_lists_it():
    assert lib.indexed("53", NAMES) == "" and lib.indexed("LED", NAMES) == ""
    assert lib.indexed("bc547", NAMES) == "BC547"


HORIZON = {
    "MPN": [False, "NE5532"], "manufacturer": [False, "Texas Instruments"],
    "datasheet": [False, "https://www.ti.com/lit/ds/symlink/ne5532.pdf"],
    "description": [False, "Dual Low-Noise Opamp"], "package": "0932e22e", "tags": ["opamp", "dual"],
    "parametric": {"table": "opamps", "channels": "2", "gbw": "10e6"}, "type": "part",
}


def test_horizon_takes_a_part_whose_mpn_the_index_knows_with_its_values_and_package():
    r = lib.horizon_row(HORIZON, "parts/ic/opamp/ti/ne5532.json", {"0932e22e": "SOIC-8"}, NAMES, "horizon_pool",
                        "2026-06-26 (0696685)", PAGE)
    assert r["part"] == "NE5532" and r["maker"] == "texas-instruments" and r["package"] == "SOIC-8"
    assert r["category"] == "ic/opamp/ti" and r["keywords"] == "opamp, dual"
    assert r["parameters"] == "channels 2; gbw 10e6"
    assert r["page"] == "https://example.org/2026-06-26 (0696685)/parts/ic/opamp/ti/ne5532.json"


def test_horizon_reads_an_inherited_field_from_the_base_part_and_leaves_a_suffixed_mpn():
    base = {**HORIZON, "uuid": "b1", "MPN": [False, "AMS1117"], "tags": ["ldo"]}
    child = {"uuid": "c1", "base": "b1", "MPN": [False, "NE5532"], "datasheet": [True, ""], "description": [False, "3.3V"],
             "manufacturer": [True, ""], "inherit_tags": True, "tags": ["3v3"], "type": "part"}
    j = lib.horizon_resolve(child, {"b1": base, "c1": child})
    r = lib.horizon_row(j, "parts/x.json", {"0932e22e": "SOIC-8"}, NAMES, "s", "r", PAGE)
    assert r["url"] == "https://www.ti.com/lit/ds/symlink/ne5532.pdf" and r["maker"] == "texas-instruments"
    assert r["name"] == "3.3V" and r["package"] == "SOIC-8" and r["keywords"] == "3v3, ldo"
    orphan = {**child, "base": "nobody"}
    assert lib.horizon_row(lib.horizon_resolve(orphan, {}), "parts/x.json", {}, NAMES, "s", "r", PAGE)["url"] == ""
    assert lib.horizon_row({**HORIZON, "MPN": [False, "NE5532D"]}, "parts/x.json", {}, NAMES, "s", "r", PAGE) is None


def test_kicad_leaves_a_symbol_that_gives_neither_a_sheet_nor_a_description():
    bare = KICAD.replace('"https://www.onsemi.com/pub/Collateral/BC550-D.pdf"', '"~"').replace(
        '"0.1A Ic, 45V Vce, Small Signal NPN Transistor, TO-92"', '""')
    assert [r["part"] for r in lib.kicad_rows("x", bare, NAMES, "s", "r", PAGE)] == ["LM317"]


LIBREPCB = '''(librepcb_device 0ca0993c
 (name "1N4006")
 (description "General-purpose rectifier diode.\\n\\nGenerated by a script.")
 (keywords "diode,rectifier")
 (resource "Datasheet 1N4006" (mediatype "application/pdf")
  (url "https://www.onsemi.com/pdf/datasheet/1n4001-d.pdf")
 )
 (component 0ca0993c)
 (package 2634cc8c)
 (part "1N4006RLG" (manufacturer "onsemi")
  (attribute "V_R" (type voltage) (unit volt) (value "800"))
  (attribute "I_O" (type current) (unit ampere) (value "1"))
  (attribute "PACKAGING" (type string) (unit none) (value "T&R 5000"))
 )
 (part "1N4006G" (manufacturer "onsemi")
  (attribute "V_R" (type voltage) (unit volt) (value "800"))
  (attribute "I_O" (type current) (unit ampere) (value "1"))
  (attribute "STATUS" (type string) (unit none) (value "Obsolete"))
 )
 (part "1N4006-E3/54" (manufacturer "Vishay")
  (attribute "V_R" (type voltage) (unit volt) (value "800"))
  (attribute "I_O" (type current) (unit milliampere) (value "1000"))
 )
)'''


def test_librepcb_gives_one_row_per_maker_with_the_mpns_and_the_typed_values_in_units():
    rows = list(lib.librepcb_rows(LIBREPCB, "dev/0ca0993c/device.lp", {"2634cc8c": "DO41"}, NAMES, "librepcb_base",
                                  "2026-06-30 (9c5a514)", PAGE))
    assert [(r["part"], r["maker"], r["maker_text"]) for r in rows] == [
        ("1N4006", "onsemi", "onsemi"), ("1N4006", "vishay", "Vishay")]
    on, vi = rows
    assert on["parameters"] == "MPN 1N4006RLG, 1N4006G; V_R 800 V; I_O 1 A"
    assert on["status"] == "Obsolete" and vi["status"] == ""
    assert vi["parameters"] == "MPN 1N4006-E3/54; V_R 800 V; I_O 1000 mA"
    assert on["url"] == "https://www.onsemi.com/pdf/datasheet/1n4001-d.pdf" and on["package"] == "DO41"
    assert on["name"] == "General-purpose rectifier diode." and on["keywords"] == "diode,rectifier"


def test_librepcb_skips_a_device_nobody_in_the_index_knows():
    assert list(lib.librepcb_rows(LIBREPCB.replace("1N4006", "ZZ9"), "dev/x/device.lp", {}, NAMES, "s", "r", PAGE)) == []


FOOTPRINT = """(footprint "TO-92_Inline"
	(version 20241229)
	(layer "F.Cu")
	(descr "TO-92 leads in-line, narrow, oval pads, drill 0.75mm (see NXP sot054_po.pdf)")
	(tags "to-92 sc-43 sc-43a sot54 PA33 transistor")
	(property "Reference" "REF**" (at 1.27 -3.56 0) (layer "F.SilkS"))
	(attr through_hole)
	(fp_line (start -2.48 -2.6) (end 3.02 -2.6) (stroke (width 0.1) (type solid)) (layer "F.Fab"))
	(fp_arc (start -2.48 -2.6) (mid 0.27 -0.05) (end 3.02 -2.6) (stroke (width 0.1) (type solid)) (layer "F.Fab"))
	(fp_text user "${REFERENCE}" (at 0 9 0) (layer "F.Fab"))
	(fp_rect (start -2.73 -2.85) (end 3.27 2.0) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))
	(pad "1" thru_hole rect (at 0 0) (size 1.05 1.5) (drill 0.75) (layers "*.Cu" "*.Mask"))
	(pad "2" thru_hole oval (at 1.27 0) (size 1.05 1.5) (drill 0.75) (layers "*.Cu" "*.Mask"))
	(pad "3" thru_hole oval (at 2.54 0) (size 1.05 1.5) (drill 0.75) (layers "*.Cu" "*.Mask"))
	(model "${KICAD9_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-92_Inline.step" (offset (xyz 0 0 0)))
)"""


def test_a_footprint_gives_mounting_pads_pitch_drill_body_size_and_the_drawing_it_came_from():
    r = lib.footprint_row(FOOTPRINT, "Package_TO_SOT_THT.pretty/TO-92_Inline.kicad_mod", "kicad_footprints", "9.0.9.1", PAGE)
    assert r["footprint"] == "Package_TO_SOT_THT:TO-92_Inline" and r["mounting"] == "through hole"
    assert (r["pads"], r["pad_spacing_mm"], r["drill_mm"]) == ("3", "1.27", "0.75")
    assert (r["body_x_mm"], r["body_y_mm"]) == ("5.50", "2.55")        # the outline on F.Fab, its text left out
    assert (r["courtyard_x_mm"], r["courtyard_y_mm"]) == ("6.00", "4.85")
    assert r["tags"] == "to-92 sc-43 sc-43a sot54 PA33 transistor"
    assert r["reference"] == "NXP sot054_po.pdf" and r["model_3d"] == "TO-92_Inline.step"
    seen = lib.footprint_row(FOOTPRINT.replace("(see NXP sot054_po.pdf)", "see https://www.vishay.com/docs/66542/to-220-1.pdf, JEDEC TO-220"),
                             "x.pretty/y.kicad_mod", "s", "r", PAGE)
    assert seen["reference"] == "https://www.vishay.com/docs/66542/to-220-1.pdf; JEDEC TO-220"
    assert r["page"] == "https://example.org/9.0.9.1/Package_TO_SOT_THT.pretty/TO-92_Inline.kicad_mod"


def test_the_s_expression_reader_keeps_quoted_strings_whole():
    assert lib.sexp('(a "b c" (d 1 "e)f"))') == ["a", "b c", ["d", "1", "e)f"]]
    assert lib.footprint_row("(kicad_pcb)", "x.pretty/y.kicad_mod", "s", "r", PAGE) is None
