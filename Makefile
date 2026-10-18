# Every step of the project, in one place. `make` on its own lists them.
#
# Most targets are thin wrappers around `sei`, the project's command (installed by `make setup`).
# Targets marked "maintainer" need the private data root; everything else works from a clean clone.

UV := uv
RUN := $(UV) run --quiet

# Where `make serve` puts the site. Every interface, so it can be opened from another machine.
WEB_HOST ?= 0.0.0.0
WEB_PORT ?= 8026

.DEFAULT_GOAL := help
.PHONY: schematics-dump-index schematics-restore-index models-deliver vlm-image vlm-models vlm-serve vlm-stop sheets-pages sheets-extract sheets-evaluate sim-vendor sim-qspice-capture sim-images datasheets-register distributors-tme datasheets-links datasheets-harvest datasheets-catalogue datasheets-databooks datasheets-survey datasheets-rows datasheets-figures datasheets-crops crops-publish symbol-drawings symbol-drawings-publish models-seal sealed-publish web-deploy ocr-image help setup test test-web lint guard check status status-write paths toragi-report models-index models-ingest models-missing models-recover models-fetch models-verify models-reconcile models-match models-found models-promote models-cards models-claims models-kinship bench-methods bench-character bench-character-publish bench-character-release bench-character-fetch bench-drawings bench-drawings-all circuitikz-image bench-preview bench-deck bench-read datasets-repos schematics-summarise schematics-summarise-bg schematics-preview schematics-export schematics-deliver backup clean web web-data web-deps serve

help:  ## show this list
	@echo "Spicy Electronics Index — make <target>"
	@echo
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) \
	  | awk -F':.*?## ' '{printf "  \033[1m%-16s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "  Targets marked (maintainer) need the private data root; the rest work from a clean clone."

# --- setting up ---------------------------------------------------------------------------------
setup:  ## install dependencies and enable the pre-commit guard
	$(UV) sync
	git config core.hooksPath .githooks
	@echo "ready — try 'make status'"

# --- checking your work -------------------------------------------------------------------------
test:  ## run the test suite
	$(RUN) pytest -q

test-web:  ## run the website's tests (the other half of the link builder)
	@test -d web/node_modules || { echo "skipping: run 'make web-deps' first"; exit 0; }
	cd web && npx vitest run

lint:  ## check code style
	$(RUN) ruff check src scripts tests

guard:  ## refuse anything that must not be published (what CI runs)
	python3 scripts/licence_guard.py --all

check: guard lint test test-web  ## guard + lint + tests, in that order

# --- looking at the project ---------------------------------------------------------------------
status:  ## what has been processed and what comes next, per source
	$(RUN) sei status

status-write:  ## regenerate STATUS.md from the ledgers
	$(RUN) sei status --write

paths:  ## where everything is, and which side of the public/private line
	$(RUN) sei paths

# --- SPICE models ------------------------------------------------------------------------------
models-index:  ## (maintainer) find every definition in the model sources, and stamp the ledgers
	$(RUN) sei models index --stats

models-ingest:  ## (maintainer) take in a delivery gathered by hand, a zip or a folder; FROM=path [DRY=1]
	$(RUN) sei models ingest $(FROM) $(if $(DRY),--dry,)

models-deliver:  ## (maintainer) deliveries for ingest from a collection gathered in a browser; COLLECTION=folder [INTO=dir] [SOURCE='a b'] [CITED=1] [DRY=1]
	$(RUN) sei models deliver $(COLLECTION) $(if $(INTO),--into $(INTO),) $(foreach s,$(SOURCE),--source $(s)) $(if $(CITED),--cited,) $(if $(DRY),--dry,)

models-missing:  ## (maintainer) what the catalogue recorded that the sources no longer hold
	$(RUN) sei models index --missing

models-recover:  ## (maintainer) fetch those files again, checking each against the checksum we had
	$(RUN) sei models recover

models-fetch:  ## (maintainer) download one URL into a model source; SOURCE=id URL=… [NAME=file] [NOTE='…'] [CURL=1] [FORCE=1]
	$(RUN) sei models fetch $(SOURCE) --url '$(URL)' $(if $(NAME),--name '$(NAME)') $(if $(NOTE),--note '$(NOTE)') $(if $(CURL),--curl) $(if $(FORCE),--force)

models-verify:  ## (maintainer) check the tree still holds every model file, byte for byte
	$(RUN) sei models verify

models-reconcile:  ## (maintainer) which downloads the definitions came from; WRITE=1 records it [SOURCE='a b']
	$(RUN) sei models reconcile $(foreach s,$(SOURCE),--source $(s)) $(if $(WRITE),--write,)

models-match:  ## (maintainer) find, for every wanted part, each definition that could be its model
	$(RUN) sei models match

models-found:  ## (maintainer) group those matches into distinct models, with where each copy can be had
	$(RUN) sei models found

models-symbols:  ## (maintainer) read every .asy the model sources ship, so promote links each model's own symbol
	$(RUN) sei models symbols

models-named:  ## (maintainer) the distinct codes published under NAME, as lines of non_native.yaml [SOURCE=]
	$(RUN) sei models named "$(NAME)" $(if $(SOURCE),--source $(SOURCE),)

models-promote:  ## (maintainer) write the public recipe for every curated part into data/models/parts/
	$(RUN) sei models promote

models-cards:  ## (maintainer) what each recipe model's card lacks, into data/verification/ (after promote)
	$(RUN) sei models cards $(if $(FORCE),--force)

models-claims:  ## (maintainer) what each recipe model's author declares, into data/verification/ (after promote)
	$(RUN) sei models claims

models-kinship:  ## (maintainer) how each recipe model's card relates to the others (same physics, derived, template), into data/verification/
	$(RUN) sei models kinship

bench-methods:  ## check the measurement catalogue (data/bench/measurements.yaml) and rewrite its copy in the docs
	$(RUN) sei bench methods --write

bench-character:  ## (maintainer) characterise every recipe transistor model in one image; [ENGINE=qspice] [KIND=bjt] [PART=2N3904] [HASH=prefix] [WORKERS=] [PACK=10] [LIMIT=] [FORCE=1]
	$(RUN) sei bench character --engine $(or $(ENGINE),qspice) --pack $(or $(PACK),10) $(foreach k,$(KIND),--kind $(k)) $(foreach p,$(PART),--part $(p)) $(foreach h,$(HASH),--hash $(h)) $(if $(WORKERS),--workers $(WORKERS)) $(if $(LIMIT),--limit $(LIMIT)) $(if $(FORCE),--force)

bench-character-publish:  ## (maintainer) publish the characterisation per model hash into data/verification/models/
	$(RUN) sei bench character-publish

bench-character-release:  ## (maintainer) upload the records as this catalogue version's release asset; commit the manifest after
	$(RUN) sei bench character-release

bench-character-fetch:  ## download and unpack the released characterisation records (the site build needs them)
	$(RUN) sei bench character-fetch

bench-drawings:  ## (maintainer) typeset one bench circuit (LaTeX + circuitikz) into data/bench/drawings/; NAME=bjt-tracer (image: make circuitikz-image)
	docker/circuitikz/draw.sh $(NAME)

bench-drawings-all:  ## (maintainer) regenerate the .tex of every bench drawing from docker/circuitikz/benches.py and typeset them all
	python3 docker/circuitikz/benches.py
	for f in docker/circuitikz/drawings/*.tex; do docker/circuitikz/draw.sh $$(basename $$f .tex) || exit 1; done

circuitikz-image:  ## build the TeX Live image the drawings are typeset with
	docker build -t spicy-electronics-index-circuitikz docker/circuitikz

bench-preview:  ## (maintainer) the whole FET and op-amp battery on ngspice, one model per part, as a report; MODELS=<dir> OUT=<dir> [REPORT=docs/bench-preview-2026-10.md]
	python3 docker/sim/preview/bench_preview.py $(MODELS) $(OUT) && python3 docker/sim/preview/bench_report.py $(OUT)/results.json $(or $(REPORT),docs/bench-preview-2026-10.md) $(MODELS)

bench-deck:  ## regenerate the deck behind a published number from your own card; ID=bjt-ft CARD=model.lib NAME=2N3904 [ENGINE=ngspice] [HASH=] [OUT=.]
	$(RUN) sei bench deck $(ID) --card $(CARD) --name $(NAME) --engine $(or $(ENGINE),ngspice) --out $(or $(OUT),.) $(if $(HASH),--hash $(HASH))

bench-read:  ## apply the bench's extraction to a waveform you produced; RAW=dc.raw ID=bjt-hfe-ic DECK=dc [ENGINE=ngspice] [HASH=]
	$(RUN) sei bench read $(RAW) --measurement $(ID) --deck $(DECK) --engine $(or $(ENGINE),ngspice) $(if $(HASH),--hash $(HASH))

# --- simulators -------------------------------------------------------------------------------
# QSPICE (the default engine), ngspice (the open cross-check) and LTspice (the compatibility check), in
# images whose every input is pinned; see docker/sim/README.md.
# The vendor store holds the installers, which may not be redistributed: it is private, like the images.
SIM_VENDOR ?= $(shell $(RUN) sei paths --get simulator_vendor)
SIM_BUILD = docker build --build-context vendor=$(SIM_VENDOR) --build-arg UID=$$(id -u) --build-arg GID=$$(id -g)
ENGINES ?= qspice ngspice ltspice

sim-vendor:  ## (maintainer) fetch the simulators' installers into the private store and check their sha256
	sh docker/sim/vendor.sh $(SIM_VENDOR)

sim-qspice-capture:  ## (maintainer, one-off) install QSPICE under Wine and pack it — this accepts Qorvo's licence
	$(SIM_BUILD) --target qspice-installer -t spicy-electronics-index-qspice-installer docker/sim
	sh docker/sim/qspice_capture.sh $(SIM_VENDOR)

sim-images:  ## (maintainer) build the simulator images from the pinned inputs; [ENGINES='ngspice ltspice']
	for e in $(ENGINES); do $(SIM_BUILD) --target $$e -t spicy-electronics-index-$$e docker/sim || exit 1; done

# --- data sheets (experiments) -------------------------------------------------------------------
# A vision-language model on one GPU reads the characteristics tables of manufacturer data sheets; the
# rows are scored against a hand-read reference and used to hold SPICE models against the sheet. See
# docker/datasheets/README.md. VLM_MODELS: the folder with the weights (outside the repository).
DATASHEET_PDFS ?= $(shell $(RUN) sei paths --get datasheet_store)
DATASHEET_LAB ?= $(shell $(RUN) sei paths --get datasheet_lab)
GOLDEN ?= docker/datasheets/golden.yaml
VLM_PORT ?= 8090
VLM_GPU ?= 1

vlm-image:  ## (maintainer) build llama.cpp's server for CUDA 12.2 (lola's driver) — docker/vlm/README.md
	docker build -t spicy-electronics-index-vlm docker/vlm

vlm-models:  ## (maintainer) fetch Qwen3.8-27B + its vision projector, sha256-checked; VLM_MODELS=dir
	@test -n "$(VLM_MODELS)" || { echo "give VLM_MODELS=/path/to/models"; exit 1; }
	sh docker/vlm/fetch_qwen38_vl.sh $(VLM_MODELS)

vlm-serve:  ## (maintainer) serve the model on VLM_GPU=1 at 127.0.0.1:$(VLM_PORT); VLM_MODELS=dir
	@test -n "$(VLM_MODELS)" || { echo "give VLM_MODELS=/path/to/models"; exit 1; }
	docker rm -f vlm-qwen >/dev/null 2>&1 || true
	docker run -d --name vlm-qwen --gpus '"device=$(VLM_GPU)"' -p 127.0.0.1:$(VLM_PORT):8090 \
	  -v $(VLM_MODELS):/models:ro spicy-electronics-index-vlm -m /models/Qwen3.8-27B-UD-Q4_K_M.gguf \
	  --mmproj /models/mmproj-F16.gguf -ngl 99 -fa on -c 32768 -np 2 --jinja --host 0.0.0.0 --port 8090

vlm-stop:  ## (maintainer) stop the model server and free its GPU
	docker rm -f vlm-qwen

sheets-pages:  ## (maintainer) render the reference pages to PNG (150 dpi)
	$(RUN) python docker/datasheets/render.py --golden $(GOLDEN) --pdfs $(DATASHEET_PDFS) --out $(DATASHEET_LAB)/pages

sheets-extract:  ## (maintainer) have the model read the reference pages; METHOD=image|text|image+text [NAME=run]
	$(RUN) python docker/datasheets/extract.py --method $(or $(METHOD),image) --server http://127.0.0.1:$(VLM_PORT) \
	  --golden $(GOLDEN) --pdfs $(DATASHEET_PDFS) --pages $(DATASHEET_LAB)/pages \
	  --out $(DATASHEET_LAB)/runs/$(or $(NAME),$(or $(METHOD),image))

sheets-evaluate:  ## (maintainer) score extraction runs against the reference; RUNS='dir dir'
	$(RUN) python docker/datasheets/evaluate.py --golden $(GOLDEN) --pdfs $(DATASHEET_PDFS) --per-doc $(RUNS)

# --- research datasets -------------------------------------------------------------------------
datasets-repos:  ## (maintainer) read stars, forks and watchers for every open-source project (needs `gh`)
	$(RUN) sei datasets repos

schematics-download:  ## (maintainer) fetch sources whose URLs are already listed; SOURCE='a b' [LIMIT=n]
	@test -n "$(SOURCE)" || { echo "give the source: make schematics-download SOURCE=audiocircuit"; exit 1; }
	$(RUN) sei schematics download $(foreach s,$(SOURCE),--source $(s)) $(if $(LIMIT),--limit $(LIMIT),)

schematics-download-bg:  ## (maintainer) the same, detached under a lock with a log — for the long ones
	@test -n "$(SOURCE)" || { echo "give the source: make schematics-download-bg SOURCE='tagboard dirtbox'"; exit 1; }
	$(RUN) sei schematics download $(foreach s,$(SOURCE),--source $(s)) $(if $(LIMIT),--limit $(LIMIT),) --detach

schematics-list:  ## (maintainer) gather a source's file URLs again from the site's listing; SOURCE='a b' [DRY=1]
	uv run sei schematics list $(foreach s,$(SOURCE),--source $(s)) $(if $(LIMIT),--limit $(LIMIT)) $(if $(DRY),--dry)

explain:  ## why a part gives nothing — the extractor, or no document that has it; PART='6V6 TTC004B'
	uv run sei parts explain $(PART)

parts-benchmark:  ## score today's extractor against the labelled pages; BUILD=1 labels more (spends money)
	uv run sei parts benchmark $(if $(BUILD),--build) $(if $(PER_SOURCE),--per-source $(PER_SOURCE)) $(if $(BUDGET),--budget $(BUDGET))

parts-judge:  ## decide which census names mean a component here; COLLECT=1 then ASK=1 (ASK spends money)
	uv run sei parts judge $(if $(COLLECT),--collect) $(if $(ASK),--ask) $(if $(BUDGET),--budget $(BUDGET))

parts-census:  ## (maintainer) read the lists that say which part numbers exist; [SOURCE='a b'] [READ=1]
	uv run sei parts census $(foreach s,$(SOURCE),--source $(s)) $(if $(READ),--read)

datasheets-register:  ## (maintainer) what each maker's catalogue says about the indexed parts; [SOURCE=ti_products] [LIMIT=N] [REREAD=1]
	uv run sei datasheets register $(foreach s,$(SOURCE),--source $(s)) $(if $(LIMIT),--limit $(LIMIT)) $(if $(REREAD),--reread)

distributors-tme:  ## (maintainer) what TME sells of the indexed parts: order numbers, status, stock, prices; [PART=TL072] [TOP=100] [LIMIT=N] [MAXAGE=30] [REFRESH=1] [REREAD=1]
	uv run sei distributors tme $(foreach p,$(PART),--part $(p)) $(if $(TOP),--top-per-kind $(TOP)) $(if $(LIMIT),--limit $(LIMIT)) $(if $(MAXAGE),--max-age $(MAXAGE)) $(if $(REFRESH),--refresh) $(if $(REREAD),--reread)

datasheets-polarity:  ## (maintainer) check the pages a search found for NPN/PNP, N/P-channel; FILES='found_*.jsonl'
	uv run --extra ocr sei datasheets polarity $(FILES)

datasheets-links:  ## (maintainer) every data sheet an archive lists for each part, from its cached index; [SOURCE=frank_pocnet]
	uv run sei datasheets links $(foreach s,$(SOURCE),--source $(s))

datasheets-harvest:  ## (maintainer) read the data sheets a maker's sitemap lists, to learn which parts each covers; [SOURCE=onsemi_docs] [LIMIT=N] [LIST=1]
	uv run --extra ocr sei datasheets harvest $(foreach s,$(SOURCE),--source $(s)) $(if $(LIMIT),--limit $(LIMIT)) $(if $(LIST),--list-only)

datasheets-catalogue:  ## (maintainer) read a maker's whole product list: each known part, its status and its sheet; [SOURCE=diotec_products] [REFRESH=1]
	uv run sei datasheets catalogue $(foreach s,$(SOURCE),--source $(s)) $(if $(REFRESH),--refresh)

datasheets-databooks:  ## (maintainer) the pages of old databooks on archive.org that head a known part; [LIMIT=N] [LIST=1] [REREAD=1]
	uv run sei datasheets databooks $(if $(LIMIT),--limit $(LIMIT)) $(if $(LIST),--list-only) $(if $(REREAD),--reread)

datasheets-survey:  ## (maintainer) what one kind's data sheets measure: every figure classified by its test, into data/datasheets/survey/; [KIND=opamp] [FETCH=1] [LIMIT=N] [REREAD=1] [MAKER='ti onsemi'] [DELIVER='op27_adi=~/Downloads/OP27.pdf']
	uv run --extra ocr sei datasheets survey --kind $(or $(KIND),opamp) $(if $(FETCH),--fetch) $(if $(LIMIT),--limit $(LIMIT)) $(if $(REREAD),--reread) $(foreach m,$(MAKER),--maker $(m)) $(foreach d,$(DELIVER),--deliver $(d))

datasheets-rows:  ## (maintainer) publish the reference sheets' rows, each located on its page, into data/datasheets/values/
	$(RUN) sei datasheets rows

datasheets-figures:  ## (maintainer) publish the reference sheets' figures — box on the page, axes, series — into data/datasheets/figures/
	$(RUN) sei datasheets figures

datasheets-crops:  ## (maintainer) crop each published row and figure from its PDF into web/public/data/crops (never committed)
	$(RUN) sei datasheets crops

symbol-drawings:  ## (maintainer) draw every symbol a recipe links as SVG into web/public/data/symbol-drawings (never committed)
	$(RUN) sei web symbol-drawings

symbol-drawings-publish:  ## (maintainer) upload the symbol drawings as the release asset the Pages workflow unpacks (CLAUDE.md rule 1)
	@test -d web/public/data/symbol-drawings || { echo "no drawings: make symbol-drawings first"; exit 1; }
	tar -cf "$${TMPDIR:-/tmp}/symbol-drawings.tar" -C web/public/data symbol-drawings
	gh release view symbol-drawings >/dev/null 2>&1 || gh release create symbol-drawings --title "Symbol drawings" \
	  --notes "Drawings of the LTspice symbols the site links, made from their publishers' .asy files (CLAUDE.md rule 1). Deleting this asset withdraws them."
	gh release upload symbol-drawings "$${TMPDIR:-/tmp}/symbol-drawings.tar" --clobber

crops-publish:  ## (maintainer) upload the crops as the release asset the Pages workflow unpacks (CLAUDE.md rule 1)
	@test -d web/public/data/crops || { echo "no crops: make datasheets-crops first"; exit 1; }
	tar -cf "$${TMPDIR:-/tmp}/crops.tar" -C web/public/data crops
	gh release view datasheet-crops >/dev/null 2>&1 || gh release create datasheet-crops --title "Data-sheet crops" \
	  --notes "Crops of data sheets quoted on the site beside their transcription (CLAUDE.md rule 1). Deleting this asset withdraws them."
	gh release upload datasheet-crops "$${TMPDIR:-/tmp}/crops.tar" --clobber

models-seal:  ## (maintainer) the recipes' model text, encrypted under the maintainer's passphrase, into web/public/data/sealed (never committed)
	uv run --quiet --extra seal sei models seal $(if $(PART),--part $(PART))

sealed-publish:  ## (maintainer) upload the sealed model text as the release asset the Pages workflow unpacks
	@test -f web/public/data/sealed/manifest.json || { echo "nothing sealed: make models-seal first"; exit 1; }
	tar -cf "$${TMPDIR:-/tmp}/sealed.tar" -C web/public/data sealed
	gh release view sealed-models >/dev/null 2>&1 || gh release create sealed-models --title "Sealed model text" \
	  --notes "The model text the site shows its maintainer, encrypted under a passphrase nobody else holds (CLAUDE.md rule 1). Deleting this asset withdraws it."
	gh release upload sealed-models "$${TMPDIR:-/tmp}/sealed.tar" --clobber

toragi-report:  ## (maintainer) トランジスタ技術: coverage by year and by issue, from the lists and ledgers
	$(RUN) sei schematics toragi

schematics-crawl:  ## (maintainer) walk a site and take what it shows; SOURCE='a b' [MAX=n]
	@test -n "$(SOURCE)" || { echo "give the source: make schematics-crawl SOURCE=tubecad"; exit 1; }
	$(RUN) sei schematics crawl $(foreach s,$(SOURCE),--source $(s)) $(if $(MAX),--max $(MAX),)

schematics-crawl-bg:  ## (maintainer) the same, detached under a lock with a log; AFTER=<job> to queue it
	@test -n "$(SOURCE)" || { echo "give the source: make schematics-crawl-bg SOURCE=tubecad"; exit 1; }
	$(RUN) sei schematics crawl $(foreach s,$(SOURCE),--source $(s)) $(if $(MAX),--max $(MAX),) \
	  $(if $(AFTER),--after $(AFTER),) --detach

schematics-ocr:  ## (maintainer) read what is downloaded and not read yet; SOURCE='a b' [GPU=0] [SHARD=0/2] [DRY=1]
	uv run sei schematics ocr $(foreach s,$(SOURCE),--source $(s)) $(if $(GPU),--gpu $(GPU)) $(if $(SHARD),--shard $(SHARD)) $(if $(LIMIT),--limit $(LIMIT)) $(if $(DRY),--dry)

# The CUDA the image is built for has to be one this machine's driver runs; see docker/ocr.Dockerfile.
PADDLE_TAG ?= 3.2.2-gpu-cuda12.6-cudnn9.5

ocr-image:  ## (maintainer) build the OCR image; PADDLE_TAG=3.2.2-gpu-cuda11.8-cudnn8.9 for a driver older than CUDA 12.6
	docker build --build-arg PADDLE_TAG=$(PADDLE_TAG) -f docker/ocr.Dockerfile -t spicy-electronics-index-ocr .

schematics-ocr-recheck:  ## (maintainer) mark what an earlier OCR read from an illegible text layer, to read again; SOURCE='a b' [DRY=1]
	uv run sei schematics ocr --recheck $(foreach s,$(SOURCE),--source $(s)) $(if $(DRY),--dry)

MATERIAL ?= $(shell $(RUN) sei paths --get material_root)
OCR_HOME ?= $(shell $(RUN) sei paths --get ocr_home)
schematics-ocr-docker:  ## (maintainer) the same inside the CUDA image, one shard per GPU; SOURCE='a b' GPU=0 SHARD=0/2
	mkdir -p "$(OCR_HOME)"
	docker run --rm --gpus '"device=$(GPU)"' --user $$(id -u):$$(id -g) -e HOME=/ocr-home -v "$(OCR_HOME)":/ocr-home \
	  -e SEI_MATERIAL=/material -v "$(MATERIAL)":/material -v "$(PWD)":/repo spicy-electronics-index-ocr \
	  schematics ocr $(foreach s,$(SOURCE),--source $(s)) --gpu 0 $(if $(SHARD),--shard $(SHARD))

schematics-verify:  ## (maintainer) find documents lost before anything read them; REPAIR=1 fetches them back
	$(RUN) sei schematics verify $(if $(SOURCE),$(foreach s,$(SOURCE),--source $(s)),) $(if $(REPAIR),--repair,)

schematics-prune:  ## (maintainer) drop what a source's rules no longer want; [SOURCE='a b'] [DRY=1]
	$(RUN) sei schematics prune $(foreach s,$(SOURCE),--source $(s)) $(if $(DRY),--dry,)

schematics-release:  ## (maintainer) delete downloaded files whose text is already read; [SOURCE='a b'] [DRY=1]
	$(RUN) sei schematics release $(foreach s,$(SOURCE),--source $(s)) $(if $(DRY),--dry,)

schematics-deliver:  ## (maintainer) take in an archive gathered by hand as a source's downloads; SOURCE=id ARCHIVE=file [REMOVE=1]
	$(RUN) sei schematics deliver --source $(SOURCE) --archive '$(ARCHIVE)' $(if $(REMOVE),--remove-archive)

schematics-ingest:  ## (maintainer) put what has been read into the index database; [SOURCE='a b'] [LIMIT=n] [DRY=1]
	$(RUN) sei schematics ingest $(foreach s,$(SOURCE),--source $(s)) $(if $(LIMIT),--limit $(LIMIT)) $(if $(DRY),--dry)

schematics-dump-index:  ## (maintainer) write the index tables the OCR cannot give back, as CSV; TO=<folder>
	$(RUN) sei schematics dump-index $(TO)

schematics-restore-index:  ## (maintainer) build index.sqlite again from a dump and the OCR; FROM=<folder> [INTO=path] [WORKERS=n] [LIMIT=n] [NOTEXT=1]
	$(RUN) sei schematics restore-index $(FROM) $(if $(INTO),--into $(INTO)) $(if $(WORKERS),--workers $(WORKERS)) $(if $(LIMIT),--limit $(LIMIT)) $(if $(NOTEXT),--no-text)

schematics-reindex:  ## (maintainer) read the corpus again with the current extractor; [SOURCE='a b'] [WORKERS=n]
	uv run sei schematics reindex $(foreach s,$(SOURCE),--source $(s)) $(if $(WORKERS),--workers $(WORKERS)) $(if $(LIMIT),--limit $(LIMIT)) $(if $(DRY),--dry)

schematics-summarise:  ## (maintainer) one line per published use, from the model next door; SOURCE='a b' [LIMIT=n] [DRY=1]
	$(RUN) sei schematics summarise $(foreach s,$(SOURCE),--source $(s)) $(if $(LIMIT),--limit $(LIMIT),) $(if $(DRY),--dry)

schematics-summarise-bg:  ## (maintainer) the same, detached under a lock with a log - this one runs for days
	$(RUN) sei schematics summarise $(foreach s,$(SOURCE),--source $(s)) $(if $(LIMIT),--limit $(LIMIT),) --detach

schematics-preview:  ## (maintainer) what the summarise pass has written so far, with its links
	$(RUN) sei schematics summarise --preview

schematics-export:  ## (maintainer) write the schematic index into data/, where the site is built from
	$(RUN) sei schematics export

backup:  ## (maintainer) pack the private trees into one archive to carry off this machine
	$(RUN) sei backup

# --- the website -------------------------------------------------------------------------------
web-deps:  ## install the website's dependencies (once)
	cd web && npm install --no-fund --no-audit

web-data:  ## write the site's data from data/ — reads nothing private
	$(RUN) sei web build

web: web-data  ## build the site into web/dist
	cd web && npm run build

web-deploy:  ## (maintainer) publish the site: run the Pages workflow on GitHub from what is pushed, and watch it
	@git fetch --quiet origin main && test "$$(git rev-parse origin/main)" = "$$(git rev-parse main)" \
	  || { echo "main is not pushed: the workflow builds what GitHub has. git push first."; exit 1; }
	gh workflow run pages.yml && sleep 5 && gh run watch $$(gh run list --workflow=pages.yml --limit 1 --json databaseId --jq '.[0].databaseId')
	@echo "  https://electrucio.github.io/spicy-electronics-index/"

serve: web-data  ## bring the site up with live reload, at http://0.0.0.0:8026/spicy-electronics-index/
	@echo "  http://$(WEB_HOST):$(WEB_PORT)/spicy-electronics-index/"
	cd web && SEI_WEB_HOST=$(WEB_HOST) SEI_WEB_PORT=$(WEB_PORT) npm run dev

clean:  ## remove caches and build output (never touches the private data root)
	rm -rf .pytest_cache .ruff_cache web/dist web/public/data
	find src tests scripts -name __pycache__ -type d -prune -exec rm -rf {} +

