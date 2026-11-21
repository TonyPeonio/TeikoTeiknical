import pandas as pd

# Load the CSV into a Pandas DataFrame
df = pd.read_csv("cell-count.csv", skipinitialspace=True)

summary_df = pd.DataFrame(columns=['sample', 'total_count', 'population', 'count', 'percentage'])

summary_df['sample'] = df['sample']
summary_df['total_count'] = df[['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']].sum(axis=1)
summary_df['population'] = df['sample_type']
summary_df['count'] = df[['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']].sum(axis=1)
summary_df['percentage'] = summary_df['count'] / summary_df['total_count']

