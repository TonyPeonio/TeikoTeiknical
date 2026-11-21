"""Part 3: Compare responders vs. non-responders (melanoma, miraclib, PBMC).

Run with:  python statistical_analysis.py   (after load_data.py and cell_frequencies.py)

NOTE: This is the original Part 3 code, moved out of cell_frequencies.py and
switched to read from the database. The statistical method is reworked (with
tests) in the next milestone.
"""

import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
import scipy.stats as stats
import seaborn as sns

DB_PATH = "cell-count.db"

if __name__ == "__main__":
    connection = sqlite3.connect(DB_PATH)
    summary_df = pd.read_sql_query("SELECT * FROM cell_frequencies", connection)
    metadata_df = pd.read_sql_query(
        """
        SELECT samples.sample, subjects.condition, subjects.treatment,
               subjects.response, samples.sample_type
        FROM samples
        JOIN subjects ON samples.subject = subjects.subject
        """,
        connection,
    )
    connection.close()

    populations = list(summary_df["population"].unique())

    # Merges the summary and metadata dataframes based on sample
    analysis_df = pd.merge(summary_df, metadata_df, on="sample")

    # Filters by condition=melanoma, treatment=miraclib, and sample_type=PBMC
    filtered_df = analysis_df[
        (analysis_df["condition"] == "melanoma") &
        (analysis_df["treatment"] == "miraclib") &
        (analysis_df["sample_type"] == "PBMC")
    ]

    # Creates a boxplot to compare cell populations of responders vs non-responders
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=filtered_df, x="population", y="percentage", hue="response")
    plt.title("Relative Frequency of Cell Populations: Responders vs. Non-Responders")
    plt.ylabel("Relative Frequency (%)")
    plt.xlabel("Cell Population")
    plt.savefig("rel_frequency_cell_pop.png")

    # Uses the Welch's t-test to compare statistical significance of cell populations in responders vs. non-responders
    print("Analyzed using Welch's t-test")
    for pop in populations:
        responders = filtered_df[(filtered_df["population"] == pop) & (filtered_df["response"] == "yes")]["percentage"]
        non_responders = filtered_df[(filtered_df["population"] == pop) & (filtered_df["response"] == "no")]["percentage"]
        stat, p_value = stats.ttest_ind(responders, non_responders, equal_var=False)

        if p_value < 0.05:
            print(f"{pop}: Significant difference (p-value = {p_value:4f})")
        else:
            print(f"{pop}: No significant difference (p-value = {p_value:4f})")
