"""Part 2: Relative frequency of each cell population in each sample.

Run with:  python cell_frequencies.py   (after python load_data.py)

Reads cell counts from cell-count.db, computes each population's percentage
of its sample's total cell count, prints a preview, and saves the full table
to the `cell_frequencies` table in the same database for the dashboard.
"""

import sqlite3

import pandas as pd

DB_PATH = "cell-count.db"


def get_frequency_table(connection):
    """Return one row per (sample, population) with total, count and percentage.

    Columns: sample, total_count, population, count, percentage
    """
    # cell_counts is already "long" (one row per sample + population), so
    # every population in the database is included automatically.
    counts = pd.read_sql_query(
        "SELECT sample, population, count FROM cell_counts", connection
    )

    # Total cells per sample: group the rows by sample and add up each group.
    # The result has one row per sample: (sample, total_count).
    totals = counts.groupby("sample", as_index=False)["count"].sum()
    totals = totals.rename(columns={"count": "total_count"})

    # Attach each sample's total to every one of its population rows.
    # merge works like a SQL JOIN: rows are matched on the "sample" column.
    table = pd.merge(counts, totals, on="sample")

    # Pandas does this division for every row at once (no loop needed).
    table["percentage"] = table["count"] / table["total_count"] * 100

    # Sort by sample; "stable" keeps the populations in their original order
    # within each sample (b_cell, cd8_t_cell, ...).
    table = table.sort_values("sample", kind="stable").reset_index(drop=True)

    return table[["sample", "total_count", "population", "count", "percentage"]]


def save_frequency_table(connection):
    """Compute the frequency table and store it in the database. Returns the table."""
    table = get_frequency_table(connection)
    # "replace" drops and recreates the table, so re-running never duplicates rows.
    # This is fine here because the table is derived data; the source of truth
    # is still cell_counts.
    table.to_sql("cell_frequencies", connection, if_exists="replace", index=False)
    connection.commit()
    return table


if __name__ == "__main__":
    connection = sqlite3.connect(DB_PATH)
    try:
        summary_df = save_frequency_table(connection)
    finally:
        connection.close()

    print("Part 2: Relative frequency of each cell population (first 10 rows)")
    print(summary_df.head(10).to_string(index=False))
    print(f"\nSaved {len(summary_df)} rows to the cell_frequencies table in {DB_PATH}")
