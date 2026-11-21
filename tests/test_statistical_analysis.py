"""Tests for Part 3: responders vs. non-responders (melanoma, miraclib, PBMC).

The synthetic data below is built so we KNOW the right answer:
  - cd4_t_cell is clearly higher in responders and monocyte clearly lower
    (cd4 + monocyte always add to 50, so the sample total doesn't change).
  - b_cell, cd8_t_cell and nk_cell are identical in both groups, so they
    must NOT come out as significant.
Every subject has 3 samples (days 0, 7, 14), like the real data.
"""

import pytest
from scipy.stats import false_discovery_control

import statistical_analysis

N_PER_GROUP = 10


def planted_rows():
    rows = []
    for response in ("yes", "no"):
        for i in range(N_PER_GROUP):
            subject = f"sbj_{response}_{i}"
            # Same values for both groups, varying a little by subject.
            b, cd8, nk = 10 + i % 5, 20 + (i * 3) % 7, 20 + (i * 2) % 3
            if response == "yes":
                cd4, mono = 40 + i % 3, 10 - i % 3
            else:
                cd4, mono = 20 + i % 3, 30 - i % 3
            for day in (0, 7, 14):
                rows.append(
                    f"prj1,{subject},melanoma,60,F,miraclib,{response},"
                    f"{subject}_d{day},PBMC,{day},{b},{cd8},{cd4},{nk},{mono}"
                )
    return rows


# Rows that must be filtered OUT of Part 3 (wrong condition / treatment / sample type).
EXCLUDED_ROWS = [
    "prj1,sbj_h,healthy,30,M,none,,s_h,PBMC,0,99,1,1,1,1",
    "prj1,sbj_c,carcinoma,30,M,miraclib,yes,s_c,PBMC,0,99,1,1,1,1",
    "prj1,sbj_p,melanoma,30,M,phauximab,yes,s_p,PBMC,0,99,1,1,1,1",
    "prj1,sbj_w,melanoma,30,M,miraclib,yes,s_w,WB,0,99,1,1,1,1",
]


# ---------- filtering ----------

def test_only_melanoma_miraclib_pbmc_samples_are_used(make_db):
    conn = make_db(planted_rows() + EXCLUDED_ROWS)

    data = statistical_analysis.get_analysis_data(conn)

    assert set(data["sample"]).isdisjoint({"s_h", "s_c", "s_p", "s_w"})
    assert data["sample"].nunique() == 2 * N_PER_GROUP * 3
    assert {"subject", "response", "population", "percentage"} <= set(data.columns)


# ---------- one value per subject ----------

def test_average_per_subject_collapses_repeated_samples(make_db):
    """3 samples per subject must become 1 value per subject per population."""
    conn = make_db(planted_rows())
    data = statistical_analysis.get_analysis_data(conn)

    per_subject = statistical_analysis.average_per_subject(data)

    assert len(per_subject) == 2 * N_PER_GROUP * 5
    assert not per_subject.duplicated(subset=["subject", "population"]).any()


def test_average_per_subject_is_the_mean():
    import pandas as pd
    data = pd.DataFrame({
        "subject": ["a", "a", "a"],
        "response": ["yes", "yes", "yes"],
        "population": ["b_cell"] * 3,
        "percentage": [10.0, 20.0, 60.0],
    })

    per_subject = statistical_analysis.average_per_subject(data)

    assert per_subject["percentage"].iloc[0] == pytest.approx(30.0)


# ---------- multiple-testing correction ----------

def test_benjamini_hochberg_hand_example():
    # Sorted: 0.005, 0.01, 0.03, 0.04  ->  p * m / rank  ->  0.02, 0.02, 0.04, 0.04
    adjusted = statistical_analysis.benjamini_hochberg([0.01, 0.04, 0.03, 0.005])
    assert adjusted == pytest.approx([0.02, 0.04, 0.04, 0.02])


def test_benjamini_hochberg_matches_scipy():
    p_values = [0.001, 0.2, 0.012, 0.04, 0.5, 0.03]
    expected = list(false_discovery_control(p_values, method="bh"))
    assert statistical_analysis.benjamini_hochberg(p_values) == pytest.approx(expected)


def test_benjamini_hochberg_never_above_one():
    assert max(statistical_analysis.benjamini_hochberg([0.9, 0.95, 0.99])) <= 1.0


# ---------- the full comparison ----------

def test_compare_responders_finds_the_planted_difference(make_db):
    conn = make_db(planted_rows() + EXCLUDED_ROWS)

    results = statistical_analysis.compare_responders(conn)
    significant = set(results.loc[results["significant"], "population"])

    assert significant == {"cd4_t_cell", "monocyte"}


def test_compare_responders_counts_subjects_not_samples(make_db):
    """n must be the number of people (10), not samples (30)."""
    conn = make_db(planted_rows())

    results = statistical_analysis.compare_responders(conn)

    assert (results["n_responders"] == N_PER_GROUP).all()
    assert (results["n_non_responders"] == N_PER_GROUP).all()


def test_compare_responders_output_columns(make_db):
    conn = make_db(planted_rows())

    results = statistical_analysis.compare_responders(conn)

    for col in ["population", "n_responders", "n_non_responders",
                "responder_median", "non_responder_median",
                "p_value", "p_adjusted", "significant", "sample_level_p_value"]:
        assert col in results.columns
    assert len(results) == 5
    # significant must agree with the adjusted p-value, not the raw one.
    assert (results["significant"] == (results["p_adjusted"] < 0.05)).all()


def test_boxplot_is_saved(make_db, tmp_path):
    conn = make_db(planted_rows())
    out = tmp_path / "plots" / "boxplot.png"

    statistical_analysis.make_boxplot(conn, out)

    assert out.exists()
