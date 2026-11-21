import pandas as pd

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

print(summary_df.head(10).to_string(index=False))