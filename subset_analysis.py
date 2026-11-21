"""Part 4: Baseline subset analysis of melanoma patients treated with miraclib.

Run with:  python subset_analysis.py   (after python load_data.py)

1. Baseline cohort: melanoma, miraclib, PBMC samples at time_from_treatment_start = 0.
2. Within that cohort:
     a. number of SAMPLES per project
     b. number of SUBJECTS who are responders / non-responders
     c. number of SUBJECTS who are male / female
   Subjects are counted with nunique() so a person with more than one
   baseline sample is still counted once.
3. Average B-cell count for melanoma males who responded, at time 0,
   across all sample types and treatments (two decimals).
"""

import sqlite3

import pandas as pd

DB_PATH = "cell-count.db"


def get_baseline_cohort(connection):
    """All melanoma / miraclib / PBMC samples taken at baseline (time 0)."""
    query = """
        SELECT samples.sample, samples.subject, subjects.project,
               subjects.response, subjects.sex
        FROM samples
        JOIN subjects ON samples.subject = subjects.subject
        WHERE subjects.condition = 'melanoma'
          AND subjects.treatment = 'miraclib'
          AND samples.sample_type = 'PBMC'
          AND samples.time_from_treatment_start = 0
        ORDER BY samples.sample
    """
    return pd.read_sql_query(query, connection)


def samples_per_project(cohort):
    """Number of samples in each project (projects come from the data, not a hard-coded list)."""
    # groupby("project") splits the rows into one group per project;
    # .count() then counts the samples in each group.
    counts = cohort.groupby("project", as_index=False)["sample"].count()
    return counts.rename(columns={"sample": "n_samples"})


def subjects_by(cohort, column):
    """Number of distinct subjects for each value of `column` (e.g. 'response' or 'sex')."""
    # nunique() counts DISTINCT subject ids, so a subject with two baseline
    # samples is still one person. (count() would count them twice.)
    counts = cohort.groupby(column, as_index=False)["subject"].nunique()
    return counts.rename(columns={"subject": "n_subjects"})


def avg_b_cell_male_responders_t0(connection):
    """Average B-cell count: melanoma, male, responder, time 0, any sample type/treatment.

    Returns the value rounded to 2 decimals, or None if no samples match.
    """
    query = """
        SELECT AVG(cell_counts.count)
        FROM cell_counts
        JOIN samples  ON cell_counts.sample = samples.sample
        JOIN subjects ON samples.subject = subjects.subject
        WHERE cell_counts.population = 'b_cell'
          AND subjects.condition = 'melanoma'
          AND subjects.sex = 'M'
          AND subjects.response = 'yes'
          AND samples.time_from_treatment_start = 0
    """
    average = connection.execute(query).fetchone()[0]  # AVG of zero rows is NULL -> None
    if average is None:
        return None
    return round(average, 2)


def percent(part, whole):
    """part / whole as a percentage, or 0 when whole is 0 (avoids ZeroDivisionError)."""
    return part / whole * 100 if whole else 0.0


def print_counts(table, label_column, count_column):
    total = table[count_column].sum()
    for _, row in table.iterrows():
        print(f"  {row[label_column]}: {row[count_column]} "
              f"({percent(row[count_column], total):.1f}%)")


if __name__ == "__main__":
    connection = sqlite3.connect(DB_PATH)
    try:
        cohort = get_baseline_cohort(connection)
        avg_b_cells = avg_b_cell_male_responders_t0(connection)
    finally:
        connection.close()

    print("Part 4: Melanoma PBMC samples at baseline (time 0) from miraclib-treated patients")
    print(f"Total: {len(cohort)} samples from {cohort['subject'].nunique()} subjects\n")

    print("Samples per project:")
    print_counts(samples_per_project(cohort), "project", "n_samples")

    print("\nSubjects by response:")
    print_counts(subjects_by(cohort, "response"), "response", "n_subjects")

    print("\nSubjects by sex:")
    print_counts(subjects_by(cohort, "sex"), "sex", "n_subjects")

    print("\nAverage B-cell count, melanoma males, responders, time 0 "
          "(all sample types and treatments):")
    print(f"  {avg_b_cells:.2f}" if avg_b_cells is not None else "  no matching samples")
