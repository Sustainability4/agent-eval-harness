"""Human scoring sheet: export a blank CSV, import a filled one."""
from __future__ import annotations

import csv
import pathlib
import random
from typing import Dict, List

from .rubric import CRITERION_IDS
from .trajectory import Trajectory

HEADER = ["order", "tid", "question"] + CRITERION_IDS + ["notes"]


def export_sheet(trajs: List[Trajectory], path: pathlib.Path, shuffle_seed: int | None = 3) -> None:
    """Blank sheet. Rows are shuffled so the scorer cannot infer the failure mode from order."""
    rows = list(trajs)
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for i, t in enumerate(rows, 1):
            w.writerow([i, t.tid, t.question] + [""] * len(CRITERION_IDS) + [""])


def import_sheet(path: pathlib.Path) -> Dict[str, Dict[str, int]]:
    """Returns tid -> scores for every fully scored row; partially scored rows are skipped with a warning."""
    out: Dict[str, Dict[str, int]] = {}
    skipped = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            try:
                scores = {c: int(row[c]) for c in CRITERION_IDS}
            except (ValueError, KeyError):
                skipped.append(row.get("tid"))
                continue
            if any(v not in (0, 1, 2) for v in scores.values()):
                skipped.append(row.get("tid"))
                continue
            out[row["tid"]] = scores
    if skipped:
        print(f"[scoring_sheet] skipped {len(skipped)} unscored/invalid rows: {', '.join(str(s) for s in skipped[:10])}{'...' if len(skipped) > 10 else ''}")
    return out


def write_renders(trajs: List[Trajectory], folder: pathlib.Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for t in trajs:
        (folder / f"{t.tid}.txt").write_text(t.render() + "\n")
