# Teiko Technical: Loblaw Bio miraclib analysis

Tony Peonio's submission for the Teiko bioinformatics engineering take-home (assigned 11/20/2026).

The project loads `cell-count.csv` into a SQLite database, analyses how immune cell
populations relate to miraclib response, and presents the results in an interactive
Streamlit dashboard.

**Dashboard:** _link to be added after deploying to Streamlit Community Cloud._
Locally or in Codespaces, run `make dashboard`; see below.

---

## Quick start (GitHub Codespaces)

```bash
make setup       # install pinned dependencies from requirements.txt
make pipeline    # build cell-count.db and run Parts 1-4 (prints all results)
make dashboard   # start the dashboard on port 8501
make test        # optional: run the 32 unit tests
```

After `make dashboard`, Codespaces shows a pop-up offering to open port 8501 in the
browser. If it doesn't, open the **Ports** tab and click the globe icon next to 8501.

`make pipeline` can be re-run any number of times: the database is rebuilt from the
CSV on every run.

---

## Code structure

| File | Part | What it does |
|---|---|---|
| `load_data.py` | 1 | Creates the schema and loads `cell-count.csv` into `cell-count.db` |
| `cell_frequencies.py` | 2 | Relative frequency of each population per sample, saved to the DB |
| `statistical_analysis.py` | 3 | Responders vs. non-responders: statistics, boxplot, saved to the DB |
| `subset_analysis.py` | 4 | Baseline cohort counts and the B-cell average |
| `dashboard.py` | 2-4 | Streamlit dashboard; reads only from `cell-count.db` |
| `tests/` | all | pytest unit tests (synthetic data) and a dashboard smoke test |
| `Makefile` | | `setup`, `pipeline`, `test`, `dashboard` targets |

Each script puts its logic in functions with an `if __name__ == "__main__":` block.
That means the tests and the dashboard can import and reuse the same functions,
and running each script prints its results.

Outputs that `make pipeline` generates (git-ignored):
- `cell-count.db`
- `outputs/responders_boxplot.png`

---

## Part 1: Database schema

```
projects ──< subjects ──< samples ──< cell_counts
```

| Table | Primary key | Columns |
|---|---|---|
| `projects` | `project` | |
| `subjects` | `subject` | `project` → projects, `condition`, `age`, `sex`, `treatment`, `response` |
| `samples` | `sample` | `subject` → subjects, `sample_type`, `time_from_treatment_start` |
| `cell_counts` | (`sample`, `population`) | `sample` → samples, `population`, `count` |

**Design choices**

- **Each fact is stored once.** Condition, age, sex, treatment and response belong to
  a subject, not to a sample. In the CSV they are repeated on every one of a subject's
  samples; here each is stored once per subject, so a subject's values can't contradict
  each other across samples.
- **Cell counts are stored "long"**, one row per (sample, population), instead of one
  column per population.
  - A new population, such as a Treg panel, is just new rows. No schema migration and
    no code changes are needed; Parts 2-4 pick it up automatically.
  - Queries like `GROUP BY population` work for any panel size.
  - A test loads a CSV with a 6th population to prove this.
- **Foreign keys are enforced**, so a sample can't point at a subject that doesn't exist.
- **Indexes** on the join and filter columns: subject → project, condition/treatment,
  sample → subject, sample_type/time.

**Scaling to hundreds of projects and thousands of samples**

- The schema doesn't change as data grows: new projects, subjects, samples and
  populations are all just rows. A test loads 10 projects × 50 subjects × 3 timepoints.
- The indexes keep the Part 3/4 filters fast as tables grow.
- Analytics that are expensive to recompute are saved as tables: `cell_frequencies`
  and `responder_comparison`. The dashboard reads them instead of recomputing on every
  page load.
- Beyond what SQLite comfortably handles (many concurrent writers, or many millions of
  rows), the same schema moves directly to PostgreSQL. The `cell_counts` table would be
  the first candidate for partitioning, by project or by sample type.

---

## Part 2: Relative frequencies

For each sample, `total_count` is the sum of all population counts, and
`percentage = count / total_count × 100`. The result has one row per (sample, population),
with the columns `sample, total_count, population, count, percentage`, and is saved to the
`cell_frequencies` table (52,500 rows). The dashboard's Part 2 tab can filter it by
sample and population.

---

## Part 3: Responders vs. non-responders (melanoma, miraclib, PBMC)

**Method**

1. Filter to melanoma patients treated with miraclib, PBMC samples only.
2. **Average each subject's samples** (days 0, 7 and 14) into one value per population.
   Samples from the same person are not independent. Treating the 1,968 samples as 1,968
   independent observations, when they come from only 656 people, inflates the
   effective sample size and makes p-values too small. This is pseudoreplication.
3. Compare responders (n = 331 subjects) with non-responders (n = 325) for each population
   using a two-sided **Mann-Whitney U** test. It compares ranks, so it does not assume the
   percentages are normally distributed, and it is robust to outliers.
4. Five populations means five tests. P-values are adjusted with **Benjamini-Hochberg**
   to control the false discovery rate. A population counts as significant only if its
   adjusted p < 0.05.

**Results**

| population | responder median % | non-responder median % | raw p | BH-adjusted p | significant |
|---|---|---|---|---|---|
| b_cell | 9.67 | 9.84 | 0.3458 | 0.4322 | no |
| cd8_t_cell | 24.90 | 25.01 | 0.6221 | 0.6221 | no |
| **cd4_t_cell** | 30.21 | 29.82 | **0.0124** | 0.0621 | no |
| nk_cell | 14.74 | 14.96 | 0.1267 | 0.3169 | no |
| monocyte | 19.79 | 20.28 | 0.2645 | 0.4322 | no |

**Conclusion:** no cell population differs significantly between responders and
non-responders after correcting for multiple testing. **CD4 T cells** are the strongest
candidate: responders have slightly higher CD4 frequencies (raw p = 0.012), but the
difference does not survive correction (adjusted p = 0.062). It is worth following up in
a larger cohort, or by looking at the change over time within each subject.

For transparency, the output also reports sample-level p-values (every sample treated as
independent). For example, b_cell gives p = 0.056 at sample level vs. 0.35 at subject
level, which shows how much pseudoreplication can overstate the evidence.

The boxplot (one point per subject) is shown in the dashboard and saved to
`outputs/responders_boxplot.png`.

---

## Part 4: Baseline subset analysis

Melanoma PBMC samples at baseline (`time_from_treatment_start = 0`) from patients treated
with miraclib: **656 samples from 656 subjects**.

| | |
|---|---|
| Samples per project | prj1: 384, prj3: 272 |
| Subjects by response | responders: 331, non-responders: 325 |
| Subjects by sex | male: 344, female: 312 |

Subjects are counted with `nunique()`, so a subject with more than one baseline sample is
counted once. Projects are read from the data rather than hard-coded.

**Average B-cell count** for melanoma males who responded, at time 0, across all sample
types and treatments: **10206.15**

---

## Testing

```bash
make test
```

- The 31 unit tests run on small synthetic datasets, built so the correct answer is
  known in advance. Examples: a planted responder difference that must be detected;
  a subject with two baseline samples that must be counted once.
- They also cover scaling cases: a new population, a new project, and many subjects.
- The dashboard smoke test runs the app headlessly against the real database. It is
  skipped if `make pipeline` hasn't been run.
- `pytest.ini` treats warnings as errors, so a passing run is a clean run.
