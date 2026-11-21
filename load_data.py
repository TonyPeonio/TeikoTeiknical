import sqlite3
import pandas as pd

# Creates a connection to the database
connection = sqlite3.connect("cell-count.db")
cursor = connection.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

# Build the custom schema
cursor.executescript("""
-- 1. Projects Table
CREATE TABLE projects (
    project TEXT PRIMARY KEY
);

-- 2. Subjects Table
CREATE TABLE subjects (
    subject TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    condition TEXT,
    age INTEGER,
    sex TEXT,
    treatment TEXT,
    response TEXT,
    
    -- Links this subject to a specific project
    FOREIGN KEY (project) REFERENCES projects(project)
);

-- 3. Samples Table (The actual readouts)
CREATE TABLE samples (
    sample TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    sample_type TEXT,
    time_from_treatment_start INTEGER,
    
    -- The Biological Data
    b_cell INTEGER,
    cd8_t_cell INTEGER,
    cd4_t_cell INTEGER,
    nk_cell INTEGER,
    monocyte INTEGER,
    
    -- Links this sample to a specific patient
    FOREIGN KEY (subject) REFERENCES subjects(subject)
);
""")

# Load the CSV into a Pandas DataFrame
df = pd.read_csv("cell-count.csv", skipinitialspace=True)

df.columns = df.columns.str.strip()

projects_df = df[['project']].drop_duplicates()
projects_df.to_sql("projects", connection, if_exists="append", index=False)

# Include the project column, plus the rest of the patient's static data
subjects_df = df[['subject', 'project', 'condition', 'age', 'sex', 'treatment', 'response']].drop_duplicates()
subjects_df.to_sql("subjects", connection, if_exists="append", index=False)

samples_df = df[['sample', 'subject', 'sample_type', 'time_from_treatment_start', 'b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']].drop_duplicates()
samples_df.to_sql("samples", connection, if_exists="append", index=False)

# Close the connection
connection.close()