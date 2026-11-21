"""Interactive dashboard for Bob's analysis (Parts 2-4).

Run with:  make dashboard
     (or:  python -m streamlit run dashboard.py)

Everything shown here is read from cell-count.db, which `make pipeline` builds.
Streamlit re-runs this whole file from top to bottom every time the user
changes a widget (a dropdown, a slider, ...). @st.cache_data remembers a
function's result so the database isn't re-queried on every click.
"""

import os
import sqlite3

import pandas as pd
import streamlit as st

from statistical_analysis import ALPHA, average_per_subject, build_boxplot_figure, \
    describe_results, get_analysis_data
from subset_analysis import avg_b_cell_male_responders_t0, get_baseline_cohort, \
    samples_per_project, subjects_by

DB_PATH = "cell-count.db"

st.set_page_config(page_title="Loblaw Bio: miraclib analysis", layout="wide")
st.title("Loblaw Bio: immune cell populations under miraclib")

# Stop early with a helpful message if the pipeline hasn't been run.
if not os.path.exists(DB_PATH):
    st.error("cell-count.db not found. Run `make pipeline` first, then reload this page.")
    st.stop()


def read_table(query):
    """Run a SQL query against the database and return a DataFrame."""
    connection = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(query, connection)
    finally:
        connection.close()


@st.cache_data
def load_frequencies():
    return read_table("SELECT * FROM cell_frequencies")


@st.cache_data
def load_comparison():
    comparison = read_table("SELECT * FROM responder_comparison")
    # SQLite has no True/False type: booleans are stored as 1/0. Turn them
    # back into True/False so they can be used as a filter (mask) again.
    comparison["significant"] = comparison["significant"].astype(bool)
    return comparison


@st.cache_data
def load_per_subject():
    connection = sqlite3.connect(DB_PATH)
    try:
        data = get_analysis_data(connection)
    finally:
        connection.close()
    return average_per_subject(data), list(data["population"].unique())


@st.cache_data
def load_subset():
    connection = sqlite3.connect(DB_PATH)
    try:
        cohort = get_baseline_cohort(connection)
        avg_b = avg_b_cell_male_responders_t0(connection)
    finally:
        connection.close()
    return cohort, avg_b


part2, part3, part4 = st.tabs([
    "Part 2: Cell frequencies",
    "Part 3: Responders vs. non-responders",
    "Part 4: Baseline subset",
])

# ---------------- Part 2 ----------------
with part2:
    st.header("Relative frequency of each cell population per sample")
    frequencies = load_frequencies()

    col1, col2 = st.columns(2)
    sample_search = col1.text_input("Filter by sample id (e.g. sample00001)")
    chosen_populations = col2.multiselect(
        "Populations", sorted(frequencies["population"].unique()))

    shown = frequencies
    if sample_search:
        shown = shown[shown["sample"].str.contains(sample_search.strip(), case=False)]
    if chosen_populations:
        shown = shown[shown["population"].isin(chosen_populations)]

    st.caption(f"{len(shown):,} of {len(frequencies):,} rows")
    st.dataframe(shown, hide_index=True, width="stretch",
                 column_config={"percentage": st.column_config.NumberColumn(format="%.2f")})

# ---------------- Part 3 ----------------
with part3:
    st.header("Melanoma patients on miraclib, PBMC samples")
    st.markdown(
        "Each subject's samples (days 0, 7, 14) are averaged into one value, because "
        "samples from the same person are not independent. Populations are compared "
        "with a two-sided **Mann-Whitney U** test, and p-values are adjusted for "
        "testing five populations with **Benjamini-Hochberg**."
    )

    comparison = load_comparison()
    per_subject, population_order = load_per_subject()

    st.info(describe_results(comparison, ALPHA))
    st.pyplot(build_boxplot_figure(per_subject, population_order))
    st.dataframe(
        comparison, hide_index=True, width="stretch",
        column_config={
            col: st.column_config.NumberColumn(format="%.4f")
            for col in ["responder_median", "non_responder_median", "p_value",
                        "sample_level_p_value", "p_adjusted"]
        },
    )
    st.caption("n = number of subjects. sample_level_p_value treats every sample as "
               "independent and is shown only for comparison.")

# ---------------- Part 4 ----------------
with part4:
    st.header("Melanoma PBMC samples at baseline (day 0), treated with miraclib")
    cohort, avg_b = load_subset()

    st.metric("Baseline samples", len(cohort))

    col1, col2, col3 = st.columns(3)
    col1.subheader("Samples per project")
    col1.dataframe(samples_per_project(cohort), hide_index=True)
    col2.subheader("Subjects by response")
    col2.dataframe(subjects_by(cohort, "response"), hide_index=True)
    col3.subheader("Subjects by sex")
    col3.dataframe(subjects_by(cohort, "sex"), hide_index=True)

    st.subheader("Average B-cell count")
    st.metric("Melanoma males, responders, day 0 (all sample types and treatments)",
              f"{avg_b:.2f}" if avg_b is not None else "n/a")
