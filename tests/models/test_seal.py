"""The model text sealed for the maintainer: what one paste holds, and a cipher both halves agree on.

The fixture in tests/fixtures/sealed/ is one invented part sealed with a known passphrase; this file
proves the Python half writes exactly it, and web/src/sealed.test.ts that the browser's half opens it.
Rewrite it with `SEI_UPDATE_FIXTURES=1 uv run --extra seal pytest tests/models/test_seal.py` when the
format changes on purpose, and change both halves in the same commit.
"""
from __future__ import annotations

import json
import os

import pytest

from spicy_electronics_index.core.config import tests_fixtures
from spicy_electronics_index.models import found as F
from spicy_electronics_index.models import seal as S

FIXTURE = tests_fixtures() / "sealed"
# What the fixture holds: a passphrase written with spaces around it and a decomposed é, which both halves
# must read as the same one, few iterations so the tests run fast, and invented models only.
CASE = {
    "passphrase": "  café sealed fixture  ",
    "iterations": 1000,
    "part": "TESTQ1",
    "rows": [
        {"source": "invented", "name": "TESTQ1", "hash": "0123456789abcdef0123456789abcdef01234567"},
        {"source": "ltspice-native", "name": "TESTQ1"},
    ],
    "texts": [
        "* TESTQ1 from invented: https://example.org/testq1.lib\n.model TESTQ1 NPN(IS=1f BF=100) ; 10 Ω base\n",
        "* TESTQ1 from ltspice-native: ships with LTspice\n.subckt TESTQ1 C B E\nQ1 C B E QIN\n.ends\n.model QIN NPN(BF=50)\n",
    ],
}


def case_models() -> dict[str, str]:
    return {S.model_key(r): t for r, t in zip(CASE["rows"], CASE["texts"])}


def sealed_case() -> tuple[dict, bytes]:
    key = S.derive(CASE["passphrase"], iterations=CASE["iterations"])
    return S.manifest(key, iterations=CASE["iterations"]), S.seal(key, CASE["part"], S.pack(case_models()))


def test_the_fixture_is_what_the_python_half_writes():
    pytest.importorskip("cryptography")
    manifest, blob = sealed_case()
    if os.environ.get("SEI_UPDATE_FIXTURES"):
        FIXTURE.mkdir(parents=True, exist_ok=True)
        (FIXTURE / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
        (FIXTURE / f"{CASE['part']}.bin").write_bytes(blob)
        (FIXTURE / "case.json").write_text(json.dumps({**CASE, "models": case_models()}, indent=1, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
    assert json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8")) == manifest
    assert (FIXTURE / f"{CASE['part']}.bin").read_bytes() == blob
    assert json.loads((FIXTURE / "case.json").read_text(encoding="utf-8"))["models"] == case_models()


def test_a_sealed_part_opens_with_its_key_and_its_name_only():
    pytest.importorskip("cryptography")
    from cryptography.exceptions import InvalidTag
    key = S.derive(CASE["passphrase"], iterations=CASE["iterations"])
    _, blob = sealed_case()
    assert S.unpack(S.unseal(key, CASE["part"], blob)) == case_models()
    with pytest.raises(InvalidTag):
        S.unseal(key, "TESTQ2", blob)                     # one part's file cannot stand in for another's
    with pytest.raises(InvalidTag):
        S.unseal(S.derive("another passphrase", iterations=CASE["iterations"]), CASE["part"], blob)


def test_an_unchanged_part_seals_to_the_same_bytes_and_a_changed_one_does_not():
    pytest.importorskip("cryptography")
    key = S.derive(CASE["passphrase"], iterations=CASE["iterations"])
    a = S.seal(key, "P", S.pack({"k": "text"}))
    assert a == S.seal(key, "P", S.pack({"k": "text"}))
    b = S.seal(key, "P", S.pack({"k": "text2"}))
    assert a[:12] != b[:12]                               # a new IV for new content
    assert S.manifest(key)["check"] == S.manifest(key)["check"]
    assert S.manifest(key)["kdf"] == {"name": "PBKDF2", "hash": "SHA-256", "iterations": 600_000,
                                      "salt": "c3BpY3ktZWxlY3Ryb25pY3MtaW5kZXggc2VhbGVkIG1vZGVscyB2MQ=="}


def test_the_passphrase_is_read_trimmed_and_in_one_spelling():
    assert S.normal("  café x \n") == "café x"
    assert S.derive(" café ", iterations=10) == S.derive("café", iterations=10)


def test_a_new_passphrase_is_long_private_and_never_overwritten(tmp_path):
    p = S.new_passphrase(tmp_path / "pass.txt")
    phrase = S.passphrase(p)
    assert len(phrase) == 29 and set(phrase) <= set(S.ALPHABET + "-")
    assert p.stat().st_mode & 0o077 == 0
    with pytest.raises(SystemExit):
        S.new_passphrase(p)
    (tmp_path / "short.txt").write_text("hunter2\n")
    with pytest.raises(SystemExit):
        S.passphrase(tmp_path / "short.txt")


LIB = """.MODEL 2 NPN(IS=1E-13 BF=80)
.model Q2N3055_ NPN(IS=4.66p BF=360 BR=2)
.model QBASE NPN(IS=1f BF=200)
.model QAKO AKO:QBASE NPN(BF=150 BR=2)
.subckt AMP 1 2 3
Q1 1 2 3 QIN
R1 2 3 2
.ends
.model QIN NPN(BF=50)
"""


def test_a_paste_holds_what_the_definition_references_and_not_a_number_that_names_another():
    defs = F.blocks(LIB)
    # found.closure takes in `.MODEL 2` for BR=2, and the model's identity keeps it that way
    assert [n for _, n, _ in F.closure(defs, "Q2N3055_")] == ["2", "Q2N3055_"]
    assert [n for _, n, _ in S.paste_chain(defs, "Q2N3055_")] == ["Q2N3055_"]
    assert [n for _, n, _ in S.paste_chain(defs, "QAKO")] == ["QBASE", "QAKO"]
    assert [n for _, n, _ in S.paste_chain(defs, "AMP")] == ["QIN", "AMP"]
    assert S.paste_chain(defs, "nothing") == []


def test_a_subcircuit_is_closed_with_ends():
    endl = ".subckt X 1 2\nR1 1 2 1k\n.ENDL X\n.model AFTER D\n"
    assert S.closed("subckt", endl) == ".subckt X 1 2\nR1 1 2 1k\n.ENDS"
    assert S.closed("subckt", ".subckt X 1 2\nR1 1 2 1k\n").endswith("R1 1 2 1k\n.ENDS")
    assert S.closed("subckt", ".subckt X 1 2\n.ends X\n") == ".subckt X 1 2\n.ends X\n"
    assert S.closed("model", ".model Q NPN\n") == ".model Q NPN\n"


def test_a_curated_file_loses_the_header_the_curation_wrote(tmp_path):
    p = tmp_path / "x.lib"
    p.write_text("* PART:      X\n* MODEL:     X\n* CHANGED:   caret_power: ...\n*\n.model X NPN(BF={2**3})\n\n")
    assert S.curated_text(p) == ".model X NPN(BF={2**3})\n"
    p.write_text("* the author's own comment\n.model X NPN\n")
    assert S.curated_text(p) == "* the author's own comment\n.model X NPN\n"


def test_the_heading_says_whose_model_and_where_in_ascii():
    row = {"source": "bordodynov", "name": "Qµ", "get": {"url": "http://example.org/lib.zip", "member": "cmp/standard.bjt"}}
    assert S.heading(row) == "* Qu from bordodynov: http://example.org/lib.zip (cmp/standard.bjt)"
    assert S.heading({"source": "ltspice-native", "name": "2N3904", "get": {"installed_with": "LTspice 17"}}) == \
        "* 2N3904 from ltspice-native: ships with LTspice 17"
