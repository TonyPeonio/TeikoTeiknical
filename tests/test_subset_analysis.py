"""Tests for Part 4: baseline subset queries and the B-cell average question."""

import pytest

import subset_analysis

# Columns: project,subject,condition,age,sex,treatment,response,sample,sample_type,
#          time_from_treatment_start,b_cell,cd8_t_cell,cd4_t_cell,nk_cell,monocyte
COHORT_ROWS = [
    # --- in the baseline cohort (melanoma, miraclib, PBMC, day 0) ---
    "prj1,sbjA,melanoma,50,M,miraclib,yes,a0,PBMC,0,100,1,1,1,1",
    "prj1,sbjB,melanoma,50,F,miraclib,no,b0,PBMC,0,200,1,1,1,1",
    "prj9,sbjC,melanoma,50,F,miraclib,yes,c0,PBMC,0,300,1,1,1,1",  # project not in real data
    # sbjD has TWO baseline samples: 2 samples, but still only 1 subject.
    "prj9,sbjD,melanoma,50,M,miraclib,no,d0a,PBMC,0,400,1,1,1,1",
    "prj9,sbjD,melanoma,50,M,miraclib,no,d0b,PBMC,0,500,1,1,1,1",
    # --- NOT in the cohort ---
    "prj1,sbjA,melanoma,50,M,miraclib,yes,a7,PBMC,7,999,1,1,1,1",       # not baseline
    "prj1,sbjE,melanoma,50,M,miraclib,yes,e0,WB,0,1000,1,1,1,1",        # whole blood
    "prj1,sbjF,melanoma,50,M,phauximab,yes,f0,PBMC,0,2000,1,1,1,1",     # other drug
    "prj1,sbjG,carcinoma,50,M,miraclib,yes,g0,PBMC,0,3000,1,1,1,1",     # other condition
]


def test_baseline_cohort_filters(make_db):
    conn = make_db(COHORT_ROWS)

    cohort = subset_analysis.get_baseline_cohort(conn)

    assert set(cohort["sample"]) == {"a0", "b0", "c0", "d0a", "d0b"}
    assert {"sample", "subject", "project", "response", "sex"} <= set(cohort.columns)


def test_samples_per_project_finds_every_project(make_db):
    """Projects come from the data, so a new project (prj9) shows up automatically."""
    conn = make_db(COHORT_ROWS)
    cohort = subset_analysis.get_baseline_cohort(conn)

    counts = subset_analysis.samples_per_project(cohort)

    assert dict(zip(counts["project"], counts["n_samples"])) == {"prj1": 2, "prj9": 3}


def test_response_counts_subjects_not_samples(make_db):
    """sbjD has two baseline samples but is one person."""
    conn = make_db(COHORT_ROWS)
    cohort = subset_analysis.get_baseline_cohort(conn)

    counts = subset_analysis.subjects_by(cohort, "response")

    assert dict(zip(counts["response"], counts["n_subjects"])) == {"yes": 2, "no": 2}


def test_sex_counts_subjects_not_samples(make_db):
    conn = make_db(COHORT_ROWS)
    cohort = subset_analysis.get_baseline_cohort(conn)

    counts = subset_analysis.subjects_by(cohort, "sex")

    assert dict(zip(counts["sex"], counts["n_subjects"])) == {"M": 2, "F": 2}


def test_empty_cohort_does_not_crash(make_db):
    """No matching samples -> empty tables, not a ZeroDivisionError."""
    conn = make_db(["prj1,sbjX,healthy,30,F,none,,x0,PBMC,0,1,1,1,1,1"])
    cohort = subset_analysis.get_baseline_cohort(conn)

    assert len(subset_analysis.samples_per_project(cohort)) == 0
    assert len(subset_analysis.subjects_by(cohort, "sex")) == 0


AVG_ROWS = [
    # Counted: melanoma, male, responder, day 0 -- ANY sample type and treatment.
    "prj1,m1,melanoma,50,M,miraclib,yes,m1_0,PBMC,0,100,1,1,1,1",
    "prj1,m2,melanoma,50,M,phauximab,yes,m2_0,WB,0,201,1,1,1,1",
    "prj1,m3,melanoma,50,M,miraclib,yes,m3_0,WB,0,300,1,1,1,1",
    # Not counted:
    "prj1,m1,melanoma,50,M,miraclib,yes,m1_7,PBMC,7,9999,1,1,1,1",   # day 7
    "prj1,f1,melanoma,50,F,miraclib,yes,f1_0,PBMC,0,9999,1,1,1,1",   # female
    "prj1,n1,melanoma,50,M,miraclib,no,n1_0,PBMC,0,9999,1,1,1,1",    # non-responder
    "prj1,c1,carcinoma,50,M,miraclib,yes,c1_0,PBMC,0,9999,1,1,1,1",  # carcinoma
]


def test_avg_b_cell_male_responders_at_baseline(make_db):
    conn = make_db(AVG_ROWS)

    avg = subset_analysis.avg_b_cell_male_responders_t0(conn)

    # (100 + 201 + 300) / 3 = 200.333...  ->  200.33
    assert avg == pytest.approx(200.33)


def test_avg_b_cell_is_rounded_to_two_decimals(make_db):
    conn = make_db(AVG_ROWS)

    avg = subset_analysis.avg_b_cell_male_responders_t0(conn)

    assert avg == round(avg, 2)
