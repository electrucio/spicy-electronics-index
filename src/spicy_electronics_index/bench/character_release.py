"""The characterisation records travel as a release asset, not in git: one archive per catalogue version.

    sei bench character-release    # (maintainer) pack every record, upload it, write the manifest
    sei bench character-fetch      # download the archive the manifest names, check it, unpack it

A record is one model's measurements (`config.character(hash)`, about 90 KB of JSON); the whole bipolar
population is two thousand of them, and every catalogue version rewrites them all. Git would keep each
version for ever, and the site's build only needs the current one. So the records are packed into one
archive per catalogue version, `character-<version>-<sha256[:12]>.tar.gz` on the release
`character-<version>` (GitHub takes files up to 2 GiB, with no limit on a release's total size or its
downloads), and git keeps what is small and says what was published: the ledger
(`config.character_state()`) and the manifest (`config.character_release()`) with the archive's name,
size, sha256 and record count. The Pages workflow and anyone with a clone run `character-fetch` before
building the site. A later run at the same catalogue version adds its archive to the same release, named
by its own sha256, so a deploy fetches the archive the committed manifest names until the new manifest is
pushed; an earlier version's release stays as it was, so every published set of numbers can still be had.

A machine that cannot upload a release (a cloud session's GitHub access cannot create one) puts the few
records it published into the supplement (`config.character_supplement()`, tracked in git,
`sei bench character-supplement <hash>`): `character-fetch` lays them over the asset's records, so the
site shows them, and the next `character-release` packs them into the asset, after which the folder is
emptied.

The archive is reproducible: members in sorted order, with fixed times, owners and modes, and a gzip
stream without a time stamp, so packing the same records twice gives the same sha256, and a release
that changes nothing uploads nothing.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import date
from pathlib import Path

from spicy_electronics_index.bench import catalogue
from spicy_electronics_index.core.config import (
    character,
    character_pack,
    character_release,
    character_supplement,
)

REPO = "electrucio/spicy-electronics-index"


def records_root() -> Path:
    """The folder that holds the records' shards (`<hh>/<hash>.json`)."""
    return character("00" * 20).parent.parent


def record_files() -> list[Path]:
    """Every record: the shards, and the supplement's records whose hash the shards do not hold."""
    root = records_root()
    files = {p.stem: p for p in root.glob("[0-9a-f][0-9a-f]/*.json") if len(p.stem) == 40}
    for p in supplement_files():
        files.setdefault(p.stem, p)
    return [files[k] for k in sorted(files)]


def supplement_files() -> list[Path]:
    d = character_supplement()
    return sorted(p for p in d.glob("*.json") if len(p.stem) == 40) if d.exists() else []


def supplement(hashes: list[str]) -> int:
    """Copy the published records of these hashes (prefixes allowed) into the supplement, for a machine that
    cannot release: the site build reads them beside the asset's records. Returns how many were copied."""
    root = records_root()
    got = 0
    for h in hashes:
        found = [p for p in root.glob(f"{h[:2]}/{h}*.json")]
        if not found:
            raise SystemExit(f"no published record for {h}: run `sei bench character-publish` first")
        for p in found:
            dst = character_supplement(p.stem)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(p.read_bytes())
            got += 1
    return got


def pack(files: list[Path], out: Path, root: Path | None = None) -> tuple[str, int]:
    """A reproducible tar.gz of the records, named by their place under the records folder (a supplement's
    record by the shard it belongs in)."""
    root = root or records_root()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for p in files:
            data = p.read_bytes()
            info = tarfile.TarInfo(f"{p.stem[:2]}/{p.name}" if p.parent.name == "supplement" else str(p.relative_to(root)))
            info.size, info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = len(data), 0, 0o644, 0, 0, "", ""
            tar.addfile(info, io.BytesIO(data))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, compresslevel=9, mtime=0) as gz:
        gz.write(buf.getvalue())
    return hashlib.sha256(out.read_bytes()).hexdigest(), out.stat().st_size


def manifest() -> dict | None:
    p = character_release()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    if not shutil.which("gh"):
        raise SystemExit("the GitHub command `gh` is needed (https://cli.github.com), logged in or with GH_TOKEN")
    return subprocess.run(["gh", *args, "--repo", REPO], capture_output=True, text=True, check=check)


def release() -> dict:
    """Pack the records, upload the archive to this catalogue version's release, and write the manifest."""
    version = catalogue.version()
    files = record_files()
    if not files:
        raise SystemExit("no records to release: run `sei bench character-publish` first")
    tag = f"character-{version}"
    out = character_pack(f"character-{version}.tar.gz")
    sha, size = pack(files, out)
    # the archive is named by its content, so uploading a new one never changes what the committed manifest
    # names: a deploy keeps fetching the old archive until the new manifest is pushed
    asset = f"character-{version}-{sha[:12]}.tar.gz"
    out = out.replace(out.with_name(asset))
    old = manifest()
    if old and old.get("sha256") == sha and old.get("release") == tag:
        print(f"{old['asset']}: unchanged ({len(files):,} records, sha256 {sha[:12]}), nothing uploaded")
        return old
    if gh("release", "view", tag, check=False).returncode != 0:
        notes = (f"The characterisation records at catalogue {version}: one JSON file per model hash "
                 "(data/verification/models/<hh>/<hash>.json), every measurement of every engine. "
                 "See docs/model-characterisation.md; `sei bench character-fetch` unpacks them into a clone.")
        gh("release", "create", tag, "--title", f"Characterisation records, catalogue {version}", "--notes", notes)
    gh("release", "upload", tag, str(out), "--clobber")
    doc = {"catalogue": version, "release": tag, "asset": asset, "sha256": sha, "bytes": size,
           "records": len(files), "on": date.today().isoformat()}
    character_release().write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"{asset}: {len(files):,} records, {size / 1e6:.1f} MB, sha256 {sha[:12]}, uploaded to release {tag}")
    return doc


def fetch() -> int:
    """Download the archive the manifest names, check its sha256, and unpack it over the records folder."""
    doc = manifest()
    if not doc:
        print("no manifest: no characterisation has been released")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        gh("release", "download", doc["release"], "--pattern", doc["asset"], "--dir", tmp)
        got = Path(tmp) / doc["asset"]
        sha = hashlib.sha256(got.read_bytes()).hexdigest()
        if sha != doc["sha256"]:
            raise SystemExit(f"{doc['asset']}: sha256 {sha[:12]} is not the manifest's {doc['sha256'][:12]}")
        root = records_root()
        with tarfile.open(got, "r:gz") as tar:
            members = tar.getmembers()
            for m in members:
                if not m.isfile() or m.name.startswith("/") or ".." in Path(m.name).parts:
                    raise SystemExit(f"{doc['asset']}: unexpected member {m.name}")
            # the "data" filter where this Python has it (3.12, and some 3.11 builds); the checks above suffice
            if hasattr(tarfile, "data_filter"):
                tar.extractall(root, members=members, filter="data")
            else:
                tar.extractall(root, members=members)
    extra = 0
    for p in supplement_files():
        dst = character(p.stem)
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(p.read_bytes())
            extra += 1
    print(f"{doc['asset']}: {len(members):,} records unpacked into {root} (catalogue {doc['catalogue']})"
          + (f"; {extra} more from the supplement" if extra else ""))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("release", "fetch", "supplement"))
    ap.add_argument("hashes", nargs="*", help="supplement: the model hashes (or prefixes) to copy in")
    a = ap.parse_args(argv)
    if a.action == "release":
        release()
        return 0
    if a.action == "supplement":
        print(f"{supplement(a.hashes)} records copied into {character_supplement()}")
        return 0
    return fetch()


if __name__ == "__main__":
    sys.exit(main())
