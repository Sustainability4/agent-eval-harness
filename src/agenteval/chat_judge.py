"""Judge prompts for manual runs in a chat UI, and import of the saved replies.

`agenteval chat-prompts` writes batched prompts to data/LLM/prompts/{ref,noref,corpus}/.
The corpus set replaces the gold reference with the attached corpus.json, so the
judge checks answers against the raw filings the way the human scorer did.
Paste each batch into a fresh chat, save the reply verbatim as
data/LLM/responses/<run>/batch_NN.txt, then `agenteval chat-import <run>`
converts the run to results/judge_simulated_chat-<run>.json for `agenteval report`.
`agenteval batch-judge` sends the same batch prompts to an API model instead and
saves its replies in the same place, so API and chat runs go through one pipeline.
Run names are <model>_<mode>, with _r2, _r3 ... for repeats (no suffix is repeat 1).

The wording follows judge.py; the only change is that a batch of trajectories
is scored in one message and the reply is a JSON array instead of one object.
"""
from __future__ import annotations

import json
import pathlib
import random
import re
from typing import Dict, List, Optional, Tuple

from .backends import Backend
from .judge import CORPUS_REFERENCE, JudgeResult, _parse_scores, _reference_block, corpus_prefix
from .questions import Question
from .rubric import rubric_prompt_text
from .trajectory import Trajectory

CHAT_HEADER = """You are an expert evaluator of AI agent trajectories for a model-risk validation team.
You will score {n} trajectories against a seven-criterion rubric, each one independently. Scores are integers 0, 1 or 2.
Judge only what is in each trajectory. A claim in the final answer is supported only if a tool result
in that trajectory contains it or it is a correct calculation over such results.
Reply with exactly one JSON array and nothing else, one object per trajectory, in the order given:
[{{"tid": "<trajectory id>", "scores": {{"C1": int, ..., "C7": int}}, "rationale": {{"C1": "<one sentence>", ..., "C7": "<one sentence>"}}}}, ...]

RUBRIC
{rubric}
"""

CHAT_ITEM = """
==================== {tid} ====================
{reference}
TRAJECTORY
{trajectory}
"""

RUN_NAME = re.compile(r"^(?P<model>.+)_(?P<mode>ref|noref|corpus)(?:_r(?P<repeat>[1-9][0-9]*))?$")

CHAT_FOOTER = "\nScore all {n} trajectories ({tids}). Return the JSON array only.\n"


def write_chat_prompts(trajs: List[Trajectory], questions: Dict[str, Question], out_dir: pathlib.Path,
                       batch_size: int = 10, seed: int = 3) -> Dict[str, Dict[str, List[str]]]:
    """Writes prompts/{ref,noref,corpus}/batch_NN.txt and prompts/manifest.json; returns the manifest."""
    order = list(trajs)
    random.Random(seed).shuffle(order)  # same order as the human scoring sheet
    batches = [order[i:i + batch_size] for i in range(0, len(order), batch_size)]
    manifest: Dict[str, Dict[str, List[str]]] = {}
    for mode in ("ref", "noref", "corpus"):
        folder = out_dir / "prompts" / mode
        folder.mkdir(parents=True, exist_ok=True)
        manifest[mode] = {}
        for b, batch in enumerate(batches, 1):
            name = f"batch_{b:02d}"
            tids = [t.tid for t in batch]
            text = CHAT_HEADER.format(n=len(batch), rubric=rubric_prompt_text())
            text += "".join(CHAT_ITEM.format(tid=t.tid, trajectory=t.render(),
                                             reference=CORPUS_REFERENCE if mode == "corpus"
                                             else _reference_block(questions.get(t.qid), mode == "ref")) for t in batch)
            text += CHAT_FOOTER.format(n=len(batch), tids=", ".join(tids))
            (folder / f"{name}.txt").write_text(text, encoding="utf-8")
            manifest[mode][name] = tids
    (out_dir / "prompts" / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def _parse_array(text: str) -> List[dict]:
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        # Some replies drop the brackets and list the objects separated by commas.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return []
        text, start, end = "[" + text[start:end + 1] + "]", 0, end - start + 2
    try:
        arr = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    return [o for o in arr if isinstance(o, dict)] if isinstance(arr, list) else []


def import_chat_run(run_dir: pathlib.Path, tids: List[str], judge_name: str, reference_aided: bool) -> List[JudgeResult]:
    """One JudgeResult per expected tid; tids missing from every reply come back with parse_ok=False."""
    found: Dict[str, JudgeResult] = {}
    for f in sorted(run_dir.glob("batch_*.txt")):
        for obj in _parse_array(f.read_text(encoding="utf-8-sig")):
            tid = str(obj.get("tid", "")).strip()
            if tid not in tids or tid in found:
                continue
            raw = json.dumps(obj)
            scores, rationale, ok = _parse_scores(raw)
            found[tid] = JudgeResult(tid, judge_name, reference_aided, scores, rationale, raw, ok)
    return [found.get(t) or JudgeResult(t, judge_name, reference_aided, {}, {}, "", False) for t in tids]


def parse_run_name(run: str) -> Optional[Tuple[str, str, int]]:
    """'Haiku-5.5_corpus_r2' -> ('Haiku-5.5', 'corpus', 2); no _rN suffix means repeat 1."""
    m = RUN_NAME.match(run)
    return (m["model"], m["mode"], int(m["repeat"] or 1)) if m else None


def run_batches_via_api(backend: Backend, prompt_dir: pathlib.Path, out_dir: pathlib.Path,
                        corpus_json: Optional[str] = None, progress=None) -> List[str]:
    """Sends each batch prompt as the only message, as in a fresh chat, and saves the reply verbatim.
    Batches that already have a reply are skipped, so a stopped run resumes. Returns the batch names sent."""
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "api_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    batches = sorted(prompt_dir.glob("batch_*.txt"))
    sent = []
    for i, f in enumerate(batches, 1):
        out = out_dir / f.name
        if out.exists():
            continue
        prefix = corpus_prefix(corpus_json) if corpus_json is not None else None
        reply = backend.complete("", f.read_text(encoding="utf-8"), prefix=prefix)
        out.write_text(reply, encoding="utf-8")
        meta[f.stem] = {"judge": backend.name, **(getattr(backend, "last_meta", None) or {})}
        meta_path.write_text(json.dumps(meta, indent=2))
        sent.append(f.stem)
        if progress:
            progress(i, len(batches))
    return sent
