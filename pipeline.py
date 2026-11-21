"""Build every table the dashboard needs, in one call.

`make pipeline` runs the four scripts one by one (and prints their results).
This module does the same database work without printing, so the dashboard
can build the database itself when it is started somewhere `make pipeline`
was never run, such as Streamlit Community Cloud.
"""

import os
import sqlite3

from cell_frequencies import save_frequency_table
from load_data import CSV_PATH, DB_PATH, load_csv
from statistical_analysis import save_comparison


def run_pipeline(csv_path=CSV_PATH, db_path=DB_PATH):
    """Part 1 (load) -> Part 2 (frequencies) -> Part 3 (comparison), saved to db_path."""
    load_csv(csv_path, db_path)
    connection = sqlite3.connect(db_path)
    try:
        save_frequency_table(connection)
        save_comparison(connection)
    finally:
        connection.close()


def ensure_database(csv_path=CSV_PATH, db_path=DB_PATH):
    """Build the database only if it doesn't exist yet. Returns True if it was built."""
    if os.path.exists(db_path):
        return False
    run_pipeline(csv_path, db_path)
    return True


if __name__ == "__main__":
    run_pipeline()
