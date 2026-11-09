"""Heatmaps of quadratic-weighted kappa for each judge, against gold and against the human.

Writes two PNGs to results/:
  kappa_by_criterion.png  - one column per rubric criterion (C1..C7) plus all criteria pooled
  kappa_by_eval_term.png  - criteria grouped into common LLM eval terms (answer correctness,
                            context relevance, groundedness, tool use, error handling, efficiency)

Uses the same loading and pooling as `agenteval report`, so the "All" column matches the
summary table in results/report.md. Needs matplotlib: pip install -e ".[plots]".
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from agenteval.agreement import stack_runs, weighted_kappa  # noqa: E402
from agenteval.report import display_name, group_result_files, load_runs  # noqa: E402
from agenteval.rubric import CRITERION_IDS  # noqa: E402
from agenteval.scoring_sheet import import_sheet  # noqa: E402
from agenteval.trajectory import load_trajectories  # noqa: E402

DATA, RESULTS = ROOT / "data", ROOT / "results"

CRITERION_LABELS = {
    "C1": "C1\nAnswer\ncorrectness", "C2": "C2\nTool\ncorrectness", "C3": "C3\nArgument\ncorrectness",
    "C4": "C4\nContext\nrelevance", "C5": "C5\nGrounded-\nness", "C6": "C6\nError\nhandling",
    "C7": "C7\nStep\nefficiency",
}
# Criteria grouped by the eval term they are usually reported under (see README, "The rubric").
TERM_GROUPS = [
    ("Answer correctness\n(outcome)\nC1", ["C1"]),
    ("Context relevance\n(retrieval)\nC4", ["C4"]),
    ("Groundedness /\nfaithfulness\nC5", ["C5"]),
    ("Tool use\n(tool + args)\nC2, C3", ["C2", "C3"]),
    ("Error handling\n(robustness)\nC6", ["C6"]),
    ("Step efficiency\nC7", ["C7"]),
    ("RAG triad\n\nC1, C4, C5", ["C1", "C4", "C5"]),
    ("Trajectory\n(process)\nC2, C3, C6, C7", ["C2", "C3", "C6", "C7"]),
    ("All criteria\n(pooled)", list(CRITERION_IDS)),
]

# Sequential blue ramp, light -> dark.
CMAP = LinearSegmentedColormap.from_list(
    "seq_blue", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
VMIN, VMAX = 0.3, 1.0
INK, MUTED = "#1f1f1e", "#6b6b66"


def kappa(runs, ref, criteria) -> float | None:
    a, b, _ = stack_runs(runs, ref)
    xa = [a[k][c] for k in a for c in criteria]
    xb = [b[k][c] for k in a for c in criteria]
    return weighted_kappa(xa, xb) if xa else None


def load():
    sim = load_trajectories(DATA / "trajectories_simulated.json")
    gold = {t.tid: t.gold_scores for t in sim}
    human = import_sheet(DATA / "scoring_sheet_simulated.csv")
    raters = [("Human", [human])]
    for (dset, key), files in group_result_files(RESULTS).items():
        if dset == "simulated":
            raters.append((f"{display_name(key).replace(' (corpus)', '')}  (x{len(files)} runs)",
                           load_runs([p for _, p in files])))
    return gold, human, raters


def grid(raters, ref, columns):
    return [[kappa(runs, ref, crits) for _, crits in columns] for _, runs in raters]


def heatmap(ax, values, row_labels, col_labels, title, pooled_cols):
    n_rows, n_cols = len(values), len(col_labels)
    for i, row in enumerate(values):
        for j, v in enumerate(row):
            t = min(max((v - VMIN) / (VMAX - VMIN), 0), 1)
            ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=CMAP(t), edgecolor="white", linewidth=2))
            ax.text(j + .5, i + .5, f"{v:.2f}", ha="center", va="center", fontsize=10,
                    fontweight="bold" if j in pooled_cols else "normal", color="white" if t > .55 else INK)
    for j in pooled_cols:  # separate summary columns from the per-criterion ones
        ax.axvline(j, color=INK, linewidth=1.2)
    ax.set_xlim(0, n_cols)
    ax.set_ylim(n_rows, 0)
    ax.set_xticks([j + .5 for j in range(n_cols)], col_labels, fontsize=8.5, color=INK)
    ax.set_yticks([i + .5 for i in range(n_rows)], row_labels, fontsize=10, color=INK)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, fontsize=12, fontweight="bold", color=INK, loc="left", pad=58)


def figure(gold, human, raters, columns, pooled_cols, suptitle, out):
    labels = [c for c, _ in columns]
    judges = [r for r in raters if r[0] != "Human"]
    fig, axes = plt.subplots(2, 1, figsize=(1.25 * len(columns) + 3.2, 11),
                             gridspec_kw={"height_ratios": [len(raters), len(judges)], "hspace": 0.55},
                             facecolor="white")
    heatmap(axes[0], grid(raters, gold, columns), [n for n, _ in raters], labels,
            "vs gold (injected-failure answer key)", pooled_cols)
    heatmap(axes[1], grid(judges, human, columns), [n for n, _ in judges], labels,
            "vs human scores", pooled_cols)
    fig.suptitle(suptitle, x=0.02, y=1.04, ha="left", fontsize=14, fontweight="bold", color=INK)
    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(VMIN, VMAX))
    cb = fig.colorbar(sm, ax=axes, fraction=0.025, pad=0.02)
    cb.set_label(f"quadratic-weighted kappa (colour clipped at {VMIN})", color=MUTED)
    cb.outline.set_visible(False)
    fig.text(0.02, 0.04, "Simulated set, 50 trajectories. Judge runs are pooled (each run of each trajectory is "
             "one item). Grouped columns pool every score in the group. See GOLD_CONFLICTS.md before reading "
             "agreement with gold.", fontsize=8, color=MUTED, ha="left")
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def main():
    gold, human, raters = load()
    by_crit = [(CRITERION_LABELS[c], [c]) for c in CRITERION_IDS] + [("All\ncriteria\n(pooled)", list(CRITERION_IDS))]
    figure(gold, human, raters, by_crit, [len(CRITERION_IDS)],
           "Judge agreement by rubric criterion (kappa_w)", RESULTS / "kappa_by_criterion.png")
    first_summary = next(i for i, (lbl, _) in enumerate(TERM_GROUPS) if lbl.startswith("RAG"))
    figure(gold, human, raters, TERM_GROUPS, list(range(first_summary, len(TERM_GROUPS))),
           "Judge agreement by LLM eval term (kappa_w)", RESULTS / "kappa_by_eval_term.png")


if __name__ == "__main__":
    main()
