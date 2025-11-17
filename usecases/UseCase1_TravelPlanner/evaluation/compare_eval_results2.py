import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# -----------------------------
# Load evaluation data
# -----------------------------
with open("traditional_mcp_eval_results_combined.json") as f:
    traditional_results = json.load(f)

with open("travelplanner_eval_results.json") as f:
    context_results = json.load(f)

# -----------------------------
# Config: names & diff directions
# -----------------------------
PRETTY_NAMES = {
    "execution_time_sec": "Execution Time (sec)",
    "completeness_score": "Completeness Score",
    "rougeL": "RougeL",
    "bertscore_f1": "BERTScore (F1)"
}

# Metrics where bigger is better for Context-Aware → diff = Context-Aware − Traditional
CONTEXT_MINUS_TRAD = {"completeness_score", "rougeL", "bertscore_f1"}

# -----------------------------
# Helpers
# -----------------------------
def extract_metric(data, key):
    """Return a list of metric values (floats) where present and not None."""
    return [r[key] for r in data if key in r and r[key] is not None]

def extract_pairs(trad_data, ctx_data, metric_key, id_key="query_id"):
    """
    Align per-query values for (Traditional, Context-Aware) for the given metric.
    Prefer aligning by id_key if present in both; otherwise align by index.
    Returns: trad_vals, ctx_vals, ids in ORIGINAL ORDER.
    """
    # Align by id_key if available in BOTH datasets
    has_ids = all(id_key in r for r in trad_data) and all(id_key in r for r in ctx_data)
    if has_ids:
        t_map = {r[id_key]: r for r in trad_data if metric_key in r and r[metric_key] is not None}
        c_map = {r[id_key]: r for r in ctx_data if metric_key in r and r[metric_key] is not None}
        # Keep original order from traditional_results
        ids = []
        t_vals = []
        c_vals = []
        for r in traditional_results:
            qid = r.get(id_key)
            if qid in t_map and qid in c_map:
                tv = t_map[qid][metric_key]
                cv = c_map[qid][metric_key]
                if tv is not None and cv is not None:
                    ids.append(qid)
                    t_vals.append(tv)
                    c_vals.append(cv)
    else:
        # Fallback: align by index (truncate to min length) in original order
        t_filtered = [r[metric_key] for r in trad_data if metric_key in r and r[metric_key] is not None]
        c_filtered = [r[metric_key] for r in ctx_data  if metric_key in r and r[metric_key] is not None]
        n = min(len(t_filtered), len(c_filtered))
        t_vals = t_filtered[:n]
        c_vals = c_filtered[:n]
        ids = list(range(n))

    return np.asarray(t_vals, dtype=float), np.asarray(c_vals, dtype=float), ids

def compute_diff(trad_vals, ctx_vals, metric_key):
    """
    Compute pairwise difference in ORIGINAL order with the requested direction:
    - If metric favors Context-Aware (in CONTEXT_MINUS_TRAD): diff = Context-Aware − Traditional
    - Else (execution time): diff = Traditional − Context-Aware
    Returns (diff_vals, diff_label_str)
    """
    if metric_key in CONTEXT_MINUS_TRAD:
        d = ctx_vals - trad_vals
        label = "Context-Aware − Traditional"
    else:
        d = trad_vals - ctx_vals
        label = "Traditional − Context-Aware"
    return d, label

# -----------------------------
# Styling
# -----------------------------
sns.set(style="whitegrid")

# -----------------------------
# Plotting
# -----------------------------
def plot_metric_with_diffs(metric_key, bins=20, id_key="query_id", show=True, save_path=None):
    """
    Left: overlay histogram (Traditional vs Context-Aware) with dotted mean lines (same colors).
    Right: per-query lollipop differences in ORIGINAL order with proper diff direction.
    """
    pretty = PRETTY_NAMES.get(metric_key, metric_key)

    # Get aligned values
    t_vals, c_vals, ids = extract_pairs(traditional_results, context_results, metric_key, id_key=id_key)
    if len(t_vals) == 0 or len(c_vals) == 0:
        print(f"[{metric_key}] No overlapping data to plot.")
        return

    # Means
    t_mean = float(np.mean(t_vals))
    c_mean = float(np.mean(c_vals))

    # Diff
    d_vals, diff_label = compute_diff(t_vals, c_vals, metric_key)
    d_mean = float(np.mean(d_vals))

    # Report means
    print(f"=== {pretty} ===")
    print(f"Traditional mean (blue): {t_mean:.4f}")
    print(f"Context-Aware mean (green): {c_mean:.4f}")
    print(f"Pairwise diff mean ({diff_label}): {d_mean:.4f}")

    # Subplots side-by-side
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    fig.suptitle(f"{pretty}: Distributions & Pairwise Differences - Traditional & Context-Aware MCP", fontsize=14)

    # --- Left: overlay histogram with mean lines ---
    ax = axes[0]
    ax.hist(t_vals, bins=bins, color='blue',  alpha=0.45, label='Traditional MCP')
    ax.hist(c_vals, bins=bins, color='green', alpha=0.45, label='Context-Aware MCP')

    # Dotted mean lines (same color as series)
    ax.axvline(t_mean, linestyle='--', color='blue',  linewidth=2, label=f"Traditional mean = {t_mean:.3f}")
    ax.axvline(c_mean, linestyle='--', color='green', linewidth=2, label=f"Context-Aware mean = {c_mean:.3f}")

    ax.set_title("Overlaid Histogram")
    ax.set_xlabel(pretty)
    ax.set_ylabel("Query Frequency")
    ax.legend(loc='best')

    # --- Right: pairwise differences (lollipop) in ORIGINAL order ---
    ax2 = axes[1]
    x = np.arange(len(d_vals))  # original order

    # stems & markers
    ax2.vlines(x, 0.0, d_vals, linewidth=1.6, alpha=0.7)
    ax2.scatter(x, d_vals, s=28, alpha=0.9)

    # baselines
    ax2.axhline(0.0, color='gray', linewidth=1)
    ax2.axhline(d_mean, color='C0', linestyle='--', linewidth=2, label=f"Mean diff = {d_mean:.3f}")

    ax2.set_title(f"Pairwise Differences ({diff_label})")
    # Use IDs on x-axis only if they are short; otherwise keep as index
    if ids and isinstance(ids[0], str) and len(ids) <= 40 and max(len(str(i)) for i in ids) <= 12:
        ax2.set_xticks(x)
        ax2.set_xticklabels(ids, rotation=90)
        ax2.set_xlabel("Query (original order)")
    else:
        ax2.set_xlabel("Query index")

    ax2.set_ylabel("Difference")
    ax2.legend(loc='best')

    if save_path:
        plt.savefig(save_path, dpi=200, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)

# -----------------------------
# Backward-compatible wrappers (optional)
# -----------------------------
def plot_comparative_histograms(metric_key, bins=20):
    plot_metric_with_diffs(metric_key, bins=bins)

def plot_overlay_histogram(metric_key, bins=20):
    plot_metric_with_diffs(metric_key, bins=bins)

# -----------------------------
# Example usage
# -----------------------------
# Execution Time → diff = Traditional − Context-Aware
plot_metric_with_diffs('execution_time_sec', bins=15)
# These favor Context-Aware → diff = Context-Aware − Traditional
plot_metric_with_diffs('completeness_score')
plot_metric_with_diffs('rougeL')
plot_metric_with_diffs('bertscore_f1')
