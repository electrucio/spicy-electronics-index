"""The SPICE model text, sealed for the maintainer: one encrypted file per part, opened in the browser.

    sei models seal              (maintainer) write web/public/data/sealed/ from the private tree
    sei models seal --new-passphrase   make the passphrase file, once; it is never printed
    make sealed-publish           upload them as the release asset the Pages workflow unpacks

What a vendor's licence forbids us to publish (CLAUDE.md rule 1) stays off the site for its readers: they
get the recipe and fetch the model from its source. The maintainer wants more on their own screen — the
definition itself, ready to paste into an LTspice or QSPICE directive — and the site has no server to ask.
So the text travels sealed: AES-GCM under a key derived from a passphrase that only the maintainer holds
and never shares, because sharing it would be publishing the text. The site's code is public, and so is
the fact that these files exist; what keeps them closed is the passphrase alone.

One file per part, `sealed/<part>.bin`: a 12-byte IV, then the ciphertext of the gzipped JSON
`{"v": 1, "models": {<key>: <text>}}`, with the part's name as additional data so that one part's file
cannot stand in for another's. A model's key is its identity (`hash`) when it has one, `source:name`
otherwise — the models LTspice installs, which no catalogue file holds. The IV is derived from the key and
the content, so an unchanged part seals to the same bytes and a rebuild changes only what changed; an IV
repeats only with the same plaintext, which then gives the same ciphertext. `sealed/manifest.json` carries
the key derivation's parameters and one sealed check value, so the page can tell a wrong passphrase from a
missing file.

The text of each model is the definition and what it references, dependencies first, as the source
wrote them (`paste_chain`, which is `found.closure` without what that takes in by coincidence). Where the curation fixed a model — `^`, which
LTspice reads as XOR; a PSpice tag on a `.subckt` line — the fixed text is the curated file's, and that is
the one sealed, because it is the one that runs; so is the curated copy of a model LTspice installs, for
QSPICE, which does not install it. A subcircuit closed with a library's `.ENDL`, or not closed at all, is
closed with `.ENDS`, as the bench closes it. One comment line on top says whose model it is and where it
was had.

`web/src/sealed.ts` is the other half; `tests/fixtures/sealed/` holds one part sealed with a known
passphrase, which both halves must open.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from spicy_electronics_index.core.config import (
    require,
    spice_models_root,
    spice_part_json,
    spice_recipe_locations,
    web_sealed,
)
from spicy_electronics_index.core.partfile import part_file
from spicy_electronics_index.models import found as F

VERSION = 1
# Credentials live outside the repository (rule 6), beside the API key; $SEI_SEAL_PASSPHRASE moves it.
PASSPHRASE_FILE = Path(os.environ.get("SEI_SEAL_PASSPHRASE", "~/.config/spicy-electronics-index/sealed-models-passphrase.txt")).expanduser()
# PBKDF2-HMAC-SHA256 at OWASP's 2023 figure. The salt is fixed and public: it only has to make this site's
# keys unlike anyone else's, and a fixed one keeps the key a browser remembers valid from one build to the next.
ITERATIONS = 600_000
SALT = b"spicy-electronics-index sealed models v1"
CHECK = b"spicy-electronics-index sealed models"
# A passphrase made here: 24 characters from an alphabet without look-alikes (no 0/o, 1/l/i), in groups of
# four, 120 bits. A reader types it once per browser.
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
RX_ENDS = re.compile(r"^\s*\.ends\b", re.I | re.M)
RX_ENDL = re.compile(r"^\s*\.endl\b[^\n]*", re.I | re.M)
RX_AKO_BASE = re.compile(r"^\.MODEL\s+\S+\s+AKO:\s*(\S+)")
RX_NUMBER = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)$")


# --- the cipher ---------------------------------------------------------------------------------------------
def normal(phrase: str) -> str:
    """The passphrase as both halves read it: trimmed and in one Unicode spelling (NFC)."""
    return unicodedata.normalize("NFC", phrase.strip())


def derive(phrase: str, salt: bytes = SALT, iterations: int = ITERATIONS) -> bytes:
    """The 256-bit AES key a passphrase gives, as WebCrypto's PBKDF2 gives it."""
    return hashlib.pbkdf2_hmac("sha256", normal(phrase).encode("utf-8"), salt, iterations, 32)


def _aead(key: bytes):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise SystemExit("sealing needs the cryptography package: uv sync --extra seal") from None
    return AESGCM(key)


def seal(key: bytes, aad: str, plain: bytes) -> bytes:
    """IV + AES-GCM ciphertext (with its tag) of `plain`, bound to `aad`."""
    iv_key = hmac.new(key, b"iv", hashlib.sha256).digest()
    iv = hmac.new(iv_key, aad.encode("utf-8") + b"\0" + plain, hashlib.sha256).digest()[:12]
    return iv + _aead(key).encrypt(iv, plain, aad.encode("utf-8"))


def unseal(key: bytes, aad: str, blob: bytes) -> bytes:
    return _aead(key).decrypt(blob[:12], blob[12:], aad.encode("utf-8"))


def pack(models: dict[str, str]) -> bytes:
    doc = {"v": VERSION, "models": models}
    return gzip.compress(json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
                         compresslevel=9, mtime=0)


def unpack(plain: bytes) -> dict[str, str]:
    return json.loads(gzip.decompress(plain))["models"]


def manifest(key: bytes, salt: bytes = SALT, iterations: int = ITERATIONS) -> dict:
    b64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731
    return {"v": VERSION, "kdf": {"name": "PBKDF2", "hash": "SHA-256", "iterations": iterations, "salt": b64(salt)},
            "cipher": "AES-GCM", "check": b64(seal(key, "check", CHECK))}


def passphrase(path: Path = PASSPHRASE_FILE) -> str:
    if not path.exists():
        raise SystemExit(f"no passphrase: write one in {path}, or run `sei models seal --new-passphrase`")
    phrase = normal(path.read_text(encoding="utf-8"))
    if len(phrase) < 16:
        raise SystemExit(f"the passphrase in {path} is shorter than 16 characters: anyone may try guesses offline")
    return phrase


def new_passphrase(path: Path = PASSPHRASE_FILE) -> Path:
    """Write a random passphrase, readable by its owner only; never over one that exists."""
    if path.exists():
        raise SystemExit(f"{path} exists: a new passphrase would lock every browser out; delete it first to change it")
    path.parent.mkdir(parents=True, exist_ok=True)
    phrase = "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(6))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(phrase + "\n")
    return path


# --- the text ----------------------------------------------------------------------------------------------
def closed(kind: str, body: str) -> str:
    """A subcircuit with its `.ENDS`: a library's `.ENDL` (onsemi's 2SC6144SG) ends it, and what the scan
    swept in after it is cut; one with no end at all gets one."""
    if kind != "subckt" or RX_ENDS.search(body):
        return body
    m = RX_ENDL.search(body)
    return (body[:m.start()] + ".ENDS") if m else body.rstrip() + "\n.ENDS"


def paste_chain(defs: dict, name: str) -> list:
    """What one paste must hold: the definition and what it really references, dependencies first.

    `found.closure` takes in, by coincidence, any definition whose name appears as a word in the text:
    bordodynov's standard.bjt holds a `.MODEL 2`, and every card in it with BR=2 gains it. The model's
    identity is computed over that closure and stays as it is; the paste is cut to what a simulator needs.
    A `.model` card references another only as the base of an AKO card; a subcircuit references
    definitions by name, and a bare number in it is a node or a value, never a name.
    """
    main = defs.get(name.lower())
    if main is None:
        return []
    if main[0] == "model":
        out, seen = [main], {name.lower()}
        while True:
            lines = F.code_lines(out[0][2])
            m = RX_AKO_BASE.match(lines[0]) if lines else None
            base = m.group(1).lower() if m else ""
            if not base or base in seen or base not in defs:
                return out
            seen.add(base)
            out.insert(0, defs[base])
    order, seen = [], set()

    def visit(key):
        if key in seen or key not in defs:
            return
        seen.add(key)
        code = "\n".join(line.split(";")[0] for line in defs[key][2].splitlines() if not line.lstrip().startswith("*"))
        for tok in sorted(set(re.findall(r"[A-Za-z0-9_.\-+$#]+", code))):
            t = tok.lower()
            if t != key and t in defs and not RX_NUMBER.match(t):
                visit(t)
        order.append(key)

    visit(name.lower())
    return [defs[k] for k in order]


def chain_text(chain: list) -> str:
    """A definition's closure as one paste: dependencies first, as `found.closure` orders them."""
    return "\n".join(closed(kind, body).strip("\n") for kind, _, body in chain) + "\n"


def curated_text(path: Path) -> str:
    """A curated file's definitions without the header the curation wrote on top (`* PART:` … `*`)."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if lines and lines[0].startswith("* PART:"):
        end = next((i for i, s in enumerate(lines) if s.strip() == "*"), -1)
        lines = lines[end + 1:]
    return "\n".join(lines).strip("\n") + "\n"


def heading(row: dict) -> str:
    """One comment line: the model, whose it is and where it was had. ASCII, as LTspice reads it."""
    get = row.get("get") or {}
    where = get.get("url") or (f"ships with {get['installed_with']}" if get.get("installed_with") else "origin not recorded")
    if get.get("member"):
        where += f" ({get['member']})"
    line = f"* {row['name']} from {row['source']}: {where}".replace("\u00b5", "u").replace("\u03bc", "u")
    return unicodedata.normalize("NFKD", line).encode("ascii", "ignore").decode("ascii")


def model_key(row: dict) -> str:
    """How the page names a model to find its text: the same expression as `web/src/sealed.ts`."""
    return row.get("hash") or f"{row['source']}:{row['name']}"


def curated(kind: str, part: str, files: F.Files) -> tuple[Path | None, dict, dict]:
    """The curated directory of a part, its candidates by identity and by (file, name)."""
    pj = spice_part_json(kind, part)
    if not pj.exists():
        return None, {}, {}
    from spicy_electronics_index.models.promote import curated_hash
    by_hash, by_file = {}, {}
    for c in json.loads(pj.read_text(encoding="utf-8")).get("candidates") or []:
        h = curated_hash(c, files)
        if h:
            by_hash.setdefault(h, c)
        by_file.setdefault(((c.get("provenance") or {}).get("file") or "", c.get("name", "")), c)
    return pj.parent, by_hash, by_file


def part_texts(kind: str, part: str, rows: list[dict], locs: list[dict], files: F.Files, c: Counter) -> dict[str, str]:
    """{key: paste-ready text} for every model of one recipe that can be read."""
    pdir, by_hash, by_file = curated(kind, part, files)
    out: dict[str, str] = {}
    for row, loc in zip(rows, locs):
        key = model_key(row)
        if key in out:
            continue
        cand = by_hash.get(row.get("hash") or "") or by_file.get((loc["file"], loc["name"]))
        own = loc["file"].startswith("sources/")
        text = None
        if pdir is not None and cand and cand.get("file") and ((cand.get("changes") or []) or not own):
            p = pdir / cand["file"]
            if p.exists():
                text, how = curated_text(p), "curated file"
        if text is None and own:
            try:
                chain = paste_chain(files.get(loc["file"])[0], loc["name"])
            except OSError:
                chain = []
            if chain:
                text, how = chain_text(chain), "catalogue file"
                if any(k == "subckt" and not RX_ENDS.search(b) for k, _, b in chain):
                    c["subcircuits closed with .ENDS"] += 1
        if text is None:
            c["not readable"] += 1
            continue
        c[how] += 1
        out[key] = heading(row) + "\n" + text
    return out


def build(only: str | None = None) -> Counter:
    from spicy_electronics_index.web.parts import model_recipes
    key = derive(passphrase())
    locations = json.loads(require(spice_recipe_locations(), "sealing the recipes' models").read_text(encoding="utf-8"))
    files = F.Files(require(spice_models_root(), "sealing the recipes' models"))
    recipes, _ = model_recipes()
    out_dir = web_sealed()
    out_dir.mkdir(parents=True, exist_ok=True)
    c: Counter = Counter()
    written: set[Path] = set()
    for part, doc in sorted(recipes.items()):
        if only and part != only:
            continue
        rows = doc.get("models") or []
        locs = locations.get(f"{doc.get('kind', '')}/{part}")
        if locs is None or len(locs) != len(rows) or any(
                r["name"] != x["name"] or (r.get("hash") or "") != x["hash"] for r, x in zip(rows, locs)):
            c["recipe and its locations disagree: run make models-promote"] += 1
            continue
        texts = part_texts(doc["kind"], part, rows, locs, files, c)
        if not texts:
            continue
        path = out_dir / f"{part_file(part)}.bin"
        blob = seal(key, part, pack(texts))
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != blob:
            path.write_bytes(blob)
            c["parts written"] += 1
        else:
            c["parts unchanged"] += 1
        written.add(path)
        c["models sealed"] += len(texts)
        c["bytes"] += len(blob)
    if not only:
        for p in out_dir.rglob("*.bin"):
            if p not in written:
                p.unlink()
                c["parts withdrawn"] += 1
    (out_dir / "manifest.json").write_text(json.dumps(manifest(key), indent=1) + "\n", encoding="utf-8")
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sei models seal", description=__doc__.splitlines()[0])
    ap.add_argument("--part", help="only this part")
    ap.add_argument("--new-passphrase", action="store_true", help=f"write a random passphrase to {PASSPHRASE_FILE}, once")
    args = ap.parse_args(argv)
    if args.new_passphrase:
        print(f"passphrase written to {new_passphrase()} (readable by you only; it is not printed)")
        return 0
    c = build(args.part)
    for k, v in sorted(c.items()):
        print(f"{v:>10,}  {k}")
    print(f"into {web_sealed()}; publish with `make sealed-publish`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
