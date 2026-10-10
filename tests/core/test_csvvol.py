"""A public CSV too big for one file is written and read as volumes, and stays one file when it fits."""
from spicy_electronics_index.core import config, csvvol

FIELDS = ("doc", "page", "line")


def rows(n):
    return [(str(i), "1", f"line number {i} of a long export") for i in range(n)]


def test_a_file_that_fits_stays_one_file(tmp_path):
    path = tmp_path / "esp.csv"
    assert csvvol.write(path, FIELDS, rows(10)) == 10
    assert csvvol.volumes(path) == [path]
    assert [r["doc"] for r in csvvol.read(path)] == [str(i) for i in range(10)]


def test_a_big_one_goes_on_in_volumes_each_with_its_header(tmp_path):
    path = tmp_path / "audiocircuit.csv"
    assert csvvol.write(path, FIELDS, rows(100), max_bytes=500) == 100
    vols = csvvol.volumes(path)
    assert len(vols) > 2 and vols[1] == config.volume(path, 2) == tmp_path / "audiocircuit.2.csv"
    assert all(v.read_text().startswith("doc,page,line\n") for v in vols)
    assert [r["doc"] for r in csvvol.read(path)] == [str(i) for i in range(100)]   # every row, once, in order


def test_a_shorter_rewrite_leaves_no_stale_volume_behind(tmp_path):
    path = tmp_path / "audiocircuit.csv"
    csvvol.write(path, FIELDS, rows(100), max_bytes=500)
    csvvol.write(path, FIELDS, rows(3), max_bytes=500)
    assert csvvol.volumes(path) == [path]
    assert len(list(csvvol.read(path))) == 3


def test_nothing_to_read_when_there_is_no_file_and_a_header_when_there_are_no_rows(tmp_path):
    assert list(csvvol.read(tmp_path / "none.csv")) == []
    path = tmp_path / "empty.csv"
    assert csvvol.write(path, FIELDS, []) == 0
    assert path.read_text() == "doc,page,line\n"


def test_a_volume_is_not_a_source():
    assert csvvol.is_volume(config.volume(config.schematics_lines("audiocircuit"), 2))
    assert not csvvol.is_volume(config.schematics_lines("amz-muzique"))
