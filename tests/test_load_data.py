"""Tests for Part 1: loading cell-count.csv into a normalized SQLite database.

Every test builds its own tiny, hand-written CSV inside pytest's `tmp_path`
(a fresh temporary folder per test), so the tests never touch the real
cell-count.csv / cell-count.db and can't interfere with each other.
"""

import sqlite3
from contextlib import closing

import pytest

import load_data

HEADER = (
    "project,subject,condition,age,sex,treatment,response,sample,sample_type,"
    "time_from_treatment_start,b_cell,cd8_t_cell,cd4_t_cell,nk_cell,monocyte"
)

# Two subjects in one project. sbj1 has two samples (day 0 and day 7) so we
# can check that subject-level info is stored once, not once per sample.
SMALL_ROWS = [
    "prj1,sbj1,melanoma,50,M,miraclib,yes,s1,PBMC,0,10,20,30,40,50",
    "prj1,sbj1,melanoma,50,M,miraclib,yes,s2,PBMC,7,11,21,31,41,51",
    "prj1,sbj2,healthy,40,F,none,,s3,WB,0,5,5,5,5,5",
]


def write_csv(tmp_path, header, rows, name="cells.csv"):
    """Write a CSV into the temp folder and return its path."""
    path = tmp_path / name
    path.write_text(header + "\n" + "\n".join(rows) + "\n")
    return path


def count_rows(db_path, table):
    with closing(sqlite3.connect(db_path)) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_creates_expected_tables(tmp_path):
    csv = write_csv(tmp_path, HEADER, SMALL_ROWS)
    db = tmp_path / "test.db"

    load_data.load_csv(csv, db)

    with closing(sqlite3.connect(db)) as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"projects", "subjects", "samples", "cell_counts"} <= tables


def test_row_counts_match_csv(tmp_path):
    csv = write_csv(tmp_path, HEADER, SMALL_ROWS)
    db = tmp_path / "test.db"

    load_data.load_csv(csv, db)

    assert count_rows(db, "projects") == 1
    assert count_rows(db, "subjects") == 2        # sbj1 stored once
    assert count_rows(db, "samples") == 3
    assert count_rows(db, "cell_counts") == 3 * 5  # 3 samples x 5 populations


def test_cell_counts_are_stored_long(tmp_path):
    """cell_counts has one row per (sample, population) with the right count."""
    csv = write_csv(tmp_path, HEADER, SMALL_ROWS)
    db = tmp_path / "test.db"

    load_data.load_csv(csv, db)

    with closing(sqlite3.connect(db)) as conn:
        count = conn.execute(
            "SELECT count FROM cell_counts WHERE sample='s2' AND population='nk_cell'"
        ).fetchone()[0]
    assert count == 41


def test_running_twice_does_not_crash_or_duplicate(tmp_path):
    """`make pipeline` may run against an existing .db, so loading must be re-runnable."""
    csv = write_csv(tmp_path, HEADER, SMALL_ROWS)
    db = tmp_path / "test.db"

    load_data.load_csv(csv, db)
    load_data.load_csv(csv, db)

    assert count_rows(db, "samples") == 3
    assert count_rows(db, "cell_counts") == 15


def test_new_population_needs_no_schema_change(tmp_path):
    """Scaling: a 6th cell population column should just become more rows."""
    header = HEADER + ",treg"
    rows = [r + ",99" for r in SMALL_ROWS]
    csv = write_csv(tmp_path, header, rows)
    db = tmp_path / "test.db"

    load_data.load_csv(csv, db)

    with closing(sqlite3.connect(db)) as conn:
        pops = {r[0] for r in conn.execute("SELECT DISTINCT population FROM cell_counts")}
    assert "treg" in pops
    assert count_rows(db, "cell_counts") == 3 * 6


def test_many_projects_and_subjects(tmp_path):
    """Scaling: lots of projects/subjects, including ones not in the real data."""
    rows = []
    for p in range(10):
        for s in range(50):
            subject = f"sbj_{p}_{s}"
            for day in (0, 7, 14):
                rows.append(
                    f"prj{p},{subject},melanoma,60,F,miraclib,no,"
                    f"{subject}_d{day},PBMC,{day},1,2,3,4,5"
                )
    csv = write_csv(tmp_path, HEADER, rows)
    db = tmp_path / "test.db"

    load_data.load_csv(csv, db)

    assert count_rows(db, "projects") == 10
    assert count_rows(db, "subjects") == 500
    assert count_rows(db, "samples") == 1500
    assert count_rows(db, "cell_counts") == 1500 * 5


def test_foreign_keys_are_enforced(tmp_path):
    """A sample pointing at a subject that doesn't exist should be rejected."""
    csv = write_csv(tmp_path, HEADER, SMALL_ROWS)
    db = tmp_path / "test.db"
    load_data.load_csv(csv, db)

    with closing(sqlite3.connect(db)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO samples (sample, subject, sample_type, time_from_treatment_start) "
                "VALUES ('bad', 'no_such_subject', 'PBMC', 0)"
            )
