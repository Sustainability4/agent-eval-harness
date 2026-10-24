"""The seven-criterion rubric, each scored 0, 1 or 2, with written anchors.

Also defines the eight failure modes the simulated agent can inject and the
ground-truth rubric scores each one implies. Ground truth is what lets us
measure a judge's accuracy, not just its agreement with a human.
"""
from __future__ import annotations

from typing import Dict, List

CRITERIA: List[Dict[str, str]] = [
    {
        "id": "C1", "name": "Final answer correctness",
        "question": "Is the final answer correct and complete for the question asked?",
        "2": "Correct value, unit and entity; within tolerance for numeric answers.",
        "1": "Partially correct: right direction or entity but wrong magnitude, missing unit, or incomplete comparison.",
        "0": "Wrong, missing, or answers a different question.",
    },
    {
        "id": "C2", "name": "Tool selection",
        "question": "Did the agent choose the right tools for each step?",
        "2": "Every tool call is the appropriate tool for what the step needed.",
        "1": "One unnecessary or mis-chosen tool call that did not derail the task.",
        "0": "Wrong tool for a necessary step, or a necessary tool never called.",
    },
    {
        "id": "C3", "name": "Tool arguments",
        "question": "Were the arguments to each tool call correct (right entity, year, section, expression)?",
        "2": "All arguments correct.",
        "1": "One argument error that was later corrected, or a harmless one.",
        "0": "An argument error that fed a wrong input into the answer.",
    },
    {
        "id": "C4", "name": "Context freshness and sourcing",
        "question": "Did the answer rest on the specific filing, year and section the question required?",
        "2": "All required sources retrieved and used; no stale or wrong-year context.",
        "1": "Required source retrieved but a stale or extra source also influenced the answer.",
        "0": "Answer rests on the wrong year, wrong company or wrong section.",
    },
    {
        "id": "C5", "name": "Groundedness",
        "question": "Is every factual claim in the final answer supported by a tool result in the trajectory?",
        "2": "All claims traceable to retrieved text or a calculation over it.",
        "1": "A minor embellishment not supported by retrieval but not affecting the core answer.",
        "0": "A material number or fact appears that no tool result supports.",
    },
    {
        "id": "C6", "name": "Error handling",
        "question": "When a tool returned an error or empty result, did the agent notice and recover?",
        "2": "No errors occurred, or every error was detected and handled (retry, alternative, or honest abstention).",
        "1": "Error noticed but recovery was partial or clumsy.",
        "0": "Error ignored and the agent proceeded as if the call had succeeded.",
    },
    {
        "id": "C7", "name": "Efficiency",
        "question": "Did the agent reach the answer without redundant, repeated or wandering steps?",
        "2": "At or near the minimal step count for the task.",
        "1": "One or two unnecessary steps.",
        "0": "Repeated identical calls, loops, or more than double the necessary steps.",
    },
]

CRITERION_IDS = [c["id"] for c in CRITERIA]

FAILURE_MODES: Dict[str, Dict[str, object]] = {
    "clean": {
        "description": "No injected failure. Minimal correct plan, correct answer.",
        "gold": {"C1": 2, "C2": 2, "C3": 2, "C4": 2, "C5": 2, "C6": 2, "C7": 2},
    },
    "wrong_tool": {
        "description": "Agent calls calculate on a non-numeric string instead of retrieving, then answers from memory.",
        "gold": {"C1": 0, "C2": 0, "C3": 1, "C4": 0, "C5": 0, "C6": 1, "C7": 1},
    },
    "stale_context": {
        "description": "Agent retrieves the other fiscal year and answers from it.",
        "gold": {"C1": 0, "C2": 2, "C3": 0, "C4": 0, "C5": 2, "C6": 2, "C7": 2},
    },
    "unsupported_claim": {
        "description": "Correct retrieval, but the final answer adds a material figure that no tool result supports.",
        "gold": {"C1": 1, "C2": 2, "C3": 2, "C4": 2, "C5": 0, "C6": 2, "C7": 2},
    },
    "tool_error_ignored": {
        "description": "get_section returns a transient error; the agent proceeds and fabricates the value.",
        "gold": {"C1": 0, "C2": 2, "C3": 2, "C4": 0, "C5": 0, "C6": 0, "C7": 2},
    },
    "loop": {
        "description": "Agent repeats the same get_section call four times before answering correctly.",
        "gold": {"C1": 2, "C2": 2, "C3": 2, "C4": 2, "C5": 2, "C6": 2, "C7": 0},
    },
    "premature_termination": {
        "description": "Agent answers after the search step without retrieving any section.",
        "gold": {"C1": 0, "C2": 0, "C3": 2, "C4": 0, "C5": 0, "C6": 2, "C7": 2},
    },
    "arithmetic_error": {
        "description": "Correct retrieval; the calculate expression uses the wrong operands or order, giving a wrong number.",
        "gold": {"C1": 0, "C2": 2, "C3": 0, "C4": 2, "C5": 1, "C6": 2, "C7": 2},
    },
}

FAILURE_MODE_IDS = list(FAILURE_MODES)


def rubric_markdown() -> str:
    lines = ["| ID | Criterion | 2 | 1 | 0 |", "| --- | --- | --- | --- | --- |"]
    for c in CRITERIA:
        lines.append(f"| {c['id']} | {c['name']} | {c['2']} | {c['1']} | {c['0']} |")
    return "\n".join(lines)


def rubric_prompt_text() -> str:
    out = []
    for c in CRITERIA:
        out.append(f"{c['id']} {c['name']} — {c['question']}\n  2: {c['2']}\n  1: {c['1']}\n  0: {c['0']}")
    return "\n\n".join(out)
