"""Kappa next to signed bias, per rubric criterion, for the human and the pooled LLM judges vs gold.

Writes results/kappa_vs_bias.png. Kappa says how often a rater agrees with gold; the signed bias
(mean of rater minus gold, on the 0-2 scale) says which way it leans when it does not.

Uses the same loading and pooling as `agenteval report`. Needs matplotlib: pip install -e ".[plots]".
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from agenteval.agreement import stack_runs, weighted_kappa  # noqa: E402
from agenteval.report import group_result_files, load_runs  # noqa: E402
from agenteval.rubric import CRITERION_IDS  # noqa: E402
from agenteval.scoring_sheet import import_sheet  # noqa: E402
from agenteval.trajectory import load_trajectories  # noqa: E402

DATA, RESULTS = ROOT / "data", ROOT / "results"

CRITERION_NAMES = {
    "C1": "Answer correctness", "C2": "Tool correctness", "C3": "Argument correctness",
    "C4": "Context relevance", "C5": "Groundedness", "C6": "Error handling", "C7": "Step efficiency",
}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
HUMAN, JUDGES = "#eb6834", "#2a78d6"  # categorical slots 2 and 1


def stats(runs, gold, criteria):
    a, b, _ = stack_runs(runs, gold)
    xa = [a[k][c] for k in a for c in criteria]
    xb = [b[k][c] for k in a for c in criteria]
    return weighted_kappa(xa, xb), sum(x - y for x, y in zip(xa, xb)) / len(xa)


def load():
    sim = load_trajectories(DATA / "trajectories_simulated.json")
    gold = {t.tid: t.gold_scores for t in sim}
    human = [import_sheet(DATA / "scoring_sheet_simulated.csv")]
    judges = []
    for (dset, _), files in group_result_files(RESULTS).items():
        if dset == "simulated":
            judges += load_runs([p for _, p in files])
    return gold, human, judges


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0, colors=MUTED, labelsize=9)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def main():
    gold, human, judges = load()
    rows = [[c] for c in CRITERION_IDS] + [list(CRITERION_IDS)]
    labels = [f"{c}  {CRITERION_NAMES[c]}" for c in CRITERION_IDS] + ["All criteria (pooled)"]
    h = [stats(human, gold, r) for r in rows]
    j = [stats(judges, gold, r) for r in rows]
    ys = list(range(len(rows)))
    ys[-1] += 0.5  # gap before the pooled row
    yh, yj = [y - 0.13 for y in ys], [y + 0.13 for y in ys]  # offset so equal values don't hide each other

    fig, (ak, ab) = plt.subplots(1, 2, figsize=(12, 6.2), sharey=True, facecolor=SURFACE,
                                 gridspec_kw={"width_ratios": [1, 1.15], "wspace": 0.08})
    for ax in (ak, ab):
        ax.set_facecolor(SURFACE)
        style(ax)
        ax.axhspan(ys[1] - 0.45, ys[1] + 0.45, color="#f3ede6", zorder=0)  # C2 highlight

    # Left: kappa_w
    for y, (hk, _), (jk, _) in zip(ys, h, j):
        ak.plot([hk, jk], [y - 0.13, y + 0.13], color=GRID, linewidth=2, zorder=1)
    ak.scatter([k for k, _ in h], yh, s=70, color=HUMAN, edgecolor=SURFACE, linewidth=2, zorder=3, label="Human")
    ak.scatter([k for k, _ in j], yj, s=70, color=JUDGES, edgecolor=SURFACE, linewidth=2, zorder=3,
               label="LLM judges (5 models x 3 runs, pooled)")
    ak.set_xlim(0.4, 1.02)
    ak.set_yticks(ys, labels, fontsize=10, color=INK)
    ak.invert_yaxis()
    ak.set_title("Agreement with gold (kappa_w)\nhigher = agrees more often", loc="left",
                 fontsize=11, color=INK, fontweight="bold")
    ak.annotate(f"{h[1][0]:.2f}", (h[1][0], yh[1]), xytext=(0, 8), textcoords="offset points",
                ha="center", fontsize=9, color=INK)

    # Right: signed bias
    ab.axvline(0, color=MUTED, linewidth=1.2, zorder=1)
    for y, (_, hb), (_, jb) in zip(ys, h, j):
        ab.plot([hb, jb], [y - 0.13, y + 0.13], color=GRID, linewidth=2, zorder=1)
    ab.scatter([b for _, b in h], yh, s=70, color=HUMAN, edgecolor=SURFACE, linewidth=2, zorder=3)
    ab.scatter([b for _, b in j], yj, s=70, color=JUDGES, edgecolor=SURFACE, linewidth=2, zorder=3)
    lim = max(abs(b) for _, b in h + j) + 0.08
    ab.set_xlim(-lim, lim)
    ab.set_title("Signed bias (mean of rater minus gold, 0-2 scale)\nwhich way it leans when it disagrees",
                 loc="left", fontsize=11, color=INK, fontweight="bold")
    ab.annotate(f"{h[1][1]:+.2f}", (h[1][1], yh[1]), xytext=(0, 8), textcoords="offset points",
                ha="center", fontsize=9, color=INK)
    ab.annotate(f"human {h[-1][1]:+.2f}: the leans\ncancel out in the average", (h[-1][1], yh[-1]),
                xytext=(-14, 0), textcoords="offset points", ha="right", va="center", fontsize=9, color=INK)
    ab.text(0, -0.09, "<- harsher than gold", transform=ab.transAxes, fontsize=9, color=MUTED, ha="left")
    ab.text(1, -0.09, "more lenient than gold ->", transform=ab.transAxes, fontsize=9, color=MUTED, ha="right")

    ak.legend(loc="upper left", bbox_to_anchor=(0, -0.12), ncol=2, frameon=False, fontsize=9.5,
              labelcolor=INK, handletextpad=0.3, columnspacing=1.5)
    fig.suptitle("Kappa says how often. Bias says which way.", x=0.02, y=1.04, ha="left",
                 fontsize=14, fontweight="bold", color=INK)
    fig.text(0.02, -0.09, "Simulated set, 50 trajectories. C2 (highlighted): the human's 11 misses were all "
             "below gold (7 scored 0 where gold was 2, 4 scored 1), so kappa reads moderate while the bias "
             "shows one direction.\nJudge runs are pooled (each run of each trajectory is one item). "
             "See GOLD_CONFLICTS.md before reading agreement with gold.", fontsize=8, color=MUTED, ha="left")
    out = RESULTS / "kappa_vs_bias.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")
    for lbl, (hk, hb), (jk, jb) in zip(labels, h, j):
        print(f"{lbl:28s} human k={hk:.2f} bias={hb:+.2f} | judges k={jk:.2f} bias={jb:+.2f}")


if __name__ == "__main__":
    main()
