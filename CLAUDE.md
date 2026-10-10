# Spicy Electronics Index — project rules

Non-commercial database for analog-audio electronics hobbyists: a static website (no backend) that answers,
per part number, "where is it used, where are its SPICE models and data sheets, and how good are the models".

## Map

`make` lists every step, `sei --help` every command, `make paths` every location and which side of the
public/private line it is on. Those three are always current; this map only says what lives where.

- `src/spicy_electronics_index/` the code, one package per pillar:
  - `core/` shared: `config` (every location), `http` (the one polite client), `ledger`, `llm`, `links`
    (with `web/src/links.ts` as its other half), `partfile` (with `web/src/data.ts`), `parts/` (the
    part-number extractor and the catalogue of what a part is);
  - `schematics/` the schematic index: crawl, download, OCR, ingest, reindex, verify, summarise, export;
  - `models/` SPICE models: fetch, ingest, index, reconcile, match, found, promote, seal;
  - `datasheets/` what makers' catalogues and data sheets say about each part;
  - `bench/` characterises every transistor model at the conditions of `data/bench/measurements.yaml`;
  - `web/` builds the site's data from `data/` alone.
- `data/` the public dataset: registries (`sources.yaml`), ledgers (`state/`), exports and recipes.
- `web/` the site (Vite + TypeScript + Preact). `docker/` the images the pipeline runs in (simulators,
  circuit drawings, the data-sheet reader). `docs/` the bench specification.
- `private_material/` (git-ignored, on the maintainer's machine): OCR, downloads, caches and work in
  transit. `private_web_spice_models/` (git-ignored, permanent): the vendor model text and symbols.

## Hard rules

1. **Links, not copies.** Never commit third-party documents, PDFs, scans, OCR text or manufacturer model
   text: publish URL + sha256 + metadata. Model files go in `data/models/files/<source>/` only when the
   source's licence allows it, with its LICENSE file. Three exceptions, each published as a release asset
   the Pages build downloads (never in git), so deleting the asset withdraws it:
   - **data-sheet crops**: one table row or one graph beside our transcription or simulation of it, with
     maker, document, revision, page and a link to the PDF; never whole pages;
   - **sealed model text** for the maintainer only (`sei models seal`, AES-GCM under a passphrase kept
     outside the repository, opened in the browser with `#unlock`). The passphrase is never shared, written
     into the repository or put in a URL, and the plaintext never leaves the private tree;
   - **drawings of the LTspice symbols** a model is published with (`sei web symbol-drawings`), shown
     beside the link to the publisher's file; the `.asy` itself is never served.
2. **Forbidding redistribution does not forbid indexing.** Every model is indexed and linked to its source;
   for non-redistributable ones publish measured results, not the `.model` parameters.
3. **Never bypass** a CAPTCHA, login, paywall, click-through licence or bot challenge. Respect robots.txt
   and per-host delays (use `core.http`). A blocked source is recorded as blocked, with the URL a person can
   follow. A 429 from a site whose robots.txt allows us is a complaint about pace, not a refusal: come back
   slower, later, or from the maintainer's browser at human pace (`paused`, with the pace to try next).
   Disguise is never a means: no borrowed user-agent, no other address, no solving the challenge. Only a
   refusal that holds at any pace is `blocked`. **On a forum, index the attachments, never the
   conversation**, and only schematics, worked projects and models among them.
4. **Precision over recall.** A wrong link is worse than no link. When a part read is doubtful, drop it.
   Every extractor fix comes with a test case.
5. **Never reprocess what is done.** Every stage goes through `core.ledger`: an item is skipped when its
   stamp matches (input sha256, stage version). Reprocess by bumping the stage version, never by deleting or
   hand-editing state.
6. **Nothing under the two private trees is ever added to git**, and nothing public may depend on a local
   path, a personal e-mail address or a secret — including inside a published URL. **Every location is
   named in `core.config` and nowhere else** (`tests/core/test_config.py` fails otherwise). Credentials live
   outside the repository. `scripts/licence_guard.py` enforces the rest in the pre-commit hook and in CI.
7. **No fact without a source.** What a part is, how parts relate, which model is a stand-in for which:
   each names a source a reader can open. An LLM is never a source.
8. Everything public is in **English**.
9. Commit in small, reviewable steps once `make check` passes. Push and deploy only when the maintainer asks.

## Working here

```
make setup      # dependencies and the pre-commit guard, once per clone
make check      # guard + lint + tests, Python and web — what CI runs
make status     # what has been processed and what comes next, per source (make status-write: STATUS.md)
make backup     # pack the private trees into one archive to carry off this machine
```

Each `make` target is a thin wrapper around `sei`; a new `sei` command gets its `make` target in the same
commit. Python ≥ 3.11, run through `uv`.

## Extending

- **A new schematic site or model vendor**: a registry entry (`data/schematics/sources.yaml` with
  `status: proposed`, or `data/models/sources/<id>.yaml`), then run that source only.
- **A new stage**: a ledger stage with a version, a `sei` command and its `make` target, and the locations
  it uses added to `core.config`.
- **New wanted parts**: `data/models/wanted.yaml` (by hand) or `data/parts/wanted.csv` (generated lists),
  then `make models-match models-found models-promote`.
- **A hand-gathered delivery** (a browser round): `make models-ingest FROM=<zip> DRY=1`, then without `DRY`.

Effort is estimated as "Claude sessions + waiting time", never person-days.
