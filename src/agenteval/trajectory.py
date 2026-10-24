"""Trajectory data model and a plain-text renderer used by both humans and the judge."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import json
import pathlib


@dataclass
class Step:
    kind: str  # "plan" | "tool_call" | "tool_result" | "final_answer"
    content: Any  # str for plan/final_answer; dict for tool_call/tool_result


@dataclass
class Trajectory:
    tid: str
    qid: str
    question: str
    source: str  # "simulated" | "llm:<model>"
    steps: List[Step] = field(default_factory=list)
    final_answer: Optional[str] = None
    # Ground truth is only known for simulated trajectories.
    injected_failure: Optional[str] = None
    gold_scores: Optional[Dict[str, int]] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Trajectory":
        steps = [Step(**s) for s in d.get("steps", [])]
        return cls(**{**d, "steps": steps})

    def n_tool_calls(self) -> int:
        return sum(1 for s in self.steps if s.kind == "tool_call")

    def render(self, numbered: bool = True) -> str:
        lines = [f"TRAJECTORY {self.tid}", f"QUESTION: {self.question}", ""]
        n = 0
        for s in self.steps:
            if s.kind == "plan":
                lines.append(f"[plan] {s.content}")
            elif s.kind == "tool_call":
                n += 1
                lines.append(f"[tool_call #{n}] {s.content['tool']}({json.dumps(s.content['args'])})")
            elif s.kind == "tool_result":
                lines.append(f"[tool_result #{n}] {json.dumps(s.content)}")
            elif s.kind == "final_answer":
                lines.append(f"[final_answer] {s.content}")
        return "\n".join(lines)


def save_trajectories(trajs: List[Trajectory], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([t.to_dict() for t in trajs], indent=2))


def load_trajectories(path: pathlib.Path) -> List[Trajectory]:
    return [Trajectory.from_dict(d) for d in json.loads(path.read_text())]
