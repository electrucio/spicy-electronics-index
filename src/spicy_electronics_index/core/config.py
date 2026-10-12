"""Where everything is. This is the only module allowed to name a location.

No other module joins a path: it asks here. That keeps one rule checkable in one place —

    PUBLIC   lives in the repository and is committed: registries, ledgers, the exported index,
             model recipes, licence notes, verification results, the part dictionary, the website.
    BUILT    lives in the repository but is generated and git-ignored: the site's data files.
             Deleting it costs a rebuild, nothing more.
    PRIVATE  never committed, in two trees with different lifetimes:
             `private_web_spice_models/` is permanent — the vendor model text and symbols the site
             shows its maintainer sealed (`models/seal.py`), which licences forbid publishing;
             `private_material/` holds the OCR of everything scraped, with the map and the index over
             it, and the work in transit around them (`sei backup` says which is which).

Both are `$SEI_SPICE_MODELS` / `$SEI_MATERIAL` if you keep them elsewhere. `.gitignore` and
`scripts/licence_guard.py` both refuse them. Private accessors are wrapped in `require()` by their caller
so a contributor without them gets an explanation instead of a stack trace.

    sei paths        prints every location, resolved, marked public, built or private
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_DATA = REPO_ROOT / "data"


class PrivateDataMissing(RuntimeError):
    """Raised when work needs the private corpus and it is not here."""


def spice_models_root() -> Path:
    """Permanent: the vendor model text and symbols. Not publishable, not re-fetchable for the vendors
    that block us, and what the site shows its maintainer sealed."""
    env = os.environ.get("SEI_SPICE_MODELS")
    return Path(env).expanduser() if env else REPO_ROOT / "private_web_spice_models"


def material_root() -> Path:
    """The OCR of everything scraped, the index over it, and the work in transit around them."""
    env = os.environ.get("SEI_MATERIAL")
    return Path(env).expanduser() if env else REPO_ROOT / "private_material"


def require(path: Path, why: str) -> Path:
    """Return `path`, or explain that this task needs the private data root."""
    if not path.exists():
        raise PrivateDataMissing(
            f"{why} needs {path}, which is not here. This step runs on the machine that holds the "
            f"corpus; set SEI_MATERIAL or SEI_SPICE_MODELS if yours is elsewhere. Everything under data/ "
            f"works without it."
        )
    return path


# --- public: the schematic index -------------------------------------------------------------------
def schematics_dir() -> Path:
    return PUBLIC_DATA / "schematics"


def schematics_registry() -> Path:
    """The source registry: add a site here to have it crawled."""
    return schematics_dir() / "sources.yaml"


def schematics_state(source: str) -> Path:
    """Processing ledger, one row per URL."""
    return schematics_dir() / "state" / f"{source}.csv"


def schematics_documents(source: str) -> Path:
    return schematics_dir() / "documents" / f"{source}.csv"


def schematics_pages(source: str) -> Path:
    return schematics_dir() / "pages" / f"{source}.csv"


def schematics_uses(source: str) -> Path:
    """Where each part was read: part, document, page, position."""
    return schematics_dir() / "uses" / f"{source}.csv"


def schematics_lines(source: str) -> Path:
    """One line per published use, saying what that part is doing on that page. Written by `summarise`
    through `export`, and kept beside the uses rather than inside them: a re-run of the model changes
    every line and nothing else, and a diff of that is worth reading."""
    return schematics_dir() / "lines" / f"{source}.csv"


def volume(path: Path, n: int) -> Path:
    """Volume `n` of a public CSV too big for one file: `x.csv`, then `x.2.csv`, `x.3.csv`. Plain CSV
    each, with its header, so a diff stays readable — audiocircuit's lines alone are 98 MB, and GitHub
    stops at 100. `core.csvvol` writes and reads them; this is only where their names are made."""
    return path if n == 1 else path.with_name(f"{path.stem}.{n}{path.suffix}")


def schematics_suspects() -> Path:
    """Parts whose published uses the model reads as something that is not a component at all — a record
    catalogue number, a resistor value, a designator, a piece of surplus equipment for sale. A by-product
    of summarising, and the shortlist for the next pass over the extractor (rule 4)."""
    return schematics_dir() / "suspects.csv"


def schematics_parts() -> Path:
    return schematics_dir() / "parts.csv"


def schematics_export_manifest() -> Path:
    return schematics_dir() / "export.json"


def schematics_withdrawn() -> Path:
    """Documents removed on request; the export gate consults it every time."""
    return schematics_dir() / "withdrawn.csv"


def schematics_curated(part: str | None = None) -> Path:
    """References added by hand, needing no corpus."""
    d = schematics_dir() / "curated"
    return d / f"{part}.yaml" if part else d


def schematics_overrides() -> Path:
    return schematics_dir() / "overrides.csv"


# --- public: SPICE models, datasheets, verification -------------------------------------------------
def models_dir() -> Path:
    return PUBLIC_DATA / "models"


def model_sources(source: str | None = None) -> Path:
    d = models_dir() / "sources"
    return d / f"{source}.yaml" if source else d


def model_state(source: str) -> Path:
    return models_dir() / "state" / f"{source}.csv"


def model_part(kind: str, part: str) -> Path:
    """The recipe for one part: candidates, where to get each, licence, verification."""
    return models_dir() / "parts" / kind / f"{part}.yaml"


def model_licence(source: str) -> Path:
    return models_dir() / "licences" / f"{source}.md"


def model_files(source: str) -> Path:
    """Model text we are allowed to host. Only for sources marked redistributable."""
    return models_dir() / "files" / source


def model_changes() -> Path:
    """The fixups we apply to a model's text, named once with the reason for each."""
    return models_dir() / "changes.yaml"


def model_wanted() -> Path:
    """The parts the model curation looks for, by kind, with the other names each one goes by and the
    parts declared to stand in for it. Written by hand; `wanted_parts` is the list generated from shops,
    databooks and documents."""
    return models_dir() / "wanted.yaml"


def model_non_native() -> Path:
    """The models of devices SPICE has no element for — loudspeakers, transformers, pots, switches, relays,
    lamps, light-dependent resistors, thermistors — each listed under the part it is a model of, or under
    its own name when it is generic, and named by its code so nothing else of that name joins it."""
    return models_dir() / "non_native.yaml"


def datasheets_table() -> Path:
    """What each manufacturer's catalogue says about a part: category, status, data sheet title and link."""
    return PUBLIC_DATA / "datasheets" / "datasheets.csv"


def datasheet_links(source: str) -> Path:
    """Every data sheet one archive or catalogue links for each part: maker, link, size, language."""
    return PUBLIC_DATA / "datasheets" / "links" / f"{source}.csv"


def datasheet_documents(source: str) -> Path:
    """The data sheets a manufacturer publishes that were read: title, revision, pages, checksum."""
    return PUBLIC_DATA / "datasheets" / "documents" / f"{source}.csv"


def datasheet_covers(source: str) -> Path:
    """Which known parts each of those sheets documents, and whether that was seen on its first page."""
    return PUBLIC_DATA / "datasheets" / "covers" / f"{source}.csv"


def datasheet_pages(source: str) -> Path:
    """The pages of old databooks that head a known part: book, page, printed page number."""
    return PUBLIC_DATA / "datasheets" / "pages" / f"{source}.csv"


def datasheet_catalogue(source: str) -> Path:
    """What a manufacturer's own product list says about each indexed part it makes: category, status,
    and the data sheet it gives for it."""
    return PUBLIC_DATA / "datasheets" / "catalogue" / f"{source}.csv"


def datasheet_polarity() -> Path:
    """Which way round each transistor is, read off a page found for it: the words that say so, and the
    page's link and checksum."""
    return PUBLIC_DATA / "datasheets" / "polarity.csv"


def datasheets_registry() -> Path:
    """The manufacturer catalogues the data-sheet register reads, and at what pace."""
    return PUBLIC_DATA / "datasheets" / "sources.yaml"


def datasheets_state(source: str) -> Path:
    """One ledger row per part asked of that catalogue."""
    return PUBLIC_DATA / "datasheets" / "state" / f"{source}.csv"


def datasheet_values_index() -> Path:
    """The data sheets whose characteristics rows are published: each with its link, checksum, maker,
    title, and who read the rows, how and when."""
    return PUBLIC_DATA / "datasheets" / "values.csv"


def datasheet_values(doc: str) -> Path:
    """One data sheet's rows as printed — symbol, conditions, min, typ, max, unit — with the page and the
    box on it where each was read, so the crop beside it on the site can be checked against the PDF."""
    return PUBLIC_DATA / "datasheets" / "values" / f"{doc}.csv"


def datasheet_figures(doc: str) -> Path:
    """One data sheet's figures: where each is on its page, and what it plots — axes, scales, series,
    conditions, and the bench that draws the same graph for a model."""
    return PUBLIC_DATA / "datasheets" / "figures" / f"{doc}.json"


def datasheet_figure_reference() -> Path:
    """The hand-read reference of data-sheet figures, the companion of `datasheet_reference`."""
    return REPO_ROOT / "docker" / "datasheets" / "figures.yaml"


def datasheet_reference() -> Path:
    """The hand-read reference rows of 20 data sheets (docker/datasheets/README.md, "The reference set")."""
    return REPO_ROOT / "docker" / "datasheets" / "golden.yaml"


def verification(kind: str, part: str) -> Path:
    """One part's models held against its data sheet: what each card lacks, what each model's author
    declares, and what the bench measured at each of the sheet's rows."""
    return PUBLIC_DATA / "verification" / kind / f"{part}.json"


def verification_state() -> Path:
    """The ledger of that work: one row per part, and one per data sheet read."""
    return PUBLIC_DATA / "verification" / "state.csv"


def bench_measurements() -> Path:
    """The measurement catalogue: what the bench measures of every transistor model, how, and what each
    number tells (docs/model-characterisation.md). The decks read their conditions from it and the
    site's method page shows its text."""
    return PUBLIC_DATA / "bench" / "measurements.yaml"


def bench_drawings() -> Path:
    """The drawings of the bench circuits, one per measurement id (`<id>.svg`), shown on the method page
    when present."""
    return PUBLIC_DATA / "bench" / "drawings"


def character(model_hash: str) -> Path:
    """One model's characterisation: every measurement of the catalogue at the universal conditions, per
    simulator, with the digests of the decks that produced it. Keyed by the recipe's hash — the same
    model under every part that lists it — and sharded by its first two hex digits. Git-ignored: the
    records travel as a release asset (`bench.character_release`), named by `character_release()`."""
    return PUBLIC_DATA / "verification" / "models" / model_hash[:2] / f"{model_hash}.json"


def character_release() -> Path:
    """What characterisation is published, and where: the release asset holding every record of the current
    catalogue version, with its size and sha256 (`sei bench character-release`, `character-fetch`)."""
    return PUBLIC_DATA / "verification" / "models" / "release.json"


def character_state() -> Path:
    """The ledger of the characterisation: one row per model hash."""
    return PUBLIC_DATA / "verification" / "models" / "state.csv"


# --- public: what distributors sell of the parts ----------------------------------------------------
def distributors_registry() -> Path:
    """The distributor registry: who is asked, through which API, at what pace, under which terms, and
    the notice each asks to be shown beside its data."""
    return PUBLIC_DATA / "distributors" / "sources.yaml"


def distributors_table(distributor: str) -> Path:
    """What the distributor sells of each part — its order numbers, their status, stock and prices — as
    its API returned them on the day in `checked`. Values verbatim, nothing computed."""
    return PUBLIC_DATA / "distributors" / f"{distributor}.csv"


def distributors_files(distributor: str) -> Path:
    """The photos and documents the distributor links for each order number: URLs, never the files."""
    return PUBLIC_DATA / "distributors" / f"{distributor}_files.csv"


def distributors_state(distributor: str) -> Path:
    """Processing ledger, one row per part asked about."""
    return PUBLIC_DATA / "distributors" / "state" / f"{distributor}.csv"


def sellers_found() -> Path:
    """What following each seller's part search found, when a stage does: part, seller, result (found,
    not_found, unclear), the address followed, and the date. Absent until that stage exists."""
    return PUBLIC_DATA / "distributors" / "sellers_found.csv"


def sellers_registry() -> Path:
    """Where parts are bought, worldwide: each seller with its kind, base, catalogue and, where it has
    one, the address of a search for a part number. Links only; no seller's stock is read here."""
    return PUBLIC_DATA / "distributors" / "sellers.yaml"


# --- public: the part dictionary and the repository itself ------------------------------------------
def known_parts() -> Path:
    return PUBLIC_DATA / "parts" / "known_parts.csv"


def wanted_parts() -> Path:
    """Parts worth having that the index has nothing for yet, and who says so."""
    return PUBLIC_DATA / "parts" / "wanted.csv"


def rejected_tokens() -> Path:
    return PUBLIC_DATA / "parts" / "rejected_tokens.txt"


# --- public: what each part is — the catalogue beside the dictionary ---------------------------------
def part_families() -> Path:
    """The families a part can belong to, each with a definition, what choosing one comes down to, and
    the device kinds of the site that default to it."""
    return PUBLIC_DATA / "parts" / "families.yaml"


def documented_families() -> Path:
    """Parts whose family a manufacturer's own document states, with the reference that says so."""
    return PUBLIC_DATA / "parts" / "part_families.csv"


def part_relations() -> Path:
    """How parts relate — one sheet documents both, a maker offers one as the other's replacement, one
    product is sold under both names — each row citing the document that says so."""
    return PUBLIC_DATA / "parts" / "relations.csv"


def part_references() -> Path:
    """The books, datasheets, standards and histories the catalogue cites, as S01, S02… with how each
    link answered when it was last requested."""
    return PUBLIC_DATA / "parts" / "references.csv"


def naming_schemes(scheme: str | None = None) -> Path:
    """What the letters and digits of a part number mean, one file per numbering system (Pro Electron,
    JIS, JEDEC, the valve codes), transcribed from the standard or from the manufacturer that printed it."""
    d = PUBLIC_DATA / "parts" / "schemes"
    return d / f"{scheme}.yaml" if scheme else d


def part_makers() -> Path:
    """The organisations behind the parts: former names, headquarters with the date it was read, the
    prefixes they registered, and dated events such as acquisitions — each with its source."""
    return PUBLIC_DATA / "parts" / "makers.yaml"


def parts_census(source: str = "*") -> Path:
    """Which part numbers exist, according to a list whose job was to be complete about them.

    One file per source, as the schematic ledgers and document indexes are: together they passed the
    five megabytes a single file may have here, and a manufacturer's catalogue is the kind of thing
    that arrives twenty thousand rows at a time.
    """
    return PUBLIC_DATA / "parts" / "census" / f"{source}.csv"


def parts_benchmark() -> Path:
    """Labelled decisions on real pages: does this token, on this page, name a component. What every
    change to the extractor is measured against."""
    return PUBLIC_DATA / "parts" / "benchmark.csv"


def parts_verdicts() -> Path:
    """What each census name means *in this corpus*, judged once with the evidence, with the reason."""
    return PUBLIC_DATA / "parts" / "verdicts.csv"


def census_registry() -> Path:
    """The lists the census is read from: what each one covers, and on whose authority."""
    return PUBLIC_DATA / "parts" / "census_sources.yaml"


def census_state(source: str) -> Path:
    return PUBLIC_DATA / "parts" / "state" / f"{source}.csv"


def datasets_registry() -> Path:
    return PUBLIC_DATA / "datasets" / "registry.yaml"


def dataset_table(name: str) -> Path:
    """A result distilled from a research dataset: facts and links, never the dataset itself."""
    return PUBLIC_DATA / "datasets" / f"{name}.csv"


def docs_dir() -> Path:
    return REPO_ROOT / "docs"


def status_md() -> Path:
    return REPO_ROOT / "STATUS.md"


def web_dir() -> Path:
    return REPO_ROOT / "web"


def web_data() -> Path:
    """Build output of `sei web build`: git-ignored, rebuilt from data/ alone."""
    return web_dir() / "public" / "data"


def web_crops() -> Path:
    """The data-sheet crops the site shows beside a transcribed row or a simulated graph (CLAUDE.md
    rule 1): made by `sei datasheets crops` from the private PDFs, never committed, published as the
    release asset the Pages workflow unpacks here."""
    return web_data() / "crops"


def web_sealed() -> Path:
    """The model text sealed for the maintainer's eyes (`sei models seal`): one file per part, encrypted
    under a passphrase only the maintainer holds. Never committed, published as the release asset the Pages
    workflow unpacks here, like the crops."""
    return web_data() / "sealed"


def web_symbol_drawings() -> Path:
    """The LTspice symbols the recipes link, drawn as SVG (`sei web symbol-drawings`): pictures made from
    the publishers' .asy files, never the files (CLAUDE.md rule 1). Never committed, published as the
    release asset the Pages workflow unpacks here, like the crops."""
    return web_data() / "symbol-drawings"


def web_dist() -> Path:
    """Build output of `make web`: the site itself, git-ignored."""
    return web_dir() / "dist"


def tests_fixtures() -> Path:
    return REPO_ROOT / "tests" / "fixtures"


# --- private: the OCR of everything scraped, and the indexes over it -------------------------------
def ocr_root() -> Path:
    """One tree, `<source>/<name>.jsonl.gz`, whatever produced the records."""
    return material_root() / "ocr"


def ocr_superseded(source: str) -> Path:
    """A reading replaced by a better one, kept beside the tree rather than in it, so nothing that walks
    the OCR tree takes it for current. Private, like every reading."""
    return material_root() / "ocr_superseded" / source


def ocr_map() -> Path:
    """Which OCR file holds each document. Lives inside the tree, so copying it takes its index along."""
    return ocr_root() / "ocr_map.csv"


def summarise_preview() -> Path:
    """Every line the summarise pass has written so far, with the link the site would show beside it.
    A window into a run that takes days; the real export is `schematics_lines`, written when it ends."""
    return material_root() / "summarise_preview.csv"


def datasheets_cache(source: str) -> Path:
    """The head of each catalogue page the register read, compressed: third-party content, so it stays
    here, and a parser fix costs a re-read rather than another visit."""
    return material_root() / "datasheets_cache" / source


def datasheets_text(source: str) -> Path:
    """The text of every data sheet the harvest read, page by page, compressed: the manufacturer's, so it
    stays here, and a better reader costs no second download."""
    return material_root() / "datasheets_text" / source


def distributor_cache(distributor: str) -> Path:
    """Every answer the distributor's API gave, whole and gzipped, one file per part and endpoint. The
    public tables publish a few fields of it; a new use of the rest costs a re-read, not another call,
    and the distributor's terms can be met by deleting one directory."""
    return material_root() / "distributors" / distributor


def census_cache(source: str) -> Path:
    """The index pages a census source was read from. Third-party content, so it never leaves this tree;
    keeping it means a parser fix costs a re-read, not a re-crawl."""
    return material_root() / "census" / source


def linkchecks() -> Path:
    """Links checked by hand. Re-indexing regenerates every other judgement, but not these."""
    return ocr_root() / "linkchecks.csv"


def index_db() -> Path:
    """The full index: every document, its pages and their text. `reindex` and `ingest` only add to it —
    the figure-to-page links the old crawler recorded live nowhere else — so it is backed up with the
    OCR. Export from it by column allow-list, never wholesale."""
    return material_root() / "index.sqlite"


def index_db_uri(readonly: bool = True) -> str:
    """The only place this connection string is written."""
    return f"file:{index_db()}{'?mode=ro' if readonly else ''}"


def page_sizes() -> Path:
    """Page geometry in points, frozen before the PDFs went. Without it a link cannot carry a zoom."""
    return material_root() / "pagesizes.csv.gz"


def downloads(source: str) -> Path:
    """What the download stage fetched for a source, `<type>/<sha1(url)[:10]>_<name>`. In transit by the
    retention rule — download, extract, verify, delete — so only the OCR of it is kept."""
    return material_root() / "downloads" / source


def download_manifest(source: str) -> Path:
    """What the crawler already has for a source, so it resumes instead of starting again."""
    return material_root() / "manifests" / f"{source}.csv"


def source_list(source: str) -> Path:
    """URLs gathered for a source that cannot be crawled; the input for downloading it."""
    return material_root() / "source_lists" / f"assets_{source}.jsonl"


def toragi_index() -> Path:
    """CQ出版社's own index of every トランジスタ技術 article, as the publisher gives it away: TRDBWin25.zip
    with TR.txt inside (CP932, one comma-separated row per article since 1964). Fetched by hand from
    https://toragi.cqpub.co.jp/database/ and kept private, since it is their database and not ours."""
    return material_root() / "indexes" / "toragi" / "TRDBWin25.zip"


def toragi_reports() -> Path:
    """Coverage of トランジスタ技術 by year and by issue, written by `sei schematics toragi`."""
    return scratch() / "toragi"


def listing_cache(source: str) -> Path:
    """The index pages a list was gathered from. Kept for the same reason the census keeps its own: a
    changed `keep` pattern should cost a re-read, not another walk of somebody's sitemap."""
    return material_root() / "source_lists" / "cache" / source


# --- private: the SPICE models the site shows its maintainer, sealed --------------------------------
def spice_source(source: str) -> Path:
    return spice_models_root() / "sources" / source


def spice_source_doc(source: str) -> Path:
    """Licence analysis and how it was fetched; promoted to data/models/licences/ once translated."""
    return spice_source(source) / "SOURCE.md"


def spice_source_manifest(source: str) -> Path:
    return spice_source(source) / "manifest.json"


def spice_curated() -> Path:
    """Where the curation lives: one directory per part, holding its candidates and `part.json`."""
    return spice_models_root() / "models"


def spice_model_dir(kind: str, part: str) -> Path:
    """Curated model text for one part. Published only where its source allows redistribution."""
    return spice_curated() / kind / part


def spice_part_json(kind: str, part: str) -> Path:
    return spice_model_dir(kind, part) / "part.json"


# --- private: in transit ----------------------------------------------------------------------------
def spice_definitions() -> Path:
    """Every definition found, with its parameters: a copy of the models. Never published, and
    regenerated from the sources, so it is in transit."""
    return material_root() / "index.jsonl"


def spice_symbols() -> Path:
    """Every LTspice symbol (.asy) the model sources ship: which model it places and how many pins it has.
    Read from the private tree, so private too; `sei models symbols` writes it."""
    return material_root() / "symbols.jsonl"


def spice_matches() -> Path:
    """Every definition whose name matches a wanted part, per part: read from the definitions above,
    so it is in transit too."""
    return material_root() / "model_matches.json"


def spice_found() -> Path:
    """Those matches grouped into distinct models, each with every copy of it and where each can be had."""
    return material_root() / "model_found.json"


def spice_recipe_locations() -> Path:
    """Where each published recipe model was read from: `<kind>/<part>` to the model's identity (`hash`),
    file and name. Written by `models promote`, the only step that knows both; read by the steps that
    look inside a recipe's models (their cards, their authors' headers) and by the bench's publisher."""
    return material_root() / "model_locations.json"


def datasheets(kind: str | None = None) -> Path:
    """Vendor PDFs, kept until the simulation and datasheet-reading work is done."""
    d = material_root() / "datasheets"
    return d / kind if kind else d


def datasheet_store() -> Path:
    """The data sheets the reference set and the experiments read, with `manifest.json` giving each
    file's URL, checksum, maker and title."""
    return datasheets("vendor")


def simulators() -> Path:
    """The simulation stage's private side: the vendor store below, and the runs (docker/sim/README.md)."""
    return material_root() / "simulators"


def sim_bench() -> Path:
    """The bench's code as the simulator images run it (docker/sim/bench, mounted read-only)."""
    return REPO_ROOT / "docker" / "sim" / "bench"


def character_pack(asset: str) -> Path:
    """The archive of the records as it is uploaded to the release (`sei bench character-release`)."""
    return simulators() / "character" / "release" / asset


def character_runs(engine: str | None = None) -> Path:
    """The characterisation runs (`sei bench character`): the jobs — each with its card — and what each
    simulator returned, per engine and date. Private because the jobs carry the cards;
    `sei bench character-publish` publishes everything else."""
    d = simulators() / "character"
    return d / engine if engine else d


def simulator_vendor() -> Path:
    """What the simulator images are built from, each checked against docker/sim/sha256/: ngspice's
    tarball, LTspice's MSI and the captured QSPICE program folder. Never published, and the images built
    from them are never pushed. The last two cannot be fetched again — their makers serve only the
    current release — so this is backed up with the essentials."""
    return simulators() / "vendor"


def datasheet_lab() -> Path:
    """What the data-sheet reader (docker/datasheets) renders, reads and scores: pages, runs, results."""
    return material_root() / "datasheet_lab"


def datasheet_experiments() -> Path:
    """Earlier trials at reading data sheets, kept for their samples and analysis."""
    return material_root() / "datasheet_experiments"


def ocr_home() -> Path:
    """HOME inside the OCR image: where PaddleOCR keeps the models it downloads on first use."""
    return material_root() / "cache_ocr_home"


def remote_ocr() -> Path:
    """The scripts that ran OCR batches on a borrowed GPU machine. They name hosts, so they stay here."""
    return material_root() / "remote_ocr"


def remote_llm() -> Path:
    """The scripts that served the summarising model on a borrowed GPU machine; private for the same reason."""
    return material_root() / "remote_llm"


def wanted_sources() -> Path:
    """The lists people handed over that wanted parts were read from: a repair shop's stock, a spreadsheet."""
    return material_root() / "wanted_sources"


def inbox() -> Path:
    """Deliveries gathered by hand in a browser: a round's zip cannot be fetched again."""
    return material_root() / "inbox"


# --- private: the rest, all of it temporary ---------------------------------------------------------
def shelved() -> Path:
    """Work set aside — stopped, paused or folded into the project — kept for reference; its README
    says what each folder is. Nothing reads it."""
    return material_root() / "shelved"


def llm_cache() -> Path:
    return material_root() / "llm_cache"


def logs() -> Path:
    return material_root() / "logs"


def scratch() -> Path:
    return material_root() / "scratch"


def backups() -> Path:
    """Where a backup archive is written before it is carried off this machine."""
    return material_root() / "backups"


def old_history() -> Path:
    """The public repository's history before it was squashed into one commit, as a git bundle, with the
    release assets of that time. The only copy."""
    return backups() / "github-2026-10-10"


def guard_extra_patterns() -> Path:
    return material_root() / "guard_extra_patterns.txt"


def material_readme() -> Path:
    """What in this tree must not be lost, in the maintainer's words."""
    return material_root() / "README.md"


def deliveries() -> Path:
    """Deliveries made from a collection gathered by hand (`sei models deliver`), one folder per run,
    each in the shape `sei models ingest` takes. In transit: once ingested, the files are in the model tree."""
    return material_root() / "deliveries"


# --- the map ----------------------------------------------------------------------------------------
# name, visibility, sample arguments. `sei paths` prints this, and tests/core/test_config.py asserts
# that each kind keeps to its side: public is committed and never git-ignored, built is in the checkout
# but always ignored, private lives under the data root.
LOCATIONS: tuple[tuple[str, str, tuple], ...] = (
    ("schematics_registry", "public", ()),
    ("schematics_state", "public", ("esp",)),
    ("schematics_documents", "public", ("esp",)),
    ("schematics_pages", "public", ("esp",)),
    ("schematics_uses", "public", ("esp",)),
    ("schematics_lines", "public", ("esp",)),
    ("schematics_suspects", "public", ()),
    ("schematics_parts", "public", ()),
    ("schematics_export_manifest", "public", ()),
    ("schematics_withdrawn", "public", ()),
    ("schematics_curated", "public", ("TL072",)),
    ("schematics_overrides", "public", ()),
    ("model_sources", "public", ("onsemi",)),
    ("model_state", "public", ("onsemi",)),
    ("model_part", "public", ("bjt", "2N3904")),
    ("model_changes", "public", ()),
    ("model_licence", "public", ("onsemi",)),
    ("model_files", "public", ("germaniumbjts",)),
    ("model_wanted", "public", ()),
    ("model_non_native", "public", ()),
    ("datasheets_table", "public", ()),
    ("datasheets_registry", "public", ()),
    ("datasheet_links", "public", ("frank_pocnet",)),
    ("datasheet_documents", "public", ("onsemi_docs",)),
    ("datasheet_covers", "public", ("onsemi_docs",)),
    ("datasheet_catalogue", "public", ("diotec_products",)),
    ("datasheet_pages", "public", ("archive_databooks",)),
    ("datasheets_state", "public", ("ti_products",)),
    ("datasheet_polarity", "public", ()),
    ("datasheet_values_index", "public", ()),
    ("datasheet_values", "public", ("2N3904_onsemi",)),
    ("datasheet_reference", "public", ()),
    ("datasheet_figures", "public", ("2N3904_onsemi",)),
    ("datasheet_figure_reference", "public", ()),
    ("distributors_registry", "public", ()),
    ("distributors_table", "public", ("tme",)),
    ("distributors_files", "public", ("tme",)),
    ("distributors_state", "public", ("tme",)),
    ("sellers_registry", "public", ()),
    ("sellers_found", "public", ()),
    ("verification", "public", ("bjt", "2N3904")),
    ("verification_state", "public", ()),
    ("bench_measurements", "public", ()),
    ("bench_drawings", "public", ()),
    ("character", "built", ("0123456789abcdef0123456789abcdef01234567",)),
    ("character_state", "public", ()),
    ("character_release", "public", ()),
    ("known_parts", "public", ()),
    ("wanted_parts", "public", ()),
    ("rejected_tokens", "public", ()),
    ("part_families", "public", ()),
    ("documented_families", "public", ()),
    ("part_relations", "public", ()),
    ("part_references", "public", ()),
    ("naming_schemes", "public", ("pro-electron",)),
    ("part_makers", "public", ()),
    ("parts_census", "public", ()),
    ("parts_benchmark", "public", ()),
    ("parts_verdicts", "public", ()),
    ("census_registry", "public", ()),
    ("census_state", "public", ("frank_pocnet",)),
    ("datasets_registry", "public", ()),
    ("dataset_table", "public", ("part_repos",)),
    ("docs_dir", "public", ()),
    ("status_md", "public", ()),
    ("web_dir", "public", ()),
    ("web_data", "built", ()),
    ("web_crops", "built", ()),
    ("web_sealed", "built", ()),
    ("web_symbol_drawings", "built", ()),
    ("web_dist", "built", ()),
    ("tests_fixtures", "public", ()),
    ("ocr_root", "private", ()),
    ("ocr_map", "private", ()),
    ("ocr_superseded", "private", ("audiocircuit",)),
    ("linkchecks", "private", ()),
    ("summarise_preview", "private", ()),
    ("census_cache", "private", ("frank_pocnet",)),
    ("datasheets_cache", "private", ("ti_products",)),
    ("datasheets_text", "private", ("onsemi_docs",)),
    ("distributor_cache", "private", ("tme",)),
    ("index_db", "private", ()),
    ("page_sizes", "private", ()),
    ("downloads", "private", ("esp",)),
    ("download_manifest", "private", ("esp",)),
    ("source_list", "private", ("diyaudio",)),
    ("toragi_index", "private", ()),
    ("toragi_reports", "private", ()),
    ("spice_models_root", "private", ()),
    ("spice_source", "private", ("onsemi",)),
    ("spice_source_doc", "private", ("onsemi",)),
    ("spice_source_manifest", "private", ("onsemi",)),
    ("spice_curated", "private", ()),
    ("spice_model_dir", "private", ("bjt", "2N3904")),
    ("spice_part_json", "private", ("bjt", "2N3904")),
    ("spice_definitions", "private", ()),
    ("spice_symbols", "private", ()),
    ("spice_matches", "private", ()),
    ("spice_found", "private", ()),
    ("spice_recipe_locations", "private", ()),
    ("datasheets", "private", ()),
    ("datasheet_store", "private", ()),
    ("simulators", "private", ()),
    ("simulator_vendor", "private", ()),
    ("datasheet_lab", "private", ()),
    ("datasheet_experiments", "private", ()),
    ("ocr_home", "private", ()),
    ("remote_ocr", "private", ()),
    ("remote_llm", "private", ()),
    ("wanted_sources", "private", ()),
    ("inbox", "private", ()),
    ("character_runs", "private", ("qspice",)),
    ("character_pack", "private", ("character-m-11.tar.gz",)),
    ("sim_bench", "public", ()),
    ("shelved", "private", ()),
    ("llm_cache", "private", ()),
    ("logs", "private", ()),
    ("scratch", "private", ()),
    ("backups", "private", ()),
    ("old_history", "private", ()),
    ("guard_extra_patterns", "private", ()),
    ("material_readme", "private", ()),
    ("deliveries", "private", ()),
)


def location(name: str) -> Path:
    """One location by its name, for a caller that cannot import this module (`sei paths --get`, which
    the Makefile asks). Only the two private roots and locations that take no argument are answered."""
    if name in ("material_root", "spice_models_root"):
        return globals()[name]()
    for known, _visibility, args in LOCATIONS:
        if known == name and not args:
            return globals()[name]()
    raise KeyError(name)


def describe() -> list[tuple[str, str, Path, bool]]:
    """(name, visibility, resolved path, exists) for every location, for `sei paths`."""
    out = []
    for name, visibility, args in LOCATIONS:
        path = globals()[name](*args)
        out.append((name, visibility, path, path.exists()))
    return out
