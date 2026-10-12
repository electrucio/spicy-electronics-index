"""What has been processed and what comes next, per source. Generates STATUS.md from the registry and ledgers.

Reads only committed files (data/schematics/sources.yaml, data/schematics/state/*.csv), so anyone can run it.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from spicy_electronics_index.core.config import (
    distributors_registry,
    distributors_state,
    models_dir,
    schematics_dir,
    status_md,
)
from spicy_electronics_index.core.ledger import Ledger, today

# How each stage is named in the "Next" column. A stage with no entry falls back to its own name,
# so adding a stage to core.ledger never breaks this report.
STAGE_VERB = {"ocr": "OCR", "linkcheck": "link-check"}


def last_activity(led: Ledger) -> str:
    return max((r[f"{s}_at"] for r in led.rows.values() for s in led.stages if r[f"{s}_at"]), default="")


def next_action(entry: dict, led: Ledger | None) -> str:
    if entry["status"] in ("excluded", "blocked"):
        return f"{entry['status']}: {entry.get('blocked_reason', '')}".rstrip(": ")
    if entry["status"] in ("proposed", "paused"):
        return entry["status"]
    if led is None or not len(led):
        return "crawl"
    for stage in led.stages:
        n = len(led.pending(stage))
        if n:
            return f"{STAGE_VERB.get(stage, stage)} {n}"
    return "up to date"


def schematics_rows() -> list[dict]:
    registry = yaml.safe_load((schematics_dir() / "sources.yaml").read_text(encoding="utf-8")) or {}
    rows = []
    for source, entry in registry.items():
        f = schematics_dir() / "state" / f"{source}.csv"
        led = Ledger(f) if f.exists() else None
        s = led.summary() if led else {}
        rows.append(dict(source=source, kind=entry["kind"], status=entry["status"], era=entry.get("era", ""),
                         last=last_activity(led) if led else "",
                         next=next_action(entry, led), **{k: s.get(k, 0) for k in ("items", "download", "ocr", "index", "linkcheck", "skipped")}))
    return rows


def model_next(entry: dict, files: int, not_tried: int) -> str:
    """The next step for one model source, from its registry entry and what its ledger holds.

    A registry `note` is prose about the source and says nothing about what is left to do. It once
    carried only "its manifest has not been written yet", and reading every note that way reported
    finished sources as unfinished.
    """
    if entry["status"] in ("link_only", "pending_manual"):
        return "manual: link only" if entry["status"] == "link_only" else "manual download"
    if entry.get("fetch") == "installed":
        return "ships with the simulator"
    if not_tried:
        return f"fetch {not_tried} parts"
    if not files:
        return "nothing downloaded"
    return "up to date"


def model_rows() -> list[dict]:
    from spicy_electronics_index.core.ledger import MODEL_FIELDS, MODEL_STAGES, MODEL_VERSIONED
    rows = []
    for reg in sorted((models_dir() / "sources").glob("*.yaml")):
        entry = yaml.safe_load(reg.read_text(encoding="utf-8"))
        f = models_dir() / "state" / f"{reg.stem}.csv"
        led = Ledger(f, stages=MODEL_STAGES, fields=MODEL_FIELDS, versioned=MODEL_VERSIONED) if f.exists() else None
        rs = list(led.rows.values()) if led else []
        files = [r for r in rs if not r["key"].startswith("part:") and r["status"] == "downloaded"]
        lookups = [r for r in rs if r["key"].startswith("part:")]
        not_tried = sum(1 for r in lookups if r["status"] == "not_tried")
        to_index = sum(1 for r in files if not r["index_at"])
        nxt = model_next(entry, len(files), not_tried)
        rows.append(dict(source=reg.stem, status=entry["status"], fetch=entry.get("fetch", ""), files=len(files),
                         scanned=len(files) - to_index, defs=sum(int(r["n_defs"] or 0) for r in files),
                         with_defs=sum(1 for r in files if int(r["n_defs"] or 0)),
                         unavailable=sum(1 for r in lookups if r["skip_reason"]), not_tried=not_tried,
                         licence=entry.get("licence", ""), last=last_activity(led) if led else "", next=nxt))
    return rows


def render_models() -> list[str]:
    rows = model_rows()
    if not rows:
        return []
    tot = {k: sum(r[k] for r in rows) for k in ("files", "scanned", "with_defs", "defs", "unavailable", "not_tried")}
    out = [
        "## SPICE model sources",
        "",
        f"{len(rows)} sources · {tot['files']:,} files downloaded · {tot['scanned']:,} scanned by the indexer, "
        f"of which {tot['with_defs']:,} hold definitions ({tot['defs']:,} in all) · part look-ups: "
        f"{tot['unavailable']:,} not available, {tot['not_tried']:,} not tried yet",
        "",
        "Registry: `data/models/sources/<id>.yaml`. Ledgers: `data/models/state/<id>.csv`, one row per downloaded file",
        "(URL + sha256) and one per part looked up at that vendor. **Scanned** is how many the indexer has read;",
        "**With models** how many of those held any definition — the rest are symbols, documents or binary formats,",
        "and they are read every time all the same. Model files themselves are not in this repository unless the source",
        "is marked `redistributable: true`.",
        "",
        "| Source | Status | Fetch | Files | Scanned | With models | Definitions | Parts not available "
        "| Parts not tried | Licence | Last activity | Next |",
        "|---|---|---|--:|--:|--:|--:|--:|--:|---|---|---|",
    ]
    for r in sorted(rows, key=lambda r: (-r["files"], r["source"])):
        out.append(f"| {r['source']} | {r['status']} | {r['fetch']} | {r['files']:,} | {r['scanned']:,} | "
                   f"{r['with_defs']:,} | {r['defs']:,} | {r['unavailable']:,} | {r['not_tried']:,} | "
                   f"{r['licence']} | {r['last']} | {r['next']} |")
    return out + [""]


def distributor_rows() -> list[dict]:
    """Per distributor: how many parts were asked about, how many it sells something of, how many it has
    nothing for, and how many answers are older than the registry's `max_age`."""
    reg = distributors_registry()
    if not reg.exists():
        return []
    from spicy_electronics_index.distributors import tme as tme_stage
    rows = []
    for name, entry in (yaml.safe_load(reg.read_text(encoding="utf-8")) or {}).items():
        f = distributors_state(name)
        if not f.exists():   # the stage has never run (or its answers were withdrawn): nothing to report
            continue
        led = Ledger(f, stages=tme_stage.STAGES, fields=tme_stage.FIELDS, versioned=tme_stage.VERSIONED)
        rs = list(led.rows.values())
        max_age = int((entry or {}).get("max_age", 30))
        with_offers = [r for r in rs if int(r["n_exact"] or 0) + int(r["n_variant"] or 0)]
        rows.append(dict(source=name, status=(entry or {}).get("status", ""), asked=len(rs), offers=len(with_offers),
                         none=sum(1 for r in rs if r["match_at"] and r not in with_offers and not r["skip_reason"]),
                         stale=sum(1 for r in with_offers if tme_stage.stale(r["data_at"], max_age)),
                         skipped=sum(1 for r in rs if r["skip_reason"]),
                         last=last_activity(led), max_age=max_age))
    return rows


def render_distributors() -> list[str]:
    rows = distributor_rows()
    if not rows:
        return []
    out = [
        "## Distributors",
        "",
        "What each distributor sells of the indexed parts, as its API answered: order numbers, status, stock and",
        "prices, verbatim and dated. Registry: `data/distributors/sources.yaml`; tables: `data/distributors/<id>.csv`",
        "and `<id>_files.csv`; ledger: `data/distributors/state/<id>.csv`, one row per part asked about. **Stale**",
        "counts parts whose prices and stock are older than the registry's `max_age` and will be asked for again.",
        "",
        "| Distributor | Status | Parts asked | With offers | Nothing sold | Stale | Skipped | Last activity |",
        "|---|---|--:|--:|--:|--:|--:|---|",
    ]
    for r in rows:
        out.append(f"| {r['source']} | {r['status']} | {r['asked']:,} | {r['offers']:,} | {r['none']:,} | "
                   f"{r['stale']:,} | {r['skipped']:,} | {r['last']} |")
    return out + [""]


def render() -> str:
    rows = schematics_rows()
    total = {k: sum(r[k] for r in rows) for k in ("items", "download", "ocr", "index", "linkcheck", "skipped")}
    out = [
        "# Processing status",
        "",
        f"Generated by `sei status --write` on {today()} from the registries and ledgers under `data/`. Do not edit by hand.",
        "",
        "Each item (a page, figure, PDF, magazine issue or book) moves through download → OCR → index → link-check.",
        "A stage is never repeated for an item unless its input or the stage version changes; see",
        "`src/spicy_electronics_index/core/ledger.py`. **To add a site:** add it to `sources.yaml` with `status: proposed`.",
        "",
        "## Schematic and reference sources",
        "",
        f"{len(rows)} sources · {total['items']:,} items · {total['download']:,} downloaded · {total['ocr']:,} OCR'd · "
        f"{total['index']:,} indexed · {total['linkcheck']:,} link-checked · {total['skipped']:,} skipped",
        "",
        "| Source | Kind | Era | Status | Items | Downloaded | OCR'd | Indexed | Link-checked | Skipped | Last activity | Next |",
        "|---|---|---|---|--:|--:|--:|--:|--:|--:|---|---|",
    ]
    order = {"active": 0, "proposed": 1, "paused": 2, "blocked": 3, "excluded": 4}
    for r in sorted(rows, key=lambda r: (order.get(r["status"], 9), r["kind"], r["source"])):
        out.append(f"| {r['source']} | {r['kind']} | {r['era']} | {r['status']} | {r['items']:,} | {r['download']:,} | "
                   f"{r['ocr']:,} | {r['index']:,} | {r['linkcheck']:,} | {r['skipped']:,} | {r['last']} | {r['next']} |")
    modern = [r for r in rows if r["era"] == "modern"]
    out += ["",
            "OCR'd counts only items that need OCR (scans and images); HTML pages and born-digital PDFs skip that stage.",
            "",
            f"`era` marks a source as **modern** where its circuits use parts still in production. "
            f"{len(modern)} of {len(rows)} sources are marked so, holding "
            f"{sum(r['items'] for r in modern):,} of {total['items']:,} items. It is the axis a reader will "
            f"want to filter on, and the one this corpus was thinnest along: of the 18,542 part numbers "
            f"published on 2026-09-24, 291 belonged to a family newer than 1995.",
            ""]
    out += render_models()
    out += render_distributors()
    return "\n".join(out)


def write(path: Path | None = None) -> Path:
    path = Path(path) if path else status_md()
    path.write_text(render(), encoding="utf-8")
    return path
