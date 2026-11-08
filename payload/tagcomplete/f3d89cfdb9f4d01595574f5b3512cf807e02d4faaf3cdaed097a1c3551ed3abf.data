"""Build the optional related-tag index from explicitly supplied public CSVs.

Usage: python tools/build_related_index.py tags.csv cooccurrence.csv[.gz]
No files are downloaded, and an existing index is never overwritten.
"""
import argparse
from contextlib import closing
import csv
import gzip
import os
from pathlib import Path
import sqlite3
import tempfile


def rows(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def build(tags, pairs, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("Existing index retained; select a new output file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".related-", suffix=".sqlite3", dir=destination.parent)
    os.close(fd)
    try:
        with closing(sqlite3.connect(name)) as database:
            database.executescript("CREATE TABLE tags(tag TEXT PRIMARY KEY, category INTEGER, count REAL, alias TEXT); CREATE TABLE pairs(a TEXT, b TEXT, n REAL);")
            with closing(rows(tags)) as tag_rows:
                database.executemany("INSERT INTO tags VALUES(?,?,?,?)", ((r["tag"], int(r["category"]), float(r["count"]), r.get("alias", "")) for r in tag_rows))
            with closing(rows(pairs)) as pair_rows:
                database.executemany("INSERT INTO pairs VALUES(?,?,?)", ((r["tag_a"], r["tag_b"], float(r["count"])) for r in pair_rows))
            database.executescript("CREATE INDEX pairs_a ON pairs(a); CREATE INDEX pairs_b ON pairs(b);")
            if database.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Index integrity check failed")
            database.commit()
        # Atomic no-clobber publication. Hardlink then unlink temp keeps existing data safe.
        os.link(name, destination)
    finally:
        if os.path.exists(name):
            os.unlink(name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tags", type=Path)
    parser.add_argument("cooccurrence", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "plus_data/related.sqlite3")
    args = parser.parse_args()
    build(args.tags, args.cooccurrence, args.output)
    print(f"Created: {args.output}")
