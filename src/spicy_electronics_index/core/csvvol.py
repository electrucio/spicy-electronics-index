"""A public CSV too big for one file, written and read as volumes.

`x.csv` holds the header and the first rows; when it reaches `MAX_BYTES` the rows go on in `x.2.csv`,
then `x.3.csv`, each with the header again, so every volume is a CSV on its own and a diff of one reads
like a diff of any other. A file that fits stays one file, named as it always was, so nothing changes
for the sources that never grow this big. The names are `config.volume`'s; readers ask `volumes()`.

A volume is never mistaken for a source: source names have no dot in them, and `is_volume` is how a
reader that lists a directory tells the two apart.
"""
from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from pathlib import Path

from spicy_electronics_index.core.config import volume

MAX_BYTES = 40_000_000        # under the guard's 50 MB, with room for a volume to grow between exports


def volumes(path: Path) -> list[Path]:
    """Every volume of `path` there is, in reading order; empty when the file does not exist."""
    out, n = [], 1
    while volume(path, n).exists():
        out.append(volume(path, n))
        n += 1
    return out


def is_volume(path: Path) -> bool:
    """Whether this file is a continuation volume (`x.2.csv`), not the first file of something."""
    return "." in path.stem


def read(path: Path) -> Iterator[dict]:
    """The rows of every volume, in order, as dicts."""
    for p in volumes(path):
        with open(p, newline="", encoding="utf-8") as f:
            yield from csv.DictReader(f)


def write(path: Path, fields, rows: Iterable, max_bytes: int = MAX_BYTES) -> int:
    """Write `rows` under `fields` as one file or as volumes; returns the row count. Volumes left over
    from a longer previous write are removed, or a reader would take their stale rows for current ones."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_vol, n, f = 0, 0, None
    try:
        for r in rows:
            if f is None or f.tell() >= max_bytes:
                if f is not None:
                    f.close()
                n_vol += 1
                f = open(volume(path, n_vol), "w", newline="", encoding="utf-8")
                w = csv.writer(f, lineterminator="\n")
                w.writerow(fields)
            w.writerow(r)
            n += 1
        if f is None:                                   # no rows: the file still says what it would hold
            n_vol = 1
            f = open(path, "w", newline="", encoding="utf-8")
            csv.writer(f, lineterminator="\n").writerow(fields)
    finally:
        if f is not None:
            f.close()
    stale = n_vol + 1
    while volume(path, stale).exists():
        volume(path, stale).unlink()
        stale += 1
    return n
