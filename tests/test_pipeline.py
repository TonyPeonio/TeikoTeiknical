"""Tests for pipeline.ensure_database: build the database only when it's missing.

The dashboard calls this on start-up so it also works where nobody ran
`make pipeline` first (e.g. a Streamlit Community Cloud deployment).
"""

import sqlite3
from contextlib import closing

import pipeline
from conftest import HEADER

ROWS = [
    f"prj1,sbj{i},melanoma,50,{'M' if i % 2 else 'F'},miraclib,{'yes' if i < 4 else 'no'},"
    f"s{i}_{day},PBMC,{day},{10 + i},{20 + day},30,40,50"
    for i in range(8) for day in (0, 7, 14)
]


def write_csv(tmp_path):
    path = tmp_path / "cells.csv"
    path.write_text(HEADER + "\n" + "\n".join(ROWS) + "\n")
    return path


def table_names(db_path):
    with closing(sqlite3.connect(db_path)) as conn:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_builds_every_table_the_dashboard_reads(tmp_path):
    db = tmp_path / "test.db"

    built = pipeline.ensure_database(write_csv(tmp_path), db)

    assert built is True
    assert {"cell_counts", "cell_frequencies", "responder_comparison"} <= table_names(db)


def test_does_not_rebuild_an_existing_database(tmp_path):
    csv = write_csv(tmp_path)
    db = tmp_path / "test.db"
    pipeline.ensure_database(csv, db)
    modified = db.stat().st_mtime_ns

    built = pipeline.ensure_database(csv, db)

    assert built is False
    assert db.stat().st_mtime_ns == modified
