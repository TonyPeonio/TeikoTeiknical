"""Tests for Part 2: relative frequency of each cell population per sample."""

import pandas as pd
import pytest

import cell_frequencies
from conftest import HEADER

# s1 counts: 10 + 20 + 30 + 40 + 50 = 150 total, easy to check by hand.
ROWS = [
    "prj1,sbj1,melanoma,50,M,miraclib,yes,s1,PBMC,0,10,20,30,40,50",
    "prj1,sbj1,melanoma,50,M,miraclib,yes,s2,PBMC,7,1,1,1,1,6",
    "prj1,sbj2,healthy,40,F,none,,s3,WB,0,5,5,5,5,5",
]

EXPECTED_COLUMNS = ["sample", "total_count", "population", "count", "percentage"]


def test_has_exactly_the_required_columns(make_db):
    conn = make_db(ROWS)

    table = cell_frequencies.get_frequency_table(conn)

    assert list(table.columns) == EXPECTED_COLUMNS


def test_one_row_per_sample_per_population(make_db):
    conn = make_db(ROWS)

    table = cell_frequencies.get_frequency_table(conn)

    assert len(table) == 3 * 5
    # No (sample, population) pair appears twice.
    assert not table.duplicated(subset=["sample", "population"]).any()


def test_matches_hand_calculation(make_db):
    conn = make_db(ROWS)

    table = cell_frequencies.get_frequency_table(conn)
    row = table[(table["sample"] == "s1") & (table["population"] == "monocyte")].iloc[0]

    assert row["total_count"] == 150
    assert row["count"] == 50
    assert row["percentage"] == pytest.approx(50 / 150 * 100)  # 33.33...


def test_percentages_sum_to_100_for_every_sample(make_db):
    conn = make_db(ROWS)

    table = cell_frequencies.get_frequency_table(conn)
    sums = table.groupby("sample")["percentage"].sum()

    for sample, total in sums.items():
        assert total == pytest.approx(100), sample


def test_new_population_is_included_automatically(make_db):
    """Scaling: adding a 6th population to the data needs no code change."""
    rows = [r + ",100" for r in ROWS]
    conn = make_db(rows, header=HEADER + ",treg")

    table = cell_frequencies.get_frequency_table(conn)

    assert "treg" in set(table["population"])
    assert len(table) == 3 * 6
    # treg is counted in the total too: s1 total is now 150 + 100.
    s1 = table[table["sample"] == "s1"]
    assert (s1["total_count"] == 250).all()


def test_save_writes_table_to_database(make_db):
    """The dashboard reads Part 2 results from the database, so they must be saved there."""
    conn = make_db(ROWS)

    cell_frequencies.save_frequency_table(conn)
    saved = pd.read_sql_query("SELECT * FROM cell_frequencies", conn)

    assert list(saved.columns) == EXPECTED_COLUMNS
    assert len(saved) == 15


def test_save_can_run_twice(make_db):
    conn = make_db(ROWS)

    cell_frequencies.save_frequency_table(conn)
    cell_frequencies.save_frequency_table(conn)
    saved = pd.read_sql_query("SELECT * FROM cell_frequencies", conn)

    assert len(saved) == 15
