"""Pack the private trees into one archive to carry off this machine.

    sei backup                 what cannot be made again
    sei backup --level full    + what can be fetched or rebuilt again, at a cost
    sei backup --level all     + the retired repositories and code kept for reference

The archive holds files at the paths they occupy inside the checkout, carries its own `MANIFEST.csv` of
checksums and its own `restore.py`, so a download years from now needs nothing from this repository to
be put back.

**Bundling matters more than compression.** The OCR is gzipped page file by page file, so anything
already compressed is stored as it is and only the rest is deflated. What the archive is for is turning
hundreds of thousands of files into one, which is the difference between a copy that finishes and one
that does not.

`essential` is what cannot be made again: the OCR, whose PDFs are gone; the index database, because
`ingest` adds documents to it but cannot recreate the figure-to-page links the old crawler recorded; the
vendor model text and its curation, since several vendors block this server; the simulator installers,
whose makers serve only their latest release; the URL lists and manifests; what people handed over; the
summariser's answers, which cost GPU hours; the scripts that ran on the borrowed GPU machine; and the
repository's history from before it was squashed.

`full` adds what has a URL or a recipe and costs time or a site's patience to get again. What is never
packed is what the steps here write again from the rest: the model catalogue and its matches, the logs,
the website's build.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from datetime import date
from pathlib import Path

from spicy_electronics_index.core.config import (
    REPO_ROOT,
    backups,
    census_cache,
    datasheet_experiments,
    datasheet_lab,
    datasheets,
    datasheets_cache,
    datasheets_text,
    download_manifest,
    downloads,
    guard_extra_patterns,
    inbox,
    index_db,
    legacy,
    llm_cache,
    material_readme,
    material_root,
    ocr_root,
    old_history,
    page_sizes,
    remote_llm,
    remote_ocr,
    scratch,
    simulator_vendor,
    simulators,
    source_list,
    spice_models_root,
    spice_symbols,
    staging,
    toragi_index,
    wanted_sources,
)

LEVELS = ("essential", "full", "all")
CHUNK = 1 << 20
RESTORE_SCRIPT = REPO_ROOT / "scripts" / "restore_private.py"
# Compressing these again costs time and gains nothing, so they go in as they are.
ALREADY_COMPRESSED = {".gz", ".zip", ".7z", ".rar", ".xz", ".bz2", ".tgz", ".png", ".jpg", ".jpeg",
                      ".webp", ".pdf", ".djvu", ".msi", ".exe"}


def contents(level: str) -> list[tuple[Path, str]]:
    """Every tree or file to pack at this level, with why it is worth carrying."""
    out: list[tuple[Path, str]] = [
        (ocr_root(), "irreplaceable: the PDFs are gone and the image that read them was deleted"),
        (page_sizes(), "page geometry frozen before the PDFs went; the zoom links depend on it"),
        (index_db(), "the index: `ingest` cannot recreate the figure-to-page links the old crawler recorded"),
        (spice_models_root(), "the vendor model text and its curation; several vendors block this server"),
        (source_list("x").parent, "URL lists for sources that cannot be crawled again"),
        (download_manifest("x").parent, "what each schematic source downloaded"),
        (guard_extra_patterns(), "the local patterns the guard checks against"),
        (material_readme(), "what in this tree must not be lost"),
        (simulator_vendor(), "the simulator installers the images are pinned to; LTspice's and QSPICE's "
                             "makers serve only their latest release"),
        (old_history(), "the repository's history before it was squashed, with its release assets: the only copy"),
        (llm_cache(), "the summariser's answers, which cost GPU hours"),
        (toragi_index(), "the publisher's article index, fetched by hand"),
        (wanted_sources(), "the lists wanted parts were read from, as they were handed over"),
        (inbox(), "deliveries gathered by hand, which cannot be fetched again"),
        (remote_ocr(), "how the OCR ran on the borrowed GPU machine"),
        (remote_llm(), "how the summariser ran there"),
    ]
    if level in ("full", "all"):
        out += [
            (downloads("x").parent, "downloads not read yet; each has its URL and checksum in a ledger"),
            (datasheets(), "manufacturer data sheets, still needed by the simulation phase"),
            (datasheets_text("x").parent, "the text read out of data sheets and databooks"),
            (datasheets_cache("x").parent, "the catalogue pages the data-sheet register was read from"),
            (census_cache("x").parent, "the index pages the part census was read from: small, and "
                                       "re-reading them costs a volunteer's site half an hour of crawling"),
            (scratch(), "work in transit"),
            (datasheet_lab(), "the data-sheet reader's pages, runs and scores"),
            (datasheet_experiments(), "earlier trials at reading data sheets"),
            (simulators(), "the simulation runs, beside the installers"),
        ]
    if level == "all":
        out += [
            (staging(), "the two retired repositories, as they were copied in to be ported"),
            (legacy(), "cancelled work, kept for reference"),
            (spice_symbols(), "the symbol catalogue; `sei models symbols` writes it again"),
        ]
    return [(p, why) for p, why in out if p.exists()]


def files_under(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*") if p.is_file() and not p.is_symlink())


def rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


def digest(path: Path) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                return h.hexdigest(), n
            h.update(b)
            n += len(b)


def readme(level: str, n_files: int, n_bytes: int) -> str:
    return f"""# Spicy Electronics Index — private data backup

Written {date.today().isoformat()} at level `{level}`: {n_files:,} files, {n_bytes / 1e9:.2f} GB.

This is the half of the project that is **not** in git: third-party material that may not be
redistributed, and the working state around it. It is a backup, not a publication — keep it private.

## Restoring

This archive is a plain zip: any tool opens it, and `restore.py` is inside it, so nothing else needs to
have been kept. Take the script out first — the zip has an index, so this reads kilobytes, not gigabytes:

    unzip -j {archive_name(level)} restore.py
    python3 restore.py {archive_name(level)} --into /path/to/spicy-electronics-index

Files go back to the paths they came from. Nothing already there is overwritten: a file that is present
and correct is skipped, and one that is present and *different* is named and left alone, because that is
either newer work or a damaged download. `--force` replaces those, `--verify-only` checks and writes
nothing.

Every file's sha256 is in `MANIFEST.csv` and is checked as it is unpacked, so a truncated download is
caught rather than restored.

## What is not in here, and why

The public half — registries, ledgers, recipes, exports — is in the git repository. Clone it; do not look
for it here.

At level `essential`, what has a URL or a recipe is left out on purpose: the downloads still to be read,
the data sheets, the caches and the work in `scratch/`, each of which can be fetched or made again. No
level holds what the steps write again from what is here: the model catalogue (`make models-index`),
its matches (`make models-match models-found models-promote`), the logs and the website's build.
"""


def archive_name(level: str) -> str:
    stamp = date.today().isoformat()
    return f"spicy-electronics-index-private-{stamp}.zip" if level == "essential" \
        else f"spicy-electronics-index-private-{level}-{stamp}.zip"


def build(out_dir: Path, level: str = "essential", dry: bool = False) -> dict:
    picked = contents(level)
    seen: dict[str, Path] = {}
    for root, _why in picked:
        for f in files_under(root):
            seen.setdefault(rel(f), f)          # a tree may be named twice; pack each file once
    total = sum(p.stat().st_size for p in seen.values())
    counts = {"files": len(seen), "bytes": total, "trees": len(picked), "packed": 0, "archive": ""}
    if dry:
        return counts

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / archive_name(level)
    tmp = target.with_name(target.name + ".part")
    rows: list[dict] = []
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for i, (name, path) in enumerate(sorted(seen.items()), 1):
            sha, n = digest(path)
            how = (zipfile.ZIP_STORED if path.suffix.lower() in ALREADY_COMPRESSED
                   else zipfile.ZIP_DEFLATED)
            zf.write(path, name, compress_type=how)
            rows.append({"path": name, "bytes": n, "sha256": sha})
            counts["packed"] += 1
            if i % 5000 == 0:
                print(f"  {i:,}/{len(seen):,} files …", flush=True)
        buf = ["path,bytes,sha256"]
        buf += [f'{r["path"]},{r["bytes"]},{r["sha256"]}' for r in rows]
        zf.writestr("MANIFEST.csv", "\n".join(buf) + "\n")
        zf.writestr("RESTORE.md", readme(level, counts["files"], counts["bytes"]))
        if RESTORE_SCRIPT.is_file():
            zf.write(RESTORE_SCRIPT, "restore.py")
    tmp.replace(target)
    # A copy also goes beside the archive. Not because it is needed — a zip carries a central
    # directory, so `unzip -j <archive> restore.py` pulls it out in milliseconds without reading the
    # rest — but so it can be read before deciding to download the rest.
    if RESTORE_SCRIPT.is_file():
        (out_dir / "restore.py").write_bytes(RESTORE_SCRIPT.read_bytes())
    counts["archive"] = str(target)
    counts["archive_bytes"] = target.stat().st_size
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--level", choices=LEVELS, default="essential")
    ap.add_argument("--out", help=f"where to write it (default: {backups()})")
    ap.add_argument("--dry", action="store_true", help="say what would be packed and write nothing")
    a = ap.parse_args(argv)

    if not material_root().exists():
        print("there is no private data root on this machine", file=sys.stderr)
        return 1
    print(f"level {a.level}:")
    for path, why in contents(a.level):
        if path.is_dir() or path.name in ("manifest.json", "SOURCE.md"):
            continue
        print(f"  {rel(path):44s} {why}")
    for path, why in contents(a.level):
        if path.is_dir():
            n = len(files_under(path))
            size = sum(p.stat().st_size for p in files_under(path))
            print(f"  {rel(path) + '/':44s} {size / 1e9:6.2f} GB  {n:>7,} files  {why}")

    c = build(Path(a.out) if a.out else backups(), a.level, dry=a.dry)
    if a.dry:
        print(f"\nwould pack {c['files']:,} files, {c['bytes'] / 1e9:.2f} GB")
        return 0
    saved = 1 - c["archive_bytes"] / c["bytes"] if c["bytes"] else 0
    print(f"\n{c['packed']:,} files -> {c['archive']}")
    print(f"{c['archive_bytes'] / 1e9:.2f} GB, {saved:.1%} smaller than the {c['bytes'] / 1e9:.2f} GB "
          f"on disk — most of it was already compressed, so what this buys is one file instead of "
          f"{c['packed']:,}")
    print(f"restore.py is inside the archive, so the .zip alone is enough. A copy sits beside it too,"
          f"\nin case it helps to read it before downloading the rest. To restore:\n"
          f"  unzip -j {archive_name(a.level)} restore.py\n"
          f"  python3 restore.py {archive_name(a.level)} --into /path/to/spicy-electronics-index")
    return 0


if __name__ == "__main__":
    sys.exit(main())
