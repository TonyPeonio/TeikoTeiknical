"""Part 1: Load cell-count.csv into a normalized SQLite database.

Run with:  python load_data.py
Creates:   cell-count.db in the repository root (rebuilt from scratch every run).

Schema (each arrow is a one-to-many relationship enforced by a FOREIGN KEY):

    projects ──< subjects ──< samples ──< cell_counts

- projects:    one row per project.
- subjects:    one row per patient. Things that never change for a patient
               (condition, age, sex, treatment, response) live here, so they
               are stored once instead of once per sample.
- samples:     one row per biological sample (sample type, timepoint).
- cell_counts: one row per (sample, population) pair. Storing counts "long"
               like this, instead of one column per population, means a new
               cell population is just new rows. The schema doesn't change,
               and SQL like GROUP BY population works for any number of them.
"""

import os
import sqlite3
from typing import Never

import pandas as pd

CSV_PATH = "cell-count.csv"
DB_PATH = "cell-count.db"

# Columns in the CSV that describe the project/subject/sample.
# Every OTHER column is treated as a cell population count, so new
# populations are picked up automatically without editing this file.
METADATA_COLUMNS = [
    "project", "subject", "condition", "age", "sex", "treatment", "response",
    "sample", "sample_type", "time_from_treatment_start",
]

SCHEMA = """
CREATE TABLE projects (
    project TEXT PRIMARY KEY
);

CREATE TABLE subjects (
    subject   TEXT PRIMARY KEY,
    project   TEXT NOT NULL REFERENCES projects(project),
    condition TEXT,
    age       INTEGER,
    sex       TEXT,
    treatment TEXT,
    response  TEXT              -- 'yes' / 'no', NULL when not applicable (e.g. healthy)
);

CREATE TABLE samples (
    sample                    TEXT PRIMARY KEY,
    subject                   TEXT NOT NULL REFERENCES subjects(subject),
    sample_type               TEXT,
    time_from_treatment_start INTEGER
);

CREATE TABLE cell_counts (
    sample     TEXT NOT NULL REFERENCES samples(sample),
    population TEXT NOT NULL,
    count      INTEGER NOT NULL,
    PRIMARY KEY (sample, population)   -- a sample can't have two counts for one population
);

-- Indexes speed up the joins and the WHERE filters used in Parts 3 and 4.
-- (Primary keys are indexed automatically, so these cover the other columns.)
CREATE INDEX idx_subjects_project ON subjects(project);
CREATE INDEX idx_subjects_filters ON subjects(condition, treatment);
CREATE INDEX idx_samples_subject  ON samples(subject);
CREATE INDEX idx_samples_filters  ON samples(sample_type, time_from_treatment_start);
"""


def create_schema(connection):
    """Create all tables and indexes in an empty database."""
    connection.executescript(SCHEMA)


def build_cell_counts(df, populations):
    """Turn the wide population columns into long (sample, population, count) rows.

    One CSV row like:
        sample=s1, b_cell=10, cd8_t_cell=20, ...
    becomes one row per population:
        (s1, b_cell, 10), (s1, cd8_t_cell, 20), ...
    """
    pieces = []
    for population in populations:
        # Take the sample id and this one population's column...
        piece = df[["sample", population]].copy()
        # ...rename the count column to the generic name "count"...
        piece = piece.rename(columns={population: "count"})
        # ...and record which population these counts belong to.
        piece["population"] = population
        pieces.append(piece)

    # Stack the per-population pieces on top of each other into one long table.
    long_df: pd.DataFrame = pd.concat(pieces, ignore_index=True)
    return long_df[["sample", "population", "count"]]


def load_csv(csv_path=CSV_PATH, db_path=DB_PATH):
    """Build a fresh database at db_path from the CSV at csv_path."""
    # Delete any old database first, so running the pipeline twice gives the
    # same result instead of crashing on "table already exists".
    if os.path.exists(db_path):
        os.remove(db_path)

    # skipinitialspace + strip guard against stray spaces after commas / in headers.
    df = pd.read_csv(csv_path, skipinitialspace=True)
    df.columns = df.columns.str.strip()

    populations = [col for col in df.columns if col not in METADATA_COLUMNS]

    connection = sqlite3.connect(db_path)
    try:
        # SQLite ignores FOREIGN KEY constraints unless this is switched on
        # (it's off by default and must be set on every new connection).
        connection.execute("PRAGMA foreign_keys = ON;")
        create_schema(connection)

        # Insert parents before children, so every foreign key already has
        # a row to point at: projects -> subjects -> samples -> cell_counts.
        projects_df = df[["project"]].drop_duplicates()
        subjects_df = df[["subject", "project", "condition", "age", "sex",
                          "treatment", "response"]].drop_duplicates()
        samples_df = df[["sample", "subject", "sample_type",
                         "time_from_treatment_start"]].drop_duplicates()
        cell_counts_df = build_cell_counts(df, populations)

        # if_exists="append" inserts into the tables we created above, so
        # pandas doesn't replace them with its own (constraint-free) version.
        projects_df.to_sql("projects", connection, if_exists="append", index=False)
        subjects_df.to_sql("subjects", connection, if_exists="append", index=False)
        samples_df.to_sql("samples", connection, if_exists="append", index=False)
        cell_counts_df.to_sql("cell_counts", connection, if_exists="append", index=False)

        connection.commit()
    finally:
        # Runs even if something above raised an error, so the file isn't left locked.
        connection.close()

    print(f"Loaded {len(samples_df)} samples, {len(subjects_df)} subjects, "
          f"{len(populations)} populations into {db_path}")


# This block only runs for `python load_data.py`, not when a test does
# `import load_data`. Without it, importing the file would rebuild the
# real database as a side effect.
if __name__ == "__main__":
    load_csv()
