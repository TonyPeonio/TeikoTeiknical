"""Part 3: Compare responders vs. non-responders (melanoma, miraclib, PBMC).

Run with:  python statistical_analysis.py   (after python load_data.py)

Method, in order:
  1. Keep only melanoma patients treated with miraclib, PBMC samples.
  2. Average each subject's samples (days 0, 7, 14) into ONE value per
     population. Samples from the same person are not independent, so
     treating them as separate data points would inflate the sample size
     and make p-values look smaller than they really are (pseudoreplication).
  3. For each population, a Mann-Whitney U test (two-sided) compares
     responders vs. non-responders. It compares ranks rather than means, so
     it does not assume the percentages are normally distributed.
  4. Five populations means five tests, so the p-values are adjusted with
     Benjamini-Hochberg to control the false discovery rate. A population
     is called significant only if its ADJUSTED p-value is < 0.05.

Outputs:
  - printed results table + plain-English conclusion
  - outputs/responders_boxplot.png
  - `responder_comparison` table in the database (for the dashboard)
"""

import os
import sqlite3

import matplotlib
matplotlib.use("Agg")  # draw to files only; no window needed (works on servers / Codespaces)
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import mannwhitneyu

from cell_frequencies import get_frequency_table

DB_PATH = "cell-count.db"
BOXPLOT_PATH = os.path.join("outputs", "responders_boxplot.png")
ALPHA = 0.05


def get_analysis_data(connection):
    """Part 2 frequency table + subject info, filtered to melanoma / miraclib / PBMC."""
    frequencies = get_frequency_table(connection)

    metadata = pd.read_sql_query(
        """
        SELECT samples.sample, samples.subject, samples.sample_type,
               samples.time_from_treatment_start,
               subjects.condition, subjects.treatment, subjects.response
        FROM samples
        JOIN subjects ON samples.subject = subjects.subject
        """,
        connection,
    )

    # Attach each sample's metadata to its population rows (like a SQL JOIN on sample).
    data = pd.merge(frequencies, metadata, on="sample")

    # Each condition makes a True/False column; & keeps rows where all are True.
    keep = (
        (data["condition"] == "melanoma") &
        (data["treatment"] == "miraclib") &
        (data["sample_type"] == "PBMC")
    )
    return data[keep].reset_index(drop=True)


def average_per_subject(data):
    """Collapse each subject's samples into one mean percentage per population."""
    # Every unique (subject, response, population) combination becomes one row,
    # holding the mean of that subject's percentages for that population.
    # (response is constant per subject; grouping by it just keeps the column.)
    return data.groupby(
        ["subject", "response", "population"], as_index=False
    )["percentage"].mean()


def benjamini_hochberg(p_values):
    """Return Benjamini-Hochberg adjusted p-values, in the same order as given.

    Steps:
      1. Sort the p-values from smallest to largest; rank 1 is the smallest.
      2. adjusted = p * m / rank   (m = number of tests).
      3. Walk from the largest rank down and never let an adjusted value
         exceed the one after it. This keeps the adjusted values in the same
         order as the raw ones, and starting the running minimum at 1.0
         caps everything at 1.
    """
    m = len(p_values)
    # Positions of the p-values, ordered from smallest p to largest p.
    order = sorted(range(m), key=lambda i: p_values[i])

    adjusted = [0.0] * m
    running_min = 1.0
    for rank in range(m, 0, -1):          # rank = m, m-1, ..., 1
        i = order[rank - 1]               # position of the p-value with this rank
        value = p_values[i] * m / rank
        running_min = min(running_min, value)
        adjusted[i] = running_min
    return adjusted


def compare_responders(connection, alpha=ALPHA):
    """Run the responder vs. non-responder comparison for every population.

    Returns one row per population with group sizes (in subjects), medians,
    the raw and BH-adjusted p-values, and whether the difference is significant.
    The sample-level p-value (the old, non-independent approach) is included
    only for comparison.
    """
    data = get_analysis_data(connection)
    per_subject = average_per_subject(data)

    rows = []
    for population in data["population"].unique():
        # Subject-level values (one per person) -> used for the real test.
        subj = per_subject[per_subject["population"] == population]
        responders = subj[subj["response"] == "yes"]["percentage"]
        non_responders = subj[subj["response"] == "no"]["percentage"]
        p_value = mannwhitneyu(responders, non_responders, alternative="two-sided").pvalue

        # Sample-level values (3 per person) -> reported for transparency only.
        samp = data[data["population"] == population]
        sample_p = mannwhitneyu(
            samp[samp["response"] == "yes"]["percentage"],
            samp[samp["response"] == "no"]["percentage"],
            alternative="two-sided",
        ).pvalue

        rows.append({
            "population": population,
            "n_responders": len(responders),
            "n_non_responders": len(non_responders),
            "responder_median": responders.median(),
            "non_responder_median": non_responders.median(),
            "p_value": p_value,
            "sample_level_p_value": sample_p,
        })

    results = pd.DataFrame(rows)
    results["p_adjusted"] = benjamini_hochberg(list(results["p_value"]))
    results["significant"] = results["p_adjusted"] < alpha
    return results


# (response value, legend label, color). Coral red + charcoal, matching the dashboard theme.
GROUPS = [("yes", "Responders", "#FF3534"), ("no", "Non-responders", "#3A3D4A")]


def build_boxplot_figure(data, population_order, title=None):
    """One small boxplot panel per population: responders vs. non-responders.

    `data` needs the columns population, response and percentage. It can be the
    per-subject averages (one value per person) or the per-sample rows.
    Each population gets its own panel and y-axis, because the populations sit
    at very different levels (B cells ~10%, CD4 T cells ~30%) and a shared
    axis would squash the small differences we care about.
    """
    n = len(population_order)
    # sharey=False -> every panel picks its own y-range.
    fig, axes = plt.subplots(1, n, figsize=(2.6 * n, 4.6), sharey=False)
    if n == 1:
        axes = [axes]  # plt.subplots returns a single Axes (not a list) when n == 1

    for ax, population in zip(axes, population_order):
        values, colors, labels = [], [], []
        for response, label, color in GROUPS:
            mask = (data["population"] == population) & (data["response"] == response)
            values.append(data[mask]["percentage"])
            colors.append(color)
            labels.append(label)

        # patch_artist=True draws boxes as filled shapes so they can be colored.
        boxes = ax.boxplot(values, patch_artist=True, widths=0.6,
                           medianprops={"color": "white", "linewidth": 2},
                           flierprops={"marker": "o", "markersize": 3,
                                       "markerfacecolor": "#9A9A9A", "markeredgecolor": "none"},
                           whiskerprops={"color": "#6B6B6B"}, capprops={"color": "#6B6B6B"})
        for box, color in zip(boxes["boxes"], colors):
            box.set_facecolor(color)
            box.set_edgecolor(color)

        ax.set_title(population, fontsize=11, fontweight="bold", color="#111111")
        ax.set_xticks([1, 2])
        ax.set_xticklabels(["Resp.", "Non-resp."], fontsize=9, color="#6B6B6B")
        # Clean look: light horizontal grid, no top/right box lines.
        ax.grid(axis="y", color="#E5E5E5", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#D0D0D0")
        ax.tick_params(colors="#6B6B6B", labelsize=9)

    axes[0].set_ylabel("Relative frequency (%)", color="#6B6B6B")
    if title:
        fig.suptitle(title, fontsize=12, fontweight="bold", color="#111111")
    fig.tight_layout()
    return fig


def make_boxplot(connection, path=BOXPLOT_PATH):
    """Save a boxplot of per-subject relative frequencies, responders vs. non-responders."""
    data = get_analysis_data(connection)
    per_subject = average_per_subject(data)
    population_order = list(data["population"].unique())

    # Create the output folder if it doesn't exist yet (e.g. outputs/).
    folder = os.path.dirname(str(path))
    if folder:
        os.makedirs(folder, exist_ok=True)

    fig = build_boxplot_figure(
        per_subject, population_order,
        title="Relative frequency per subject: responders vs. non-responders "
              "(melanoma, miraclib, PBMC)")
    fig.savefig(path)
    plt.close(fig)  # free the memory; important if this runs many times
    return per_subject


def describe_results(results, alpha=ALPHA):
    """Plain-English summary of the comparison."""
    significant = results[results["significant"]]
    if len(significant) > 0:
        names = ", ".join(significant["population"])
        return (f"Significant after Benjamini-Hochberg correction (adjusted p < {alpha}): {names}.")

    best = results.sort_values("p_value").iloc[0]
    return (
        f"No population differs significantly after Benjamini-Hochberg correction "
        f"(adjusted p < {alpha}). The strongest candidate is {best['population']} "
        f"(raw p = {best['p_value']:.4f}, adjusted p = {best['p_adjusted']:.4f}), "
        f"which would need more subjects to confirm."
    )


def save_comparison(connection):
    """Run the comparison and store it in the database for the dashboard. Returns the results."""
    results = compare_responders(connection)
    # "replace" so re-running never duplicates rows.
    results.to_sql("responder_comparison", connection, if_exists="replace", index=False)
    connection.commit()
    return results


if __name__ == "__main__":
    connection = sqlite3.connect(DB_PATH)
    try:
        results = save_comparison(connection)
        make_boxplot(connection)
    finally:
        connection.close()

    print("Part 3: Responders vs. non-responders (melanoma, miraclib, PBMC)")
    print("Test: Mann-Whitney U on per-subject averages, Benjamini-Hochberg corrected\n")
    # .4f = 4 digits after the decimal point. (A bare "4f" would mean
    # "minimum width 4", which is not the same thing.)
    print(results.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\n" + describe_results(results))
    print(f"\nBoxplot saved to {BOXPLOT_PATH}")
