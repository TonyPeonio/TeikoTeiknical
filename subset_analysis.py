import sqlite3
import pandas as pd

# Creates an SQLite connection and query
connection = sqlite3.connect("cell-count.db")
query = """
SELECT 
    TRIM(samples.sample) AS sample,
    TRIM(subjects.subject) AS subject,
    TRIM(subjects.project) AS project,
    TRIM(subjects.response) AS response,
    TRIM(subjects.sex) AS sex
FROM samples
INNER JOIN subjects ON TRIM(samples.subject) = TRIM(subjects.subject)
WHERE TRIM(subjects.condition) = 'melanoma'
  AND TRIM(subjects.treatment) = 'miraclib'
  AND TRIM(samples.sample_type) = 'PBMC'
  AND samples.time_from_treatment_start = 0;
"""

# Reads the query into the baseline_df
baseline_df = pd.read_sql_query(query, connection)
connection.close()

# Cleans the columns to allow for exact text matching
for col in ['project', 'response', 'sex']:
    baseline_df[col] = baseline_df[col].str.strip()

# Iterates through each project and computes the following (in addition to relevant percentages):
# --total samples
# --total responders
# ----male responders
# ----female responders
# --total non_responders
# ----male responders
# ----female responders
projects = ['prj1', 'prj2', 'prj3']
for project in projects:
    print("\n\n", project.upper())
    num_project_samples = len(baseline_df[baseline_df['project'] == project])
    print(f"Number of melanoma samples treated with miraclib: {num_project_samples}.")
    if num_project_samples > 0:
        num_responders = len(baseline_df[(baseline_df['response'] == 'yes') & (baseline_df['project'] == project)])
        num_male_responders = len(baseline_df[(baseline_df['response'] == 'yes') & (baseline_df['project'] == project) & (baseline_df['sex'] == 'M')])
        num_female_responders = len(baseline_df[(baseline_df['response'] == 'yes') & (baseline_df['project'] == project) & (baseline_df['sex'] == 'F')])
        num_non_responders = len(baseline_df[(baseline_df['response'] == 'no') & (baseline_df['project'] == project)])
        num_male_non_responders = len(baseline_df[(baseline_df['response'] == 'no') & (baseline_df['project'] == project) & (baseline_df['sex'] == 'M')])
        num_female_non_responders = len(baseline_df[(baseline_df['response'] == 'no') & (baseline_df['project'] == project) & (baseline_df['sex'] == 'F')])
        print(f"Responders from {project.upper()}: {num_responders}. Percentage responders: {float(num_responders) / num_project_samples * 100}")
        print(f"---Male Responders: {num_male_responders}. Percentage male of all responders: {num_male_responders / num_responders * 100}")
        print(f"---Female Responders: {num_female_responders}. Percentage female of all responders: {num_female_responders / num_responders * 100}")
        print(f"Non-Responders from {project.upper()}: {num_non_responders}. Percentage non-responders: {float(num_non_responders) / num_project_samples * 100}")
        print(f"---Male Responders: {num_male_non_responders}. Percentage male of all responders: {num_male_non_responders / num_non_responders * 100}")
        print(f"---Female Responders: {num_female_non_responders}. Percentage female of all responders: {num_female_non_responders / num_non_responders * 100}")
    else:
        print("No samples found in this project. No further analysis.")

# Creates a new connection to determine melanoma males of all sample and treatment types
# to find the average b cells for responders at time 0
connection = sqlite3.connect("cell-count.db")
query = """
SELECT 
  AVG(samples.b_cell) AS avg_b_cells
FROM samples
INNER JOIN subjects ON TRIM(samples.subject) = TRIM(subjects.subject)
WHERE TRIM(subjects.condition) = 'melanoma'
  AND samples.time_from_treatment_start = 0
  AND TRIM(subjects.sex) = 'M'
  AND TRIM(subjects.response) = 'yes';
"""

all_melanoma_df = pd.read_sql_query(query, connection)
connection.close()

# Prints the average b cells at time 0
avg_b_cells = all_melanoma_df['avg_b_cells'].iloc[0]
print(f"Average B Cells: {avg_b_cells:.2f}")
