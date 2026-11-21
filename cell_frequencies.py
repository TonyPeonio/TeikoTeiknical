import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats

# Creates the dataframe from the CSV
df = pd.read_csv("cell-count.csv", skipinitialspace=True)
df.columns = df.columns.str.strip()

# Defines the cell populations
populations = ['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']

# Creates an empty template to fill in the new rows
new_rows = []

# Fills in the new rows with cell populations and percentages
for index, row in df.iterrows():
    total_count = row['b_cell'] + row['cd8_t_cell'] + row['cd4_t_cell'] + row['nk_cell'] + row['monocyte']
    for population in populations:
        count = row[population]
        percentage = (count / total_count) * 100

        new_rows.append({
            'sample': row['sample'],
            'total_count': total_count,
            'population': population,
            'count': count,
            'percentage': percentage
        })

# Creates a dataframe out of the new rows and prints the first 10 rows
summary_df = pd.DataFrame(new_rows)
print(summary_df.head(10).to_string(index=False), "\n\n")

# Defines a metadata dataframe with sample, condition, treatment, response, and sample_type
metadata_df = df[['sample', 'condition', 'treatment', 'response', 'sample_type']]

# Merges the summary and metadata dataframes based on sample
analysis_df = pd.merge(summary_df, metadata_df, on='sample')

# Filters by condition=melanoma, treatment=miraclib, and sample_type=PBMC
filtered_df = analysis_df[
    (analysis_df['condition'] == 'melanoma') &
    (analysis_df['treatment'] == 'miraclib') &
    (analysis_df['sample_type'] == 'PBMC')
]
print(filtered_df.head(10).to_string(index=False), "\n\n")

# Creates a boxplot to compare cell populations of responders vs non-responders
plt.figure(figsize=(10,6))
sns.boxplot(
    data=filtered_df,
    x='population',
    y='percentage',
    hue='response'
)
plt.title('Relative Frequency of Cell Populations: Responders vs. Non-Responders')
plt.ylabel('Relative Frequency (%)')
plt.xlabel('Cell Population')
plt.savefig("rel_frequency_cell_pop.png")

# Uses the Welch's t-test to compare statistical significance of cell populations in responders vs. non-responders
print("Analyzed using Welch's t-test")
for pop in populations:
    responders = filtered_df[(filtered_df['population'] == pop) & (filtered_df['response'] == 'yes')]['percentage']
    non_responders = filtered_df[(filtered_df['population'] == pop) & (filtered_df['response'] == 'no')]['percentage']
    stat, p_value = stats.ttest_ind(responders, non_responders, equal_var=False)

    # Uses p_value of 0.05 to define statistical significance
    # If this was scaled further, it would use additional normalization formulas to ensure that 1/20 were not statistically significant by chance
    if p_value < 0.05:
        print(f"{pop}: Significant difference (p-value = {p_value:4f})")
    else:
        print(f"{pop}: No significant difference (p-value = {p_value:4f})")