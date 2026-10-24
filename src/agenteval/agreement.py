"""Agreement statistics between two raters on the 0/1/2 rubric scores.

Rater pairs the paper reports:
  judge vs gold   (accuracy of the judge, simulated set only)
  human vs gold   (accuracy of the human, simulated set only; a sanity check on the rubric)
  judge vs human  (agreement, both sets)
Statistics per criterion and pooled: exact agreement, within-one agreement,
quadratic-weighted Cohen's kappa, and mean signed difference (rater A minus B;
positive = A is more generous).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Tuple

from .rubric import CRITERION_IDS

Scores = Dict[str, Dict[str, int]]  # tid -> {C1: s, ...}


@dataclass
class PairStats:
    n: int
    exact: float
    within_one: float
    kappa_w: float
    mean_diff: float

    def to_dict(self):
        return asdict(self)


def weighted_kappa(a: List[int], b: List[int], k: int = 3) -> float:
    """Quadratic-weighted Cohen's kappa for ordinal scores in 0..k-1."""
    n = len(a)
    if n == 0:
        return float("nan")
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[x][y] += 1
    ra = [sum(obs[i]) for i in range(k)]
    rb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]
    num = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * ra[i] * rb[j] / n for i in range(k) for j in range(k))
    if den == 0:
        return 1.0 if num == 0 else 0.0
    return 1 - num / den


def pair_stats(a: List[int], b: List[int]) -> PairStats:
    n = len(a)
    if n == 0:
        return PairStats(0, float("nan"), float("nan"), float("nan"), float("nan"))
    exact = sum(x == y for x, y in zip(a, b)) / n
    within = sum(abs(x - y) <= 1 for x, y in zip(a, b)) / n
    return PairStats(n, round(exact, 4), round(within, 4), round(weighted_kappa(a, b), 4), round(sum(x - y for x, y in zip(a, b)) / n, 4))


def compare(a: Scores, b: Scores, groups: Dict[str, str] | None = None) -> Dict[str, object]:
    """Compare rater A to rater B over the trajectories both scored.

    groups: optional tid -> group label (e.g. injected failure mode) for a by-group breakdown.
    """
    tids = sorted(set(a) & set(b))
    per_c = {}
    pooled_a: List[int] = []
    pooled_b: List[int] = []
    for c in CRITERION_IDS:
        xa = [a[t][c] for t in tids]
        xb = [b[t][c] for t in tids]
        per_c[c] = pair_stats(xa, xb).to_dict()
        pooled_a += xa
        pooled_b += xb
    out: Dict[str, object] = {"n_trajectories": len(tids), "per_criterion": per_c, "pooled": pair_stats(pooled_a, pooled_b).to_dict()}
    if groups:
        by_g: Dict[str, Tuple[List[int], List[int]]] = defaultdict(lambda: ([], []))
        for t in tids:
            g = groups.get(t, "unknown")
            for c in CRITERION_IDS:
                by_g[g][0].append(a[t][c])
                by_g[g][1].append(b[t][c])
        out["by_group"] = {g: pair_stats(xa, xb).to_dict() for g, (xa, xb) in sorted(by_g.items())}
    # Total-score view: sum over criteria (0..14), mean per rater
    ta = [sum(a[t].values()) for t in tids]
    tb = [sum(b[t].values()) for t in tids]
    out["total_score"] = {"mean_a": round(sum(ta) / max(len(ta), 1), 3), "mean_b": round(sum(tb) / max(len(tb), 1), 3)}
    return out


def disagreements(a: Scores, b: Scores, min_gap: int = 2) -> List[Dict[str, object]]:
    """Trajectory/criterion pairs where the two raters differ by at least min_gap."""
    rows = []
    for t in sorted(set(a) & set(b)):
        for c in CRITERION_IDS:
            if abs(a[t][c] - b[t][c]) >= min_gap:
                rows.append({"tid": t, "criterion": c, "a": a[t][c], "b": b[t][c]})
    return rows


def format_report(title: str, rep: Dict[str, object], a_name: str, b_name: str, runs: int = 1) -> str:
    n = rep["n_trajectories"]
    size = f"{n // runs} trajectories x {runs} runs, pooled" if runs > 1 else f"{n} trajectories"
    lines = [f"## {title}", f"n = {size}; diff = {a_name} minus {b_name}", "",
             "| Criterion | exact | within 1 | kappa_w | mean diff |", "| --- | --- | --- | --- | --- |"]
    for c, s in rep["per_criterion"].items():
        lines.append(f"| {c} | {s['exact']:.2f} | {s['within_one']:.2f} | {s['kappa_w']:.2f} | {s['mean_diff']:+.2f} |")
    p = rep["pooled"]
    lines.append(f"| **pooled** | {p['exact']:.2f} | {p['within_one']:.2f} | {p['kappa_w']:.2f} | {p['mean_diff']:+.2f} |")
    if "by_group" in rep:
        lines += ["", "| Group | n items | exact | kappa_w | mean diff |", "| --- | --- | --- | --- | --- |"]
        for g, s in rep["by_group"].items():
            lines.append(f"| {g} | {s['n']} | {s['exact']:.2f} | {s['kappa_w']:.2f} | {s['mean_diff']:+.2f} |")
    ts = rep["total_score"]
    lines += ["", f"Mean total score (0-14): {a_name} {ts['mean_a']:.2f}, {b_name} {ts['mean_b']:.2f}"]
    return "\n".join(lines)


# ---- repeats, confidence intervals, stability --------------------------------

def stack_runs(runs: List[Scores], ref: Scores, groups: Dict[str, str] | None = None):
    """Pools several runs of one rater against a single reference: each (run, tid) becomes its own item,
    paired with the reference's scores for that tid. Returns (a, b, groups) ready for compare()."""
    a: Scores = {}
    b: Scores = {}
    g: Dict[str, str] = {}
    for i, run in enumerate(runs, 1):
        for t in run:
            if t in ref:
                key = f"{t}#{i}"
                a[key], b[key] = run[t], ref[t]
                if groups:
                    g[key] = groups.get(t, "unknown")
    return a, b, (g or None)


def bootstrap_ci(runs: List[Scores], ref: Scores, n_boot: int = 2000, seed: int = 0,
                 level: float = 0.95) -> Dict[str, Tuple[float, float]]:
    """Percentile intervals for pooled exact agreement and kappa_w. Trajectories are resampled with
    replacement, and every repeat and criterion of a drawn trajectory comes with it, so repeats of the
    same trajectory are not treated as independent evidence."""
    import random

    tids = sorted(set(ref).intersection(*[set(r) for r in runs])) if runs else []
    if not tids:
        return {"exact": (float("nan"), float("nan")), "kappa_w": (float("nan"), float("nan"))}
    rng = random.Random(seed)
    exact, kappa = [], []
    for _ in range(n_boot):
        xa: List[int] = []
        xb: List[int] = []
        for t in rng.choices(tids, k=len(tids)):
            for run in runs:
                for c in CRITERION_IDS:
                    xa.append(run[t][c])
                    xb.append(ref[t][c])
        exact.append(sum(x == y for x, y in zip(xa, xb)) / len(xa))
        kappa.append(weighted_kappa(xa, xb))
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2

    def pct(v: List[float]) -> Tuple[float, float]:
        v = sorted(v)
        return round(v[int(lo_q * (len(v) - 1))], 4), round(v[int(hi_q * (len(v) - 1))], 4)

    return {"exact": pct(exact), "kappa_w": pct(kappa)}


def self_agreement(runs: List[Scores]) -> Dict[str, float] | None:
    """Run-to-run consistency of one rater: mean pairwise exact agreement and kappa_w over all pairs of
    runs, and the share of trajectory-criterion cells scored identically in every run. None if < 2 runs."""
    if len(runs) < 2:
        return None
    tids = sorted(set.intersection(*[set(r) for r in runs]))
    pairs = [(i, j) for i in range(len(runs)) for j in range(i + 1, len(runs))]
    ex, kw = [], []
    for i, j in pairs:
        xa = [runs[i][t][c] for t in tids for c in CRITERION_IDS]
        xb = [runs[j][t][c] for t in tids for c in CRITERION_IDS]
        s = pair_stats(xa, xb)
        ex.append(s.exact)
        kw.append(s.kappa_w)
    same = sum(len({r[t][c] for r in runs}) == 1 for t in tids for c in CRITERION_IDS)
    return {"runs": len(runs), "exact": round(sum(ex) / len(ex), 4), "kappa_w": round(sum(kw) / len(kw), 4),
            "all_runs_identical": round(same / max(len(tids) * len(CRITERION_IDS), 1), 4)}
