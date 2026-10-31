# Spicy Electronics Index

A non-commercial database for analog-audio electronics hobbyists, made by a hobbyist and served as a
static website with no backend: [electrucio.github.io/spicy-electronics-index](https://electrucio.github.io/spicy-electronics-index/).

When you start out in this hobby it is hard to know where to find SPICE models, which of them can be
trusted, where the datasheets are, what a part number means, and which real circuits use a given part.
This project collects those answers per part number (for example `2N2222`, `TL072`, `12AX7`), with an
emphasis on audio and analog electronics.

## What it contains

| Pillar | What you get |
|---|---|
| **Schematic and reference index** | For each part number, links to factory schematics, project sites, classic electronics magazines, books and historical references that use it, with the page and the position on the page. |
| **SPICE models and datasheets** | Where each model can be found, who published it, under which terms, and links to the datasheets of the main manufacturers. |
| **Model characterisation** | Each transistor model is measured the same way in three simulators (QSPICE, ngspice, LTspice), so you can see what it does before you trust it. |

## Links, not copies

The repository stores **no third-party documents**. Schematics, magazine scans, books and datasheets are
referenced by public URL only. Manufacturer SPICE models that may not be redistributed are indexed and
linked, with a recipe (URL + checksum) that lets you download them yourself; model files are hosted here
only when their licence allows it. If something listed here should not be, see [TAKEDOWN.md](TAKEDOWN.md).

## Running it

Four tools, installed by hand: `git`, `make`, [`uv`](https://docs.astral.sh/uv/), which fetches Python itself
(3.11 or newer), and, for the site only, [Node.js](https://nodejs.org/) 20 or newer (the published site is
built with Node 24). Nothing is installed globally with npm: the TypeScript compiler and Vite come with
`make setup`.

```
make setup      # dependencies, Python and site, and the pre-commit guard
make            # every step, one line each
make web        # build the site from data/ into web/dist
make serve      # the same with live reload, at http://localhost:8026/spicy-electronics-index/
```

A local build has every page but no measurements: the characterisation records are a release asset, not
in git. With the GitHub CLI (`gh`) installed, `make bench-character-fetch` downloads them and the next
`make web` includes them.

The public dataset is in `data/`; the code in `src/spicy_electronics_index/`, run as `sei`. Crawling, OCR, index
builds and simulator runs need the private corpus and happen on the maintainer's machine; everything that
builds the site needs only `data/`.

## Contributing

Most contributions need neither the private corpus nor a GPU: adding a reference for a part, reporting a
wrong link, proposing a source site, adding what a part is with its source, or working on the website. See [CONTRIBUTING.md](CONTRIBUTING.md). The repository is set up for working with
Claude Code; [CLAUDE.md](CLAUDE.md) holds the project rules.

## Licence and disclaimer

A non-commercial hobby project, made by a hobbyist for hobbyists.

- ✓ Use it for free, for your own projects, study and hobby
- ✓ Copy, share and adapt any part of it, as long as it is not for commercial use
- ✓ Use it in schools, universities, clubs and other non-profit organisations
- ✓ Build your own circuits with what you find here
- ✗ **No commercial use**: do not sell it, use it in a paid product or service, or republish it for money
- ✗ Do not share it without crediting it as
  `Spicy Electronics Index by Electrucio, https://electrucio.github.io/spicy-electronics-index/, CC BY-NC-SA 4.0`
- ✗ Do not publish a changed version of the index under other terms
- ✗ Do not rely on it blindly: it comes with **no warranty**, so check what matters against the data sheet

The code (`src/`, `scripts/`, `web/`, `docker/`, `tests/`) is under
[PolyForm Noncommercial 1.0.0](LICENSES/PolyForm-Noncommercial-1.0.0.txt); everything else, meaning the index
and the rest of `data/`, the documentation, the drawings and the website, is under
[CC BY-NC-SA 4.0](LICENSES/CC-BY-NC-SA-4.0.txt). Third-party model files keep their original licence, stated
next to each file. Details: [LICENSE](LICENSE) and [NOTICE](NOTICE).
