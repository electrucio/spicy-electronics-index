"""The words of a text as the Projects tab looks them up: the same rules here and in `web/src/words.ts`.

The summaries `summarise` wrote — one line per part per page — are where a magazine page that a title calls
"Elektor 1975-02" says it is a wah pedal, so the site can look words up in them. It cannot carry them whole
(135 MB), so the build keeps which units each word is on, split by the word's first two letters, and the
browser fetches the split a word falls in. Both sides cut text into words by these rules, and
`tests/fixtures/words_cases.json` holds them to it.

Kept: words of two letters or more, a number of four digits or more (a year, a 7025), and codes of letters
and digits (AB763). A word written with hyphens is kept joined as well as in pieces: 5F6-A is looked up as
5F6A, op-amp as opamp. Left out: designators and values, which the lines are full of and nobody searches for
(R12, C3, IC1, 10k, 100nF), short numbers and the commonest small words.
"""
from __future__ import annotations

import re
import unicodedata

STOP = frozenset("""
a an and are as at be been but by for from has have in into is it its near next not of on or so than that the
their then there these this those to two used uses using was were where which while with within without also
one three part parts page pages shown labelled labeled listed list located positioned beside appears appearing
""".split())
DESIGNATOR = re.compile(r"(?:r|c|q|d|l|t|u|v|j|k|p|s|f|x|ic|tr|vr|rv|sw|led|zd|tp|cn|fb|jp|rl)\d{1,4}[a-z]?")
VALUE = re.compile(r"\d+(?:[kmrunp]\d*|uf|nf|pf|v|w|ma|mv|hz|khz|mhz|db|ohms?)")
HYPHENED = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")


def fold(text: str) -> str:
    """Lower case, accents off: what a reader types."""
    t = unicodedata.normalize("NFKD", text)
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def kept(w: str) -> bool:
    if len(w) < 2 or w in STOP:
        return False
    if w.isdigit():
        return len(w) >= 4
    return not (DESIGNATOR.fullmatch(w) or VALUE.fullmatch(w))


def words(text: str) -> list[str]:
    """The words of `text` the index keeps, each once, in the order they come."""
    t = fold(text)
    out: list[str] = []
    for m in HYPHENED.finditer(t):
        joined = m.group(0).replace("-", "")
        if kept(joined) and joined not in out:
            out.append(joined)
    for w in re.split(r"[^a-z0-9]+", t):
        if kept(w) and w not in out:
            out.append(w)
    return out


def shard_of(word: str) -> str:
    """Which split of the index a word is in: its first two letters."""
    return word[:2]
