# docker/datasheets — reading data-sheet tables with a vision-language model

Turns a maker's data sheet into rows — symbol, test conditions, min/typ/max, unit — so SPICE models can be
held against the sheet of their part. The rule is the project's: **the data sheet is the source; the model
only transcribes it**, and it is never trusted on its word.

- `render.py` — the reference pages as PNG at 150 dpi.
- `extract.py` — one prompt, three ways of showing a page: `image`, `text` (the PDF's text layer plus
  PyMuPDF's rebuilt tables) or `image+text`; `--second-look` asks again for the rows the first answer left
  out.
- `evaluate.py` — scores a run against `golden.yaml` and looks every returned number up in the page's text
  layer.
- `figures.yaml` — the reference sheets' graphs (box on the page, axes, series), published by
  `make datasheets-figures`.

```sh
make vlm-image vlm-models VLM_MODELS=/path/to/models   # docker/vlm/README.md
make vlm-serve VLM_MODELS=/path/to/models               # VLM_GPU=1 by default
make sheets-pages
make sheets-extract METHOD=image [NAME=run]
make sheets-evaluate RUNS='private_material/datasheet_lab/runs/<run> …'
make vlm-stop
```

Pages, runs and results go to `private_material/datasheet_lab/` (`DATASHEET_LAB`), never into the
repository: the pages are third-party documents. The PDFs come from the private data-sheet store
(`DATASHEET_PDFS`, whose `manifest.json` gives each file's URL).

**The recipe that holds up:** the page image with a second look; every number checked against the text
layer; the conditions checked for plausibility against the part; whatever fails a check, plus a sample of
what passes, to a person. Do not feed the model the text layer: it copies its faults (a µ in a symbol font
dropped, so "100 µA" becomes "100 A"). The model does not invent numbers; it omits rows silently and
confuses subscripts (VDG read as VDS), which no check against the page catches — only the reference does.

## The reference set

`golden.yaml`: 20 data sheets chosen to be awkward in different ways — several makers and decades, tables
with and without rules, several parts per table (2N3903/2N3904, BC546…550, 2N7000/2N7002), grades (LSK170
A–D), PNP sheets printing negative values, typos in the sheets themselves. Read off the page images and
checked against readers that fail differently: every value is on its page's text layer, and every
disagreement with the model's readings was settled on a 300-dpi crop. A misreading every reader shares
cannot be ruled out; a person's spot check is still owed, and the set is the thing to grow (older and
scanned sheets, where there is no text layer to check against).
