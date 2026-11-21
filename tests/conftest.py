"""Shared test helpers.

pytest automatically loads conftest.py, so any fixture defined here can be
used by any test file just by naming it as a test function argument.
"""

import sqlite3

import pytest

import load_data

HEADER = (
    "project,subject,condition,age,sex,treatment,response,sample,sample_type,"
    "time_from_treatment_start,b_cell,cd8_t_cell,cd4_t_cell,nk_cell,monocyte"
)


@pytest.fixture
def make_db(tmp_path):
    """Return a function that builds a test database from CSV rows.

    Usage inside a test:
        conn = make_db(["prj1,sbj1,...", ...])
    """
    connections = []

    def _make_db(rows, header=HEADER):
        csv_path = tmp_path / "cells.csv"
        csv_path.write_text(header + "\n" + "\n".join(rows) + "\n")
        db_path = tmp_path / "test.db"
        load_data.load_csv(csv_path, db_path)
        conn = sqlite3.connect(db_path)
        connections.append(conn)
        return conn

    yield _make_db

    # Everything after `yield` runs once the test finishes: close connections
    # so Windows can delete the temp folder.
    for conn in connections:
        conn.close()
