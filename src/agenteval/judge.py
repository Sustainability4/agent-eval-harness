"""LLM-as-judge: score a trajectory against the rubric, one JSON object out.

Three reference modes:
  ref     (default): the judge sees the gold answer and the required sources.
  noref:  the judge sees only the question and the trajectory.
  corpus: no gold answer; the judge gets corpus.json, the raw filings, and checks
          answers against it, as the human scorer did.
A judge that needs the answer key is a weaker tool for second-line validation,
where the key often does not exist but the underlying data does.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from typing import Any, Callable, Dict, List, Optional

from .backends import Backend
from .questions import Question
from .rubric import CRITERION_IDS, rubric_prompt_text
from .trajectory import Trajectory

JUDGE_SYSTEM = """You are an expert evaluator of AI agent trajectories for a model-risk validation team.
You will score ONE trajectory against a seven-criterion rubric. Scores are integers 0, 1 or 2.
Judge only what is in the trajectory. A claim in the final answer is supported only if a tool result
in the trajectory contains it or it is a correct calculation over such results.
Reply with exactly one JSON object and nothing else:
{"scores": {"C1": int, ..., "C7": int}, "rationale": {"C1": "<one sentence>", ..., "C7": "<one sentence>"}}"""

CORPUS_REFERENCE = """REFERENCE: no gold answer provided. The attached file corpus.json contains the filing data for every
company and fiscal year. Use it to check whether the final answer is correct."""

MODES = ("ref", "noref", "corpus")

JUDGE_USER = """RUBRIC
{rubric}

{reference}
TRAJECTORY
{trajectory}

Score the trajectory. Return the JSON object only."""


@dataclass
class JudgeResult:
    tid: str
    judge: str
    reference_aided: bool
    scores: Dict[str, int]
    rationale: Dict[str, str]
    raw: str
    parse_ok: bool
    mode: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)  # backend call details: tokens, stop reason, ids

    def to_dict(self):
        return asdict(self)


def _reference_block(q: Optional[Question], aided: bool) -> str:
    if not aided or q is None:
        return "REFERENCE: none provided. Judge correctness from internal consistency and the retrieved text."
    srcs = "; ".join(f"{s['ticker']} {s['fiscal_year']} {s['section']}" for s in q.required_sources)
    return f"REFERENCE\nGold answer: {q.gold_answer}\nRequired sources: {srcs}\nMinimal correct tool calls: {len(q.gold_plan)}"


def _parse_scores(text: str) -> tuple[Dict[str, int], Dict[str, str], bool]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {c: 0 for c in CRITERION_IDS}, {}, False
    try:
        obj = json.loads(m.group(0))
        scores = {c: int(obj["scores"][c]) for c in CRITERION_IDS}
        for c, v in scores.items():
            if v not in (0, 1, 2):
                raise ValueError(c)
        rationale = {c: str(obj.get("rationale", {}).get(c, "")) for c in CRITERION_IDS}
        return scores, rationale, True
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return {c: 0 for c in CRITERION_IDS}, {}, False


def corpus_prefix(corpus_json: str) -> str:
    """The corpus block sent ahead of the prompt, standing in for the chat-UI file attachment."""
    return f"Attached file corpus.json:\n{corpus_json}"


def judge_trajectory(backend: Backend, tr: Trajectory, q: Optional[Question], reference_aided: bool = True,
                     mode: Optional[str] = None, corpus_json: Optional[str] = None) -> JudgeResult:
    mode = mode or ("ref" if reference_aided else "noref")
    if mode == "corpus" and corpus_json is None:
        raise ValueError("corpus mode needs corpus_json")
    reference = CORPUS_REFERENCE if mode == "corpus" else _reference_block(q, mode == "ref")
    user = JUDGE_USER.format(rubric=rubric_prompt_text(), reference=reference, trajectory=tr.render())
    raw = backend.complete(JUDGE_SYSTEM, user, prefix=corpus_prefix(corpus_json) if mode == "corpus" else None)
    scores, rationale, ok = _parse_scores(raw)
    return JudgeResult(tid=tr.tid, judge=backend.name, reference_aided=mode == "ref", scores=scores, rationale=rationale,
                       raw=raw, parse_ok=ok, mode=mode, meta=dict(getattr(backend, "last_meta", None) or {}))


def judge_all(backend: Backend, trajs: List[Trajectory], questions: Dict[str, Question], reference_aided: bool = True,
              progress=None, mode: Optional[str] = None, corpus_json: Optional[str] = None,
              on_result: Optional[Callable[[JudgeResult], None]] = None) -> List[JudgeResult]:
    """on_result is called after every trajectory, so a caller can save progress and resume later."""
    out = []
    for i, tr in enumerate(trajs):
        r = judge_trajectory(backend, tr, questions.get(tr.qid), reference_aided, mode=mode, corpus_json=corpus_json)
        out.append(r)
        if on_result:
            on_result(r)
        if progress:
            progress(i + 1, len(trajs))
    return out
