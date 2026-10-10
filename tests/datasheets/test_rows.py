"""The sheet rows' reading, ported from docker/datasheets/, and where on its page each row is found."""
import sys

import pytest
import yaml

from spicy_electronics_index.core import config
from spicy_electronics_index.datasheets import rows as R

pymupdf = pytest.importorskip("pymupdf")


def prototype():
    sys.path.insert(0, str(config.REPO_ROOT / "docker" / "datasheets"))
    import evaluate
    return evaluate


def test_the_port_reads_every_reference_row_as_the_prototype_does_and_keeps_a_temperatures_sign():
    """Rule 7: moved first, proved identical. The conditions reader's prototype (crosscheck.py) was proved
    against and then removed with the second sheet-versus-model iteration on 2026-10-05; what stays is the
    name and unit reading against evaluate.py, every reference row's conditions parsing, and the one change
    made in the move: a temperature keeps its sign."""
    evaluate = prototype()
    docs = yaml.safe_load(config.datasheet_reference().read_text(encoding="utf-8"))["docs"]
    temps = 0
    for d in docs:
        for r in d["rows"]:
            param = r[7] if len(r) > 7 else ""
            assert R.canon(r[0], param) == evaluate.canon(r[0], param)
            assert R.unit_factor(r[5]) == evaluate.unit_factor(r[5])
            ours = R.conditions(r[1])
            assert all(isinstance(k, str) and isinstance(v, float) for k, v in ours.items())
            temps += any(v < 0 for k, v in ours.items() if k in R.TEMPERATURES)
    assert temps >= 1                          # the reference has rows at −55 °C, and they stay negative


def test_a_temperature_keeps_its_sign_and_25_degrees_is_the_benchs_own():
    assert R.conditions("IC=10mA, VCE=1.0V, TA=-55C") == {"IC": 0.01, "VCE": 1.0, "TA": -55.0}
    assert R.conditions("IC=10mA, TA=25C") == {"IC": 0.01}


def test_a_row_printed_over_several_lines_is_found_whole_and_rows_run_down_the_page(tmp_path):
    """Conditions on one line and each part's value on its own, as onsemi prints a table of two parts."""
    doc = pymupdf.open()
    page = doc.new_page()
    for y, text in ((100, "Collector-Emitter Breakdown Voltage (IC = 1.0 mAdc)   40   Vdc"),
                    (140, "DC Current Gain (IC = 0.1 mAdc, VCE = 1.0 Vdc)   2N3903   20"),
                    (152, "2N3904   40"),
                    (180, "(IC = 1.0 mAdc, VCE = 1.0 Vdc)   2N3903   35"),
                    (192, "2N3904   70")):
        page.insert_text((60, y), text, fontsize=9)
    breakdown = R.locate(page, ["V(BR)CEO", "IC=1.0mA", 40, None, None], "2N3904")
    gain = R.locate(page, ["hFE", "IC=0.1mA, VCE=1.0V", 40, None, None], "2N3904", after=breakdown[0][1])
    # text set on baselines 100, 140 and 152 sits on lines 90-103, 130-143 and 142-155
    assert breakdown[0][1] < 91 and 102 < breakdown[0][3] < 130
    assert gain[0][1] < 131 and 154 < gain[0][3] < 170          # both lines of its row, and no more
