import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats

df = pd.read_csv("cell-count.csv", skipinitialspace=True)
df.columns = df.columns.str.strip()

populations = ['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']

new_rows = []

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

summary_df = pd.DataFrame(new_rows)

print(summary_df.head(10).to_string(index=False), "\n\n")

metadata_df = df[['sample', 'condition', 'treatment', 'response', 'sample_type']]
analysis_df = pd.merge(summary_df, metadata_df, on='sample')

filtered_df = analysis_df[
    (analysis_df['condition'] == 'melanoma') &
    (analysis_df['treatment'] == 'miraclib') &
    (analysis_df['sample_type'] == 'PBMC')
]

print(filtered_df.head(10).to_string(index=False), "\n\n")

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

populations = ['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']

print("Analyzed using Welch's t-test")

for pop in populations:
    responders = filtered_df[(filtered_df['population'] == pop) & (filtered_df['response'] == 'yes')]['percentage']
    non_responders = filtered_df[(filtered_df['population'] == pop) & (filtered_df['response'] == 'no')]['percentage']

    stat, p_value = stats.ttest_ind(responders, non_responders, equal_var=False)

    if p_value < 0.05:
        print(f"{pop}: Significant difference (p-value = {p_value:4f})")
    else:
        print(f"{pop}: No significant difference (p-value = {p_value:4f})")