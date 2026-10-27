# Soviet analogues of foreign transistors: Aksenov, Nefedov and Yushin (MRB 1190)

Where the `approximate_analogue_of` rows of `data/parts/relations.csv` come from, and how they were read, so
the trail can be followed and the reading repeated.

## The trail

1. [Canifol](https://github.com/invisiblelevel/canifol), a repair technician's toolkit posted on Reddit on
   2026-10-26 (MIT), ships `src/lib/data/analogs.json`: 2,395 transistor names, Soviet and foreign, each with
   its analogues, parsed from a PDF the program does not name. Nothing was taken from it: an app is not a
   source (CLAUDE.md rule 7). It only said that such a table existed.
2. The table is **"Зарубежные транзисторы и их отечественные аналоги"** (foreign transistors and their domestic
   analogues), a 19-page PDF an anonymous compiler posted as an attachment on the hobbielektronika.hu forum
   (reference S99: 235,148 bytes, sha256 `e01750d0984e6c255b856a13df3c35dbb507c88af2689eff8f4c5f677e13c70f`).
   Three columns: foreign type, package, "приближенный отечественный аналог" — *approximate* domestic
   analogue. Its last page names the book it was typed from.
3. The book is **А. И. Аксенов, А. В. Нефедов, А. М. Юшин. Элементы схем бытовой радиоаппаратуры. Диоды.
   Транзисторы: Справочник** (elements of consumer radio circuits: diodes, transistors — a handbook), Moscow:
   Радио и связь, 1992, issue 1190 of the Массовая радиобиблиотека series, ISBN 5-256-00964-8 (reference
   S98). The series list at radionostalgia.ca records it under 1992; the TUSUR library catalogue files the
   same ISBN under 1993. The book itself was not read: no copy a reader can open was found, only the
   extract. The series' issue 1154, Нефедов and Гордеева's "Отечественные полупроводниковые приборы и их
   зарубежные аналоги" (1990), runs the other way, Soviet to foreign, and is not used here.

## What the relation says

"Approximate domestic analogue" is the handbook's own heading: the Soviet type its authors judged nearest to
the foreign one, by their reading of the sheets. Nobody declares the two interchangeable, so the relation is
worth `("both", "similar")` in `catalogue.COVERAGE`: a part like it, in either direction, never a substitute
a document names. Every row is `draft`, as every relation is until reviewed.

## How the extract was read

`extract.py` reads the PDF's text layer with PyMuPDF (the project's reader), walks the three columns in turn
and keeps a pair when the foreign type or the Soviet one is a part the index knows or wants:

```
uv run python -I docs/surveys/aksenov-mrb1190/extract.py <the PDF> > rows.csv
```

On 2026-10-28: 2,408 table rows, 2,351 pairs, **393 rows touching the index** (319 silicon BJTs, 49 germanium,
the rest the index files as "transistor"), naming 187 Soviet types, of which only MP42B and P416 were already
in the index. The Soviet part is transliterated the way the index already names those two — Б B, В V, Г G,
Д D, Е E, Ж ZH, И I, К K, М M, П P, Т T — and the Cyrillic original and the package stay in the note.

The typist's habits the script puts right: Cyrillic look-alikes in the Latin column (ВС170В is BC170B), З and
О among digits (ГТЗЗОЖ is ГТ330Ж), cells of several analogues ("МП42Б, МП20А"), suffix lists and ranges
("КТ373 (Б, В)", "KT818 (АМ—ГМ)"). What it drops, by rule 4 (precision over recall): an analogue typed in
Latin letters whose suffix could be Б or В ("KT342B": 26 such, for parts the index has, listed on stderr),
and any name that does not look like a Soviet type number afterwards.

Three foreign parts the index files under another kind are in the table as transistors — BF254 (filed as a
JFET; an NPN RF transistor), OC28 and OC201 (filed as diodes; germanium power transistors) — which is a
flaw in the index's kinds, not in the handbook, left for the catalogue to fix.

## What is not here

Canifol's other data: its SMD marking-code table (parsed from a commercial databook, and markings on
packages are not what this index reads), its pinouts (unsourced) and its live look-ups (DigiKey's API with
the author's own credentials, LCSC's and JLCPCB's internal APIs under a borrowed browser user-agent — what
rule 3 forbids). LCSC's data-sheet host, `wmsc.lcsc.com`, disallows every robot in its robots.txt (read
2026-10-27), which settles that question for scripts.
