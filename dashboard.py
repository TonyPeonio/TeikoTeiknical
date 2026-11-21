"""Interactive dashboard for Bob's analysis (Parts 2-4).

Run with:  make dashboard
     (or:  python -m streamlit run dashboard.py)

Everything shown is read from cell-count.db. If the database doesn't exist
(for example on Streamlit Community Cloud, where nobody runs `make pipeline`),
it is built once from cell-count.csv on start-up.

Streamlit re-runs this whole file from top to bottom every time the user
changes a widget (a dropdown, a toggle, ...). @st.cache_data remembers a
function's result so the database isn't re-queried on every click.
"""

import sqlite3

import pandas as pd
import streamlit as st

from pipeline import ensure_database
from statistical_analysis import ALPHA, average_per_subject, build_boxplot_figure, \
    get_analysis_data
from subset_analysis import avg_b_cell_male_responders_t0, get_baseline_cohort, \
    samples_per_project, subjects_by

DB_PATH = "cell-count.db"

st.set_page_config(page_title="Loblaw Bio · miraclib immune monitoring", layout="wide")

# ---------------------------------------------------------------- styling
# Colors and the Inter font live in .streamlit/config.toml. This CSS adds the
# headline sizes and card styling Streamlit's theme options don't cover.
st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 2.5rem; }
    .hero-eyebrow { color: #FF3534; font-weight: 600; font-size: 0.95rem; margin-bottom: 0.25rem; }
    .hero-title { font-size: 3.1rem; font-weight: 800; letter-spacing: -0.045em;
                  line-height: 1.05; color: #111111; margin: 0 0 0.75rem 0; }
    .hero-sub { color: #6B6B6B; font-size: 1.15rem; font-weight: 500; max-width: 760px; }
    .section-title { font-size: 1.9rem; font-weight: 700; letter-spacing: -0.03em;
                     color: #111111; margin: 0.5rem 0 0.25rem 0; }
    .section-title .accent { color: #FF3534; }
    .muted { color: #6B6B6B; }
    .stat-card { background: #FFFFFF; border: 1px solid #ECECEC; border-radius: 12px;
                 padding: 1.1rem 1.25rem; box-shadow: 0 4px 16px rgba(0,0,0,0.04); height: 100%; }
    .stat-value { color: #FF3534; font-size: 2.1rem; font-weight: 800; letter-spacing: -0.03em; }
    .stat-label { color: #111111; font-weight: 600; font-size: 0.95rem; }
    .stat-note { color: #6B6B6B; font-size: 0.85rem; }
    .callout { background: #FFFFFF; border-left: 4px solid #FF3534; border-radius: 8px;
               padding: 0.9rem 1.1rem; color: #111111; box-shadow: 0 4px 16px rgba(0,0,0,0.04); }
    .stTabs [data-baseweb="tab-list"] { gap: 1.5rem; border-bottom: 1px solid #E5E5E5; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def section_title(accent, rest):
    """Heading in the 'Red label: black text' style."""
    st.markdown(f'<div class="section-title"><span class="accent">{accent}</span> {rest}</div>',
                unsafe_allow_html=True)


def stat_card(column, value, label, note=""):
    column.markdown(
        f'<div class="stat-card"><div class="stat-value">{value}</div>'
        f'<div class="stat-label">{label}</div><div class="stat-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- data
@st.cache_resource
def prepare_database():
    """Build the database once per server if it's missing. Returns True if it was built."""
    return ensure_database(db_path=DB_PATH)


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
def load_overview():
    return read_table(
        """
        SELECT (SELECT COUNT(*) FROM projects) AS projects,
               (SELECT COUNT(*) FROM subjects) AS subjects,
               (SELECT COUNT(*) FROM samples)  AS samples,
               (SELECT COUNT(DISTINCT population) FROM cell_counts) AS populations
        """
    ).iloc[0]


@st.cache_data
def load_comparison():
    comparison = read_table("SELECT * FROM responder_comparison")
    # SQLite has no True/False type: booleans are stored as 1/0. Turn them
    # back into True/False so they can be used as a filter (mask) again.
    comparison["significant"] = comparison["significant"].astype(bool)
    return comparison


@st.cache_data
def load_part3_data():
    connection = sqlite3.connect(DB_PATH)
    try:
        per_sample = get_analysis_data(connection)
    finally:
        connection.close()
    return per_sample, average_per_subject(per_sample), list(per_sample["population"].unique())


@st.cache_data
def load_subset():
    connection = sqlite3.connect(DB_PATH)
    try:
        cohort = get_baseline_cohort(connection)
        avg_b = avg_b_cell_male_responders_t0(connection)
    finally:
        connection.close()
    return cohort, avg_b


with st.spinner("Building the database from cell-count.csv (first start only)..."):
    prepare_database()

overview = load_overview()
comparison = load_comparison()
cohort, avg_b = load_subset()

# ---------------------------------------------------------------- hero
st.markdown('<div class="hero-eyebrow">Loblaw Bio · miraclib clinical trial</div>',
            unsafe_allow_html=True)
st.markdown('<div class="hero-title">Immune cell populations,<br>responder by responder.</div>',
            unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Relative frequencies of five immune cell populations across '
    f'{overview["samples"]:,} samples, a responder vs. non-responder comparison for '
    'melanoma patients on miraclib, and a baseline cohort breakdown.</div>',
    unsafe_allow_html=True,
)
st.write("")

c1, c2, c3, c4 = st.columns(4)
stat_card(c1, f'{overview["samples"]:,}', "Samples", f'{overview["subjects"]:,} subjects')
stat_card(c2, f'{overview["projects"]}', "Projects", f'{overview["populations"]} cell populations')
stat_card(c3, f'{int(comparison["significant"].sum())} / {len(comparison)}',
          "Significant populations", "after Benjamini-Hochberg correction")
stat_card(c4, f"{avg_b:.2f}" if avg_b is not None else "n/a", "Avg. B cells",
          "melanoma males, responders, day 0")
st.write("")

part2, part3, part4 = st.tabs(["Frequencies", "Responders", "Baseline cohort"])

# ---------------------------------------------------------------- Part 2
with part2:
    section_title("Part 2:", "Relative frequency of each population")
    st.markdown('<p class="muted">For each sample, every population\'s count as a percentage '
                'of the sample\'s total cell count.</p>', unsafe_allow_html=True)
    frequencies = load_frequencies()

    col1, col2 = st.columns(2)
    sample_search = col1.text_input("Sample id contains", placeholder="e.g. sample00001")
    chosen_populations = col2.multiselect(
        "Populations", list(frequencies["population"].unique()), placeholder="All populations")

    shown = frequencies
    if sample_search:
        shown = shown[shown["sample"].str.contains(sample_search.strip(), case=False)]
    if chosen_populations:
        shown = shown[shown["population"].isin(chosen_populations)]

    st.caption(f"{len(shown):,} of {len(frequencies):,} rows")
    st.dataframe(shown, hide_index=True, width="stretch", height=420,
                 column_config={"percentage": st.column_config.NumberColumn(format="%.2f")})

# ---------------------------------------------------------------- Part 3
with part3:
    section_title("Part 3:", "Responders vs. non-responders")
    st.markdown(
        '<p class="muted">Melanoma patients treated with miraclib, PBMC samples only. Each '
        "subject's samples (days 0, 7, 14) are averaged into one value, because samples from "
        "the same person are not independent. Populations are compared with a two-sided "
        "Mann-Whitney U test, and p-values are adjusted for five tests with Benjamini-Hochberg.</p>",
        unsafe_allow_html=True,
    )

    significant = comparison[comparison["significant"]]
    if len(significant) > 0:
        verdict = (f"<b>Significant after correction (adjusted p &lt; {ALPHA}):</b> "
                   f"{', '.join(significant['population'])}.")
    else:
        best = comparison.sort_values("p_value").iloc[0]
        verdict = (f"<b>No population differs significantly after correction</b> "
                   f"(adjusted p &lt; {ALPHA}). The strongest candidate is "
                   f"<b>{best['population']}</b>: raw p = {best['p_value']:.4f}, "
                   f"adjusted p = {best['p_adjusted']:.4f}. A larger cohort would be "
                   "needed to confirm it.")
    st.markdown(f'<div class="callout">{verdict}</div>', unsafe_allow_html=True)
    st.write("")

    per_sample, per_subject, population_order = load_part3_data()
    by_sample = st.toggle("Show every sample instead of one value per subject", value=False)
    plot_data = per_sample if by_sample else per_subject
    unit = "sample" if by_sample else "subject (mean of days 0, 7, 14)"
    st.pyplot(build_boxplot_figure(plot_data, population_order), width="stretch")
    st.caption(f"One point per {unit}. Red = responders, charcoal = non-responders.")

    st.dataframe(
        comparison, hide_index=True, width="stretch",
        column_config={
            "responder_median": st.column_config.NumberColumn("responder median %", format="%.2f"),
            "non_responder_median": st.column_config.NumberColumn("non-responder median %", format="%.2f"),
            "p_value": st.column_config.NumberColumn("p (subject level)", format="%.4f"),
            "p_adjusted": st.column_config.NumberColumn("p adjusted (BH)", format="%.4f"),
            "sample_level_p_value": st.column_config.NumberColumn("p (sample level)", format="%.4f"),
        },
    )
    st.caption("n = number of subjects. The sample-level p-value treats every sample as "
               "independent and is shown only for comparison.")

# ---------------------------------------------------------------- Part 4
with part4:
    section_title("Part 4:", "Baseline cohort")
    st.markdown('<p class="muted">Melanoma PBMC samples at baseline (time_from_treatment_start = 0) '
                'from patients treated with miraclib.</p>', unsafe_allow_html=True)

    k1, k2, k3 = st.columns(3)
    stat_card(k1, f"{len(cohort):,}", "Baseline samples")
    stat_card(k2, f"{cohort['subject'].nunique():,}", "Subjects")
    stat_card(k3, f"{cohort['project'].nunique()}", "Projects represented")
    st.write("")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Samples per project**")
        st.dataframe(samples_per_project(cohort), hide_index=True, width="stretch")
    with col2:
        st.markdown("**Subjects by response**")
        st.dataframe(subjects_by(cohort, "response"), hide_index=True, width="stretch")
    with col3:
        st.markdown("**Subjects by sex**")
        st.dataframe(subjects_by(cohort, "sex"), hide_index=True, width="stretch")

    st.write("")
    st.markdown("**Average B-cell count:** melanoma males, responders, time 0, all sample "
                "types and treatments")
    st.metric("Average B cells", f"{avg_b:.2f}" if avg_b is not None else "n/a",
              label_visibility="collapsed")
