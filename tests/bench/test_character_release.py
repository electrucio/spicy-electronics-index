"""The released archive of the characterisation records is reproducible, so a release that changes nothing
uploads nothing, and it holds the records under their shard folders, as the site build reads them."""
import os
import tarfile

from spicy_electronics_index.bench import character_release as R


def _records(root):
    files = []
    for h, text in (("ab" + "0" * 38, '{"a":1}\n'), ("cd" + "1" * 38, '{"b":2}\n')):
        p = root / h[:2] / f"{h}.json"
        p.parent.mkdir(parents=True)
        p.write_text(text, encoding="utf-8")
        files.append(p)
    return files


def test_packing_the_same_records_twice_gives_the_same_archive(tmp_path):
    files = _records(tmp_path / "models")
    sha1, size1 = R.pack(files, tmp_path / "one.tar.gz", root=tmp_path / "models")
    for f in files:                                   # other times on disk change nothing in the archive
        os.utime(f, (1, 1))
    sha2, size2 = R.pack(files, tmp_path / "two.tar.gz", root=tmp_path / "models")
    assert (sha1, size1) == (sha2, size2)
    with tarfile.open(tmp_path / "one.tar.gz") as tar:
        names = [m.name for m in tar.getmembers()]
        assert names == [f"ab/ab{'0' * 38}.json", f"cd/cd{'1' * 38}.json"]
        assert all(m.mtime == 0 and m.uid == 0 and m.uname == "" for m in tar.getmembers())


def test_a_changed_record_changes_the_archive(tmp_path):
    files = _records(tmp_path / "models")
    sha1, _ = R.pack(files, tmp_path / "one.tar.gz", root=tmp_path / "models")
    files[0].write_text('{"a":2}\n', encoding="utf-8")
    sha2, _ = R.pack(files, tmp_path / "two.tar.gz", root=tmp_path / "models")
    assert sha1 != sha2
