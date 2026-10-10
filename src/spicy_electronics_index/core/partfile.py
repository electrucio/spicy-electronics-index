"""The file a part's data is served from: its page, its characterisation and its sealed models.

A part is its own file name, so that the site can ask for it without a lookup. Two names that differ
only in case are two parts (`CORE` and `Core` are different models, `DPDT` a relay and `dpdt` a switch),
but a case-insensitive disk — a Mac's, Windows' — keeps only one of two such files. So a name with
lower-case letters carries a suffix that says which letters those are: `Core` is `Core~e`, `core`
`core~f`. A name in capitals, which is nearly every part, is unchanged.

`web/src/data.ts` (`partFile`) is the other half; `tests/fixtures/part_files.json` is checked by both.
"""
from __future__ import annotations

MARK = "~"


def part_file(part: str) -> str:
    """The part's file name, without the extension; a slash in it stays a folder."""
    if MARK in part:
        raise ValueError(f"a part name may not hold {MARK!r}: {part!r}")
    mask = 0
    for i, ch in enumerate(part):
        if ch != ch.upper():
            mask |= 1 << i
    return f"{part}{MARK}{mask:x}" if mask else part
