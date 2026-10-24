"""Interactive terminal scorer for the human scoring sheet.

Shows one rendered trajectory at a time with the current criterion's anchors
underneath, and asks for C1..C7 and an optional note. It reads only the blind
renders in data/render/<set>/, never the trajectory JSON, so the injected
failure mode and gold scores are never loaded. The sheet is saved after every
trajectory; rerun to resume at the first unscored row.
"""
from __future__ import annotations

import csv
import os
import pathlib
from typing import Dict, List, Optional, Tuple, Union

from .rubric import CRITERIA, CRITERION_IDS

KEYS = "0/1/2 score   Enter keep   b back   r full rubric   s skip   q save and quit"


def _clear(enabled: bool) -> None:
    if enabled:
        os.system("cls" if os.name == "nt" else "clear")


def _read_sheet(path: pathlib.Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _write_sheet(path: pathlib.Path, header: List[str], rows: List[Dict[str, str]]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def _is_scored(row: Dict[str, str]) -> bool:
    return all((row.get(c) or "").strip() in ("0", "1", "2") for c in CRITERION_IDS)


def criterion_text(c: Dict[str, str]) -> str:
    return f"{c['id']} {c['name']}: {c['question']}\n  2  {c['2']}\n  1  {c['1']}\n  0  {c['0']}"


def full_rubric_text() -> str:
    return "\n\n".join(criterion_text(c) for c in CRITERIA)


def _score_one(row: Dict[str, str], render: str, progress: str, clear: bool, ask=input) -> Union[Dict[str, str], str]:
    """Returns the updated scores and note, or "skip" / "quit"."""
    scores = {c: (row.get(c) or "").strip() for c in CRITERION_IDS}
    i = 0
    while i < len(CRITERIA):
        c = CRITERIA[i]
        _clear(clear)
        print(f"{progress}   {row['tid']}\n{'=' * 78}\n{render}\n{'-' * 78}")
        print(criterion_text(c))
        print("\n" + "  ".join(f"{k}={scores[k] or '.'}" for k in CRITERION_IDS))
        print(KEYS)
        ans = ask(f"{c['id']}> ").strip().lower()
        if ans in ("0", "1", "2"):
            scores[c["id"]] = ans
            i += 1
        elif ans == "" and scores[c["id"]] in ("0", "1", "2"):
            i += 1
        elif ans == "b":
            i = max(i - 1, 0)
        elif ans == "r":
            _clear(clear)
            print(full_rubric_text())
            ask("\nEnter to return ")
        elif ans in ("s", "q"):
            return "skip" if ans == "s" else "quit"
    note = (row.get("notes") or "").strip()
    new_note = ask(f"notes (Enter {'keeps current' if note else 'for none'}): ").strip()
    return {**scores, "notes": new_note or note}


def interactive_score(sheet: pathlib.Path, render_dir: pathlib.Path, redo: bool = False,
                      start: Optional[str] = None, clear: bool = True, ask=input) -> None:
    header, rows = _read_sheet(sheet)
    missing = [h for h in ["order", "tid"] + CRITERION_IDS if h not in header]
    if missing:
        print(f"{sheet} is not a scoring sheet (missing columns: {', '.join(missing)}); regenerate it with `agenteval generate`")
        return
    todo =[r for r in rows if redo or not _is_scored(r)]
    if start:
        tids = [r["tid"] for r in todo]
        todo = todo[tids.index(start):] if start in tids else []
    if not todo:
        print(f"nothing to score in {sheet} (use --redo to revisit scored rows)")
        return
    try:
        for row in todo:
            path = render_dir / f"{row['tid']}.txt"
            render = path.read_text().rstrip() if path.exists() else f"(no rendered trajectory at {path})"
            done = sum(_is_scored(r) for r in rows)
            res = _score_one(row, render, f"row {row['order']} of {len(rows)} | {done} scored", clear, ask)
            if res == "quit":
                break
            if res == "skip":
                continue
            row.update(res)
            while True:
                try:
                    _write_sheet(sheet, header, rows)
                    break
                except PermissionError:
                    ask(f"could not save {sheet.name}: close it in any other program, then press Enter ")
    except (KeyboardInterrupt, EOFError):
        print("\ninterrupted; the trajectory in progress was not saved")
    print(f"{sum(_is_scored(r) for r in rows)}/{len(rows)} trajectories fully scored in {sheet}")
