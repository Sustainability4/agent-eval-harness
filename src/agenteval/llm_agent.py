"""A minimal ReAct-style agent driven by a real LLM backend.

The model sees the question, the tool specs and the transcript so far, and
must reply with one JSON object per turn:
  {"thought": "...", "action": "tool", "tool": "<name>", "args": {...}}
  {"thought": "...", "action": "final", "answer": "..."}
No failure injection here: whatever goes wrong goes wrong naturally.
"""
from __future__ import annotations

import json
import re
from typing import List

from .backends import Backend
from .corpus import build_corpus
from .questions import Question, build_questions
from .tools import Environment, TOOL_SPECS
from .trajectory import Step, Trajectory

SYSTEM = """You are a financial research agent. Answer the user's question about company filings
using ONLY the tools provided. Every number in your final answer must come from a tool result.
Reply with exactly one JSON object per turn and nothing else.

Tools:
{tools}

Reply format (one of):
{{"thought": "<brief>", "action": "tool", "tool": "<tool name>", "args": {{...}}}}
{{"thought": "<brief>", "action": "final", "answer": "<concise answer with units>"}}

Rules: retrieve before you answer; use calculate for arithmetic; if a tool errors, retry once or
say you could not determine the answer; do not repeat identical calls; stop within {max_steps} tool calls."""


def _tools_text() -> str:
    return "\n".join(f"- {t['name']}: {t['description']} Parameters: {json.dumps(t['parameters'])}" for t in TOOL_SPECS)


def _parse(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"action": "final", "answer": text[:300]}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"action": "final", "answer": text[:300]}


def run_llm_agent(backend: Backend, q: Question, max_steps: int = 8) -> Trajectory:
    env = Environment(build_corpus())
    tr = Trajectory(tid=f"L{int(q.qid[1:]):02d}", qid=q.qid, question=q.text, source=f"llm:{backend.name}")
    transcript: List[str] = []
    system = SYSTEM.format(tools=_tools_text(), max_steps=max_steps)

    mock_plan = list(q.gold_plan) if backend.name == "mock" else None

    for step_no in range(max_steps + 1):
        user = f"Question: {q.text}\n\nTranscript so far:\n" + ("\n".join(transcript) or "(none)") + "\n\nYour next JSON:"
        if mock_plan is not None:
            nxt = ({"action": "tool", "tool": mock_plan[0]["tool"], "args": mock_plan[0]["args"]} if mock_plan
                   else {"action": "final", "answer": q.gold_answer})
            user += "\nMOCK_AGENT_PLAN:" + json.dumps(nxt)
            if mock_plan:
                mock_plan.pop(0)
        out = _parse(backend.complete(system, user))
        thought = out.get("thought")
        if thought and step_no == 0:
            tr.steps.append(Step("plan", str(thought)))
        if out.get("action") == "tool" and step_no < max_steps:
            name, args = out.get("tool", ""), out.get("args", {}) or {}
            res = env.call(name, args)
            tr.steps.append(Step("tool_call", {"tool": name, "args": args}))
            tr.steps.append(Step("tool_result", res))
            transcript.append(f"tool_call: {name}({json.dumps(args)})\ntool_result: {json.dumps(res)}")
            continue
        answer = str(out.get("answer", "")) if out.get("action") == "final" else "(step limit reached without a final answer)"
        tr.final_answer = answer
        tr.steps.append(Step("final_answer", answer))
        break
    return tr


def build_llm_trajectories(backend: Backend, limit: int | None = None) -> List[Trajectory]:
    qs = build_questions()
    if limit:
        qs = qs[:limit]
    return [run_llm_agent(backend, q) for q in qs]
