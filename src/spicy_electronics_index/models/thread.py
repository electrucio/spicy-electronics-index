"""Turn a forum thread of models gathered in a browser into the delivery `sei models ingest` takes.

    sei models deliver-thread <collection> [--source diyaudio] [--into DIR] [--dry]
    make models-deliver-thread COLLECTION=<folder> [SOURCE=diyaudio] [DRY=1]

The collection is the maintainer's browser round of one forum thread; the first was diyAudio's "Vacuum
Tube SPICE Models" (thread 243950, read to 2026-10-22). It holds every attachment with the post it came in
(`attachments_manifest.csv`), and a catalogue of every distinct model in the thread, one file per model
under `modelos_spice/`, whose header says where the model was first published: the post, and the
attachment and archive member when it came in one. The catalogue counts two models as one when their SPICE
lines are the same, so each model is delivered once, from where it first appeared.

Of a forum the attachments are taken, never the conversation (CLAUDE.md rule 3):
- a model first published in an attachment the index can read (a library, a text file, a zip) comes as
  that attachment, byte for byte, at its own address. A zip is opened for the members that hold a
  definition or an LTspice symbol, and a zip of symbols posted beside a delivered model comes too, since
  a symbol is what places a model in a schematic;
- a model first published in the text of a post, or inside something the index cannot read (an LTspice
  schematic's directives, a PDF, an archive ingest cannot open), comes as its text alone: one file per
  post holding every model first published there, at the post's address. The post's words stay on the
  forum.
An archive the forum renamed (a .tar.gz posted as .zip) is left out when another attachment holds the
same files. Nothing here fetches anything, and a file the source already holds, by address or by
checksum, is left out.

The catalogue marks what it added to a model's text, and that is undone here. The one exception is the
`.ENDS` it added to a subcircuit its post never closed: that line stays, with an English comment saying
so, because one file holds all of a post's models and an open subcircuit would swallow every model
after it.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import shutil
import sys
import tarfile
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import cached_property
from pathlib import Path, PurePosixPath

from spicy_electronics_index.core.config import deliveries
from spicy_electronics_index.models.fetch import DEF, MAX_MEMBER, already_have, inspect
from spicy_electronics_index.models.ingest import held_checksums

LOG_COLUMNS = ("source_id", "pieza", "fichero", "url_descarga", "url_pagina", "fecha", "estado", "notas", "miembros")
# The catalogue's own words, in its own language: the header it puts on every model, and the marks it
# leaves where it added to the text.
RULE = re.compile(r"^\* ={10,}\s*$")
RX_ID = re.compile(r"^\* ID catalogo: (\S+).*?Subcircuito: (\S+)")
RX_FIRST = re.compile(r"^\* Primera aparicion: (#[\d,.]+) por (.+?) \((\d{4}-\d{2}-\d{2})\)")
RX_POST = re.compile(r"^\* (https?://\S+/post-(\d+))/?\s*$")
RX_ATTACHED = re.compile(r"^\* Adjunto: (.+?)(?: -> (.+?))?\s*$")
RX_THREAD = re.compile(r"/threads/[^/]*?\.?(\d+)/")
LIBRARY_HEAD = "* --- cabecera del archivo/libreria original ---"
DEPENDENCY = "* --- dependencia incluida desde la misma fuente ---"
ENDS_ADDED = "* .ENDS anadido por el catalogo (no estaba en el original)"
ENDS_SAID = "* .ENDS added on delivery: the post does not close this subcircuit"
# The index walks files for SPICE lines: a schematic keeps its directives in TEXT lines, a PDF in its
# own encoding, and neither is read.
UNREADABLE = {".asc", ".pdf"}
READABLE = {"model", "zip", "encrypted"}
SYMBOL = ".asy"


@dataclass
class Model:
    id: str
    name: str                       # the subcircuit, as the catalogue names it
    post: str                       # the post it first appeared in
    post_id: str
    number: str                     # the post's number in the thread, "#2,481"
    author: str
    day: str
    attachment: str = ""            # its file name, when it came in one
    member: str = ""                # inside an archive
    own: list[str] = field(default_factory=list)
    deps: list[list[str]] = field(default_factory=list)


@dataclass
class Attachment:
    id: str
    name: str
    path: Path
    url: str
    post: str
    post_id: str
    number: str
    author: str
    day: str

    @cached_property
    def data(self) -> bytes:
        return self.path.read_bytes()

    @cached_property
    def verdict(self) -> str:
        return inspect(self.data)[0]

    @cached_property
    def members(self) -> dict[str, bytes]:
        """A zip's members, by path; anything else has none."""
        if self.data[:2] != b"PK":
            return {}
        out = {}
        with zipfile.ZipFile(io.BytesIO(self.data)) as z:
            for n in z.namelist():
                if not n.endswith("/") and z.getinfo(n).file_size <= MAX_MEMBER:
                    out[n] = z.read(n)
        return out

    def wanted_members(self) -> list[str]:
        """The members ingest is to open: those holding a definition, and the symbols."""
        return [n for n, b in self.members.items() if n.lower().endswith(SYMBOL) or DEF.search(b)]


@dataclass
class Outcome:
    files: dict[str, bytes] = field(default_factory=dict)
    rows: list[dict] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)
    left_out: list[str] = field(default_factory=list)


# --- reading the collection ------------------------------------------------------------------------------
def published(body: list[str]) -> tuple[list[str], list[list[str]]]:
    """The model as its post had it, and the dependencies the catalogue appended from the same source."""
    own: list[str] = []
    deps: list[list[str]] = []
    current = own
    lines = iter(body)
    for s in lines:
        t = s.strip()
        if t == LIBRARY_HEAD:
            continue
        if t == DEPENDENCY:
            current = []
            deps.append(current)
        elif t == ENDS_ADDED:
            own.append(ENDS_SAID)
            own.append(next(lines, ".ENDS"))
        else:
            current.append(s)
    return trimmed(own), [trimmed(d) for d in deps if trimmed(d)]


def trimmed(block: list[str]) -> list[str]:
    while block and not block[-1].strip():
        block = block[:-1]
    return block


def read_model(path: Path) -> Model | None:
    """One catalogue file: its header, and the text below it with the catalogue's additions undone."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rules = [i for i, s in enumerate(lines) if RULE.match(s)]
    if len(rules) < 2:
        return None
    f: dict[str, str] = {}
    for s in lines[rules[0] + 1:rules[1]]:
        if m := RX_ID.match(s):
            f["id"], f["name"] = m.groups()
        elif m := RX_FIRST.match(s):
            f["number"], f["author"], f["day"] = m.groups()
        elif m := RX_POST.match(s):
            f["post"], f["post_id"] = m.groups()
        elif m := RX_ATTACHED.match(s):
            f["attachment"], f["member"] = m.group(1).strip(), (m.group(2) or "").strip()
    if not {"id", "name", "post", "number"} <= f.keys():
        return None
    own, deps = published(lines[rules[1] + 1:])
    return Model(**f, own=own, deps=deps)


def attachments(root: Path) -> list[Attachment]:
    out = []
    with open(root / "attachments_manifest.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("kind") != "file" or not (root / r["local_path"]).is_file():
                continue
            out.append(Attachment(r["attachment_id"], r["filename"], root / r["local_path"], r["attachment_url"],
                                  r["post_url"].rstrip("/"), r["post_id"], r["post_num"], r["author"],
                                  r["post_datetime"][:10]))
    return out


def names(block: list[str]) -> set[str]:
    return {m.group(2).decode("latin-1").upper() for m in DEF.finditer("\n".join(block).encode("utf-8", "replace"))}


def repacked(a: Attachment, others: list[Attachment]) -> Attachment | None:
    """Another attachment, a zip, holding every file of this archive that ingest cannot open."""
    try:
        with tarfile.open(fileobj=io.BytesIO(a.data), mode="r:*") as t:
            mine = {hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in t.getmembers() if m.isfile()}
    except (tarfile.TarError, OSError, EOFError):
        return None
    for other in others:
        if other.id == a.id or not other.members:
            continue
        theirs = {hashlib.sha256(b).hexdigest() for b in other.members.values()}
        if mine and mine <= theirs:
            return other
    return None


def safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "model"


def pattern(member: str) -> str:
    """A member's path as a shell pattern that matches it alone."""
    return re.sub(r"([*?\[])", r"[\1]", member)


# --- the delivery ------------------------------------------------------------------------------------------
def deliver(root: Path, source: str, fetched: str) -> Outcome:
    out = Outcome()
    atts = attachments(root)
    by_post = {(a.post_id, a.name): a for a in atts}
    by_name: dict[str, list[Attachment]] = defaultdict(list)
    for a in atts:
        by_name[a.name].append(a)
    models = [m for p in sorted((root / "modelos_spice").rglob("*.inc")) if (m := read_model(p))]
    out.counts["models"] = len(models)
    thread = next((t.group(1) for m in models if (t := RX_THREAD.search(m.post))), "thread")

    def found_in(m: Model) -> Attachment | None:
        if not m.attachment:
            return None
        return by_post.get((m.post_id, m.attachment)) or (by_name[m.attachment][0] if len(by_name[m.attachment]) == 1 else None)

    # First the attachments that carry a model the index can read where it lies.
    take: dict[str, Attachment] = {}
    rest: list[tuple[Model, Attachment | None]] = []
    for m in models:
        a = found_in(m)
        if a and a.verdict in READABLE and PurePosixPath(m.member or a.name).suffix.lower() not in UNREADABLE:
            take[a.id] = a
        else:
            rest.append((m, a))
    # Then what came in something it cannot read: the same files elsewhere, or the text alone.
    in_text: dict[str, list[tuple[Model, Attachment | None]]] = defaultdict(list)
    twins: dict[str, Attachment | None] = {}
    for m, a in rest:
        if a and a.verdict not in READABLE and a.id not in twins:
            twins[a.id] = repacked(a, atts)
        if a and (other := twins.get(a.id)):
            take[other.id] = other
            out.counts["models_in_a_repacked_archive"] += 1
            note = f"{a.name} ({a.number}, {a.url}): an archive ingest cannot open; the same files are {other.url}"
            if note not in out.left_out:
                out.left_out.append(note)
            continue
        if not names(m.own):
            out.counts["models_not_spice"] += 1        # a curve tracer's macro, say: no definition to index
            continue
        in_text[m.post].append((m, a))
    for items in in_text.values():
        items.sort(key=lambda ma: int(re.sub(r"\D", "", ma[0].id) or 0))
    # A zip of symbols posted beside a model that comes.
    posts = {a.post_id for a in take.values()}
    for a in atts:
        if a.id not in take and a.post_id in posts and any(n.lower().endswith(SYMBOL) for n in a.members):
            take[a.id] = a
            out.counts["symbol_archives"] += 1

    held = held_checksums(source)
    for a in sorted(take.values(), key=lambda a: int(a.id)):
        if already_have(source, a.url) or hashlib.sha256(a.data).hexdigest() in held:
            out.counts["held_already"] += 1
            continue
        rel = f"thread-{thread}/{a.post_id}/att{a.id}_{safe(a.name)}"
        out.files[rel] = a.data
        members = a.wanted_members() if a.members else []
        out.rows.append(row(source, rel, a.url, a.post, fetched, f"{a.number} by {a.author} ({a.day}): attachment {a.name}",
                            ";".join(pattern(n) for n in members)))
        out.counts["attachments"] += 1
    for post, items in sorted(in_text.items(), key=lambda kv: int(kv[1][0][0].post_id)):
        if already_have(source, post):
            out.counts["held_already"] += 1
            continue
        first = items[0][0]
        text = post_text(post, first.author, items)
        if hashlib.sha256(text).hexdigest() in held:
            out.counts["held_already"] += 1
            continue
        rel = f"thread-{thread}/{first.post_id}/{safe(first.name)}_post{first.post_id}.txt"
        out.files[rel] = text
        out.rows.append(row(source, rel, post, post, fetched,
                            f"{first.number} by {first.author} ({first.day}): " + ", ".join(m.name for m, _ in items)))
        out.counts["posts"] += 1
        out.counts["models_in_posts"] += len(items)
    return out


def post_text(post: str, author: str, items: list[tuple[Model, Attachment | None]]) -> bytes:
    """Every model first published in one post, one after another, each with the dependencies its post
    gave it that the file does not already hold."""
    out = [f"* {post} — {author}"]
    defined: set[str] = set()
    own = set().union(*(names(m.own) for m, _ in items))      # a dependency that is a model of its own here
    for m, a in items:
        if m.attachment:
            out.append(f"* from the attachment {m.attachment}" + (f", member {m.member}" if m.member else ""))
        out += m.own + [""]
        defined |= names(m.own)
        for d in m.deps:
            n = names(d)
            if n and n <= defined | own:
                continue
            out += d + [""]
            defined |= n
    return ("\n".join(out).rstrip() + "\n").encode("utf-8")


def row(source: str, rel: str, url: str, page: str, fetched: str, note: str, members: str = "") -> dict:
    return dict(source_id=source, pieza="", fichero=rel, url_descarga=url, url_pagina=page, fecha=fetched,
                estado="encontrado", notas=note, miembros=members)


def note(root: Path, source: str, out: Outcome, fetched: str) -> str:
    lines = [f"# {source} — the models of a forum thread, from the maintainer's browser round of {fetched}",
             "",
             f"Made by `sei models deliver-thread` on {date.today().isoformat()} from `{root.name}`.",
             "",
             "- **Attachments:** each one where a model of the thread was first published and the index can read "
             "it, byte for byte at its own address; zips are opened for the members holding a definition or a "
             "symbol, and a zip of symbols posted beside one of them comes too.",
             "- **Posts:** the models first published in a post's text, or in an attachment the index cannot read "
             "(an LTspice schematic, a PDF), as their text alone, one file per post at the post's address. "
             "The catalogue's header and additions are taken out; an `.ENDS` it added to a subcircuit the post "
             "never closed stays, marked.",
             "- **Counts:** " + ", ".join(f"{k} {v}" for k, v in sorted(out.counts.items())) + "."]
    if out.left_out:
        lines += ["- **Left in the collection:**"] + [f"  - {x}" for x in out.left_out]
    return "\n".join(lines) + "\n"


def write(root: Path, source: str, out: Outcome, into: Path, fetched: str) -> Path:
    home = into / f"{source}-thread"
    if home.exists():
        shutil.rmtree(home)
    for rel, data in out.files.items():
        target = home / source / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    tag = PurePosixPath(next(iter(out.files), "thread/x")).parts[0]
    with open(home / f"descargas_{tag}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(out.rows)
    (home / f"DELIVERY_{tag}.md").write_text(note(root, source, out, fetched), encoding="utf-8")
    return home


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("collection", help="the folder the round left: attachments_manifest.csv, attachments/, modelos_spice/")
    ap.add_argument("--source", default="diyaudio", help="the model source the thread belongs to (default: diyaudio)")
    ap.add_argument("--into", help="where to write the delivery (default: the private deliveries folder, dated)")
    ap.add_argument("--fetched", help="the day the round read the thread (default: the day of its attachment list)")
    ap.add_argument("--dry", action="store_true", help="count what would be delivered and write nothing")
    a = ap.parse_args(argv)
    root = Path(a.collection).expanduser()
    if not (root / "attachments_manifest.csv").is_file() or not (root / "modelos_spice").is_dir():
        print(f"{root} holds no attachments_manifest.csv and modelos_spice/", file=sys.stderr)
        return 1
    fetched = a.fetched or date.fromtimestamp((root / "attachments_manifest.csv").stat().st_mtime).isoformat()
    out = deliver(root, a.source, fetched)
    for r in out.rows:
        if any(str(root) in r[k] or "/Users/" in r[k] or "/home/" in r[k] for k in ("url_descarga", "url_pagina")):
            raise ValueError(f"a local path in the log: {r}")
    size = sum(len(b) for b in out.files.values())
    print(f"{a.source}: {len(out.files)} files, {size / 1e6:.1f} MB  "
          + ", ".join(f"{k}={v}" for k, v in sorted(out.counts.items())))
    for x in out.left_out:
        print(f"  left out: {x}")
    if not a.dry:
        into = Path(a.into).expanduser() if a.into else deliveries() / date.today().isoformat()
        home = write(root, a.source, out, into, fetched)
        print(f"-> {home}\nthen: make models-ingest FROM={home} DRY=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
