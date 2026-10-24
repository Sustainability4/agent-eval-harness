"""Builds results/report.md from the human sheets and every judge results file.

Results files for the same judge and mode that differ only in a repeat suffix
(_r2, _r3 ...; no suffix is repeat 1) are grouped and pooled. Every headline
figure carries a 95% bootstrap interval that resamples trajectories, and
judges with two or more runs get a run-to-run stability row.
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .agreement import Scores, bootstrap_ci, compare, format_report, self_agreement, stack_runs
from .rubric import CRITERION_IDS

REPEAT = re.compile(r"_r([1-9][0-9]*)$")


def group_result_files(results_dir: pathlib.Path) -> Dict[Tuple[str, str], List[Tuple[int, pathlib.Path]]]:
    """(set, judge key) -> [(repeat, path), ...] sorted by repeat. The set is 'simulated' or 'llm'."""
    groups: Dict[Tuple[str, str], List[Tuple[int, pathlib.Path]]] = defaultdict(list)
    for f in sorted(results_dir.glob("judge_*.json")):
        name = f.stem[len("judge_"):]
        dset, _, rest = name.partition("_")
        m = REPEAT.search(rest)
        key, rep = (rest[: m.start()], int(m.group(1))) if m else (rest, 1)
        groups[(dset, key)].append((rep, f))
    return {k: sorted(v) for k, v in sorted(groups.items())}


def display_name(key: str) -> str:
    """'chat-Haiku-5.5_corpus' -> 'Haiku-5.5 (corpus)'."""
    base, _, mode = key.rpartition("_")
    base = base[len("chat-"):] if base.startswith("chat-") else base
    return f"{base} ({mode})" if base else key


def load_runs(paths: List[pathlib.Path]) -> List[Scores]:
    runs = []
    for p in paths:
        rows = json.loads(p.read_text())
        runs.append({r["tid"]: r["scores"] for r in rows if r["parse_ok"]})
    return runs


def _ci(point: float, ci: Tuple[float, float]) -> str:
    return f"{point:.2f} [{ci[0]:.2f}, {ci[1]:.2f}]"


def _vs(runs: List[Scores], ref: Scores, n_boot: int) -> Tuple[Dict, Dict]:
    a, b, _ = stack_runs(runs, ref)
    return compare(a, b)["pooled"], bootstrap_ci(runs, ref, n_boot=n_boot)


def _summary_row(label: str, runs: List[Scores], gold: Scores, human: Scores, n_boot: int) -> str:
    cells = [label, str(len(runs))]
    for ref in (gold, human):
        if ref:
            p, ci = _vs(runs, ref, n_boot)
            cells += [_ci(p["exact"], ci["exact"]), _ci(p["kappa_w"], ci["kappa_w"])]
        else:
            cells += ["—", "—"]
    sa = self_agreement(runs)
    cells.append(f"{sa['kappa_w']:.2f}" if sa else "—")
    totals = [sum(r[t].values()) for r in runs for t in r]
    cells.append(f"{sum(totals) / max(len(totals), 1):.2f}")
    return "| " + " | ".join(cells) + " |"


def _disagreement_table(name: str, runs: List[Scores], gold: Scores, modes: Dict[str, str]) -> Optional[str]:
    rows = []
    for t in sorted(gold):
        for c in CRITERION_IDS:
            vals = [r[t][c] for r in runs if t in r]
            if any(abs(v - gold[t][c]) >= 2 for v in vals):
                hits = sum(abs(v - gold[t][c]) >= 2 for v in vals)
                rows.append(f"| {t} | {modes.get(t)} | {c} | {', '.join(map(str, vals))} | {gold[t][c]} | {hits} of {len(vals)} |")
    if not rows:
        return None
    return (f"### Largest judge-vs-gold disagreements [{name}] (gap of 2)\n\n"
            "| tid | mode | criterion | judge, by run | gold | runs with gap 2 |\n| --- | --- | --- | --- | --- | --- |\n"
            + "\n".join(rows))


def build_report(results_dir: pathlib.Path, gold: Scores, modes: Dict[str, str], human_sim: Scores,
                 human_llm: Scores, version: str, n_boot: int = 2000) -> Optional[str]:
    groups = group_result_files(results_dir)
    sim = {k: v for k, v in groups.items() if k[0] == "simulated"}
    llm = {k: v for k, v in groups.items() if k[0] != "simulated"}
    if not (human_sim or sim or llm):
        return None

    out = [f"# Agreement report\n\nagenteval {version}\n",
           "Judges with several runs (_r2, _r3 ...) are pooled: each run of each trajectory counts as an item. "
           f"Brackets are 95% bootstrap intervals ({n_boot} resamples of the trajectories; all runs and criteria "
           "of a drawn trajectory move together). kappa_w is quadratic-weighted Cohen's kappa. "
           "Run-to-run is the mean kappa_w between pairs of a judge's own runs. "
           "See GOLD_CONFLICTS.md before reading agreement with gold."]

    loaded = {k: load_runs([p for _, p in v]) for k, v in groups.items()}

    if gold and (human_sim or sim):
        head = ("| Rater | runs | vs gold exact | vs gold kappa_w | vs human exact | vs human kappa_w | run-to-run kappa_w | mean total (0-14) |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |")
        rows = []
        if human_sim:
            rows.append(_summary_row("Human", [human_sim], gold, {}, n_boot))
        for k in sim:
            rows.append(_summary_row(display_name(k[1]), loaded[k], gold, human_sim, n_boot))
        gold_total = sum(sum(v.values()) for v in gold.values()) / max(len(gold), 1)
        out.append(f"## Summary: simulated set\n\n{head}\n" + "\n".join(rows) + f"\n\nGold mean total: {gold_total:.2f}")

        stab = []
        for k in sim:
            sa = self_agreement(loaded[k])
            if sa:
                per_run = ", ".join(f"{compare(r, gold)['pooled']['kappa_w']:.2f}" for r in loaded[k])
                stab.append(f"| {display_name(k[1])} | {sa['runs']} | {per_run} | {sa['exact']:.2f} | {sa['kappa_w']:.2f} | {sa['all_runs_identical']:.2f} |")
        if stab:
            out.append("## Run-to-run stability\n\n"
                       "| Judge | runs | kappa_w vs gold, by run | pairwise exact | pairwise kappa_w | cells identical in every run |\n"
                       "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(stab))

    if human_sim and gold:
        out.append(format_report("Human vs ground truth (simulated set)", compare(human_sim, gold, modes), "human", "gold"))

    for k, files in sim.items():
        name, runs = display_name(k[1]), loaded[k]
        a, b, g = stack_runs(runs, gold, modes)
        out.append(format_report(f"Judge [{name}] vs ground truth", compare(a, b, g), "judge", "gold", runs=len(runs)))
        if human_sim:
            a, b, g = stack_runs(runs, human_sim, modes)
            out.append(format_report(f"Judge [{name}] vs human (simulated set)", compare(a, b, g), "judge", "human", runs=len(runs)))
        dis = _disagreement_table(name, runs, gold, modes)
        if dis:
            out.append(dis)

    for k in llm:
        name, runs = display_name(k[1]), loaded[k]
        if human_llm:
            a, b, _ = stack_runs(runs, human_llm)
            p, ci = _vs(runs, human_llm, n_boot)
            out.append(format_report(f"Judge [{name}] vs human (LLM-agent set)", compare(a, b), "judge", "human", runs=len(runs))
                       + f"\n\nPooled with 95% intervals: exact {_ci(p['exact'], ci['exact'])}, kappa_w {_ci(p['kappa_w'], ci['kappa_w'])}")
        else:
            out.append(f"## Judge [{name}] on LLM-agent set\n\nNo human sheet found at data/scoring_sheet_llm.csv; nothing to compare against.")

    return "\n\n".join(out) + "\n"
