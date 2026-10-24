"""Fifty questions over the corpus, each with a gold answer and a gold plan.

The gold plan is the minimal correct tool sequence. It is used by the simulated
agent (to produce clean trajectories before failure injection) and by the
judge's reference material.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import json
import pathlib
import random

from .corpus import Filing, build_corpus

METRICS = {
    "revenue": ("income_statement", "revenue_musd", "USD million"),
    "net income": ("income_statement", "net_income_musd", "USD million"),
    "total debt": ("balance_sheet", "total_debt_musd", "USD million"),
    "cash and equivalents": ("balance_sheet", "cash_musd", "USD million"),
    "year-end employee count": ("operations", "employees", "employees"),
}


@dataclass
class Question:
    qid: str
    qtype: str
    text: str
    gold_answer: str
    gold_value: float | None
    gold_plan: List[Dict[str, Any]]  # [{"tool":..., "args":...}, ...]
    required_sources: List[Dict[str, str]]  # (ticker, fiscal_year, section) the answer must rest on
    tolerance: float = 0.01  # relative tolerance for numeric answers

    def to_dict(self):
        return asdict(self)


def _f(filings: List[Filing], ticker: str, fy: str) -> Filing:
    return next(f for f in filings if f.ticker == ticker and f.fiscal_year == fy)


def build_questions(seed: int = 7) -> List[Question]:
    rng = random.Random(seed)
    filings = build_corpus()
    tickers = sorted({f.ticker for f in filings})
    names = {f.ticker: f.company for f in filings}
    qs: List[Question] = []

    def src(t, fy, sec):
        return {"ticker": t, "fiscal_year": fy, "section": sec}

    def plan_search(t):
        return {"tool": "search_filings", "args": {"query": names[t]}}

    def plan_get(t, fy, sec):
        return {"tool": "get_section", "args": {"ticker": t, "fiscal_year": fy, "section": sec}}

    # A. single-value lookups (12)
    for i in range(12):
        t = tickers[i % len(tickers)]
        fy = "FY2025" if i % 3 else "FY2024"
        metric = list(METRICS)[i % len(METRICS)]
        sec, attr, unit = METRICS[metric]
        v = getattr(_f(filings, t, fy), attr)
        qs.append(Question(
            qid=f"Q{len(qs) + 1:02d}", qtype="lookup",
            text=f"What was {names[t]}'s {metric} in {fy}?",
            gold_answer=f"{v:,.1f} {unit}" if unit != "employees" else f"{v:,} employees",
            gold_value=float(v),
            gold_plan=[plan_search(t), plan_get(t, fy, sec)],
            required_sources=[src(t, fy, sec)],
        ))

    # B. year-over-year percentage change (10)
    for i in range(10):
        t = tickers[(i + 3) % len(tickers)]
        metric = ["revenue", "net income", "total debt", "cash and equivalents"][i % 4]
        sec, attr, _ = METRICS[metric]
        a, b = getattr(_f(filings, t, "FY2024"), attr), getattr(_f(filings, t, "FY2025"), attr)
        pct = (b - a) / a * 100
        qs.append(Question(
            qid=f"Q{len(qs) + 1:02d}", qtype="yoy_change",
            text=f"By what percentage did {names[t]}'s {metric} change from FY2024 to FY2025?",
            gold_answer=f"{pct:+.1f}%",
            gold_value=round(pct, 2),
            gold_plan=[plan_search(t), plan_get(t, "FY2024", sec), plan_get(t, "FY2025", sec),
                       {"tool": "calculate", "args": {"expression": f"({b} - {a}) / {a} * 100"}}],
            required_sources=[src(t, "FY2024", sec), src(t, "FY2025", sec)],
            tolerance=0.02,
        ))

    # C. debt-to-cash ratio (8)
    for i in range(8):
        t = tickers[i]
        fy = "FY2025" if i % 2 == 0 else "FY2024"
        f = _f(filings, t, fy)
        r = f.total_debt_musd / f.cash_musd
        qs.append(Question(
            qid=f"Q{len(qs) + 1:02d}", qtype="ratio",
            text=f"What was {names[t]}'s ratio of total debt to cash and equivalents in {fy}?",
            gold_answer=f"{r:.2f}x",
            gold_value=round(r, 3),
            gold_plan=[plan_search(t), plan_get(t, fy, "balance_sheet"),
                       {"tool": "calculate", "args": {"expression": f"{f.total_debt_musd} / {f.cash_musd}"}}],
            required_sources=[src(t, fy, "balance_sheet")],
            tolerance=0.02,
        ))

    # D. two-company comparison (8)
    for i in range(8):
        a, b = rng.sample(tickers, 2)
        fy = "FY2025" if i % 2 == 0 else "FY2024"
        metric = ["revenue", "net income"][i % 2]
        sec, attr, _ = METRICS[metric]
        va, vb = getattr(_f(filings, a, fy), attr), getattr(_f(filings, b, fy), attr)
        winner = a if va > vb else b
        qs.append(Question(
            qid=f"Q{len(qs) + 1:02d}", qtype="compare",
            text=f"Which company reported higher {metric} in {fy}: {names[a]} or {names[b]}?",
            gold_answer=f"{names[winner]} ({max(va, vb):,.1f} vs {min(va, vb):,.1f} USD million)",
            gold_value=None,
            gold_plan=[plan_search(a), plan_search(b), plan_get(a, fy, sec), plan_get(b, fy, sec)],
            required_sources=[src(a, fy, sec), src(b, fy, sec)],
        ))

    # E. top risk factor (6)
    for i in range(6):
        t = tickers[(i * 2 + 1) % len(tickers)]
        fy = "FY2025" if i % 2 == 0 else "FY2024"
        f = _f(filings, t, fy)
        qs.append(Question(
            qid=f"Q{len(qs) + 1:02d}", qtype="risk",
            text=f"What does {names[t]} list as its highest-priority risk factor in its {fy} filing?",
            gold_answer=f.risk_factors[0],
            gold_value=None,
            gold_plan=[plan_search(t), plan_get(t, fy, "risk_factors")],
            required_sources=[src(t, fy, "risk_factors")],
        ))

    # F. net margin (6)
    for i in range(6):
        t = tickers[(i * 3 + 2) % len(tickers)]
        fy = "FY2024" if i % 2 == 0 else "FY2025"
        f = _f(filings, t, fy)
        m = f.net_income_musd / f.revenue_musd * 100
        qs.append(Question(
            qid=f"Q{len(qs) + 1:02d}", qtype="margin",
            text=f"What was {names[t]}'s net profit margin in {fy}?",
            gold_answer=f"{m:.1f}%",
            gold_value=round(m, 2),
            gold_plan=[plan_search(t), plan_get(t, fy, "income_statement"),
                       {"tool": "calculate", "args": {"expression": f"{f.net_income_musd} / {f.revenue_musd} * 100"}}],
            required_sources=[src(t, fy, "income_statement")],
            tolerance=0.02,
        ))

    assert len(qs) == 50, len(qs)
    return qs


def save_questions(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([q.to_dict() for q in build_questions()], indent=2))


def load_questions(path: pathlib.Path | None = None) -> List[Question]:
    if path is None or not path.exists():
        return build_questions()
    return [Question(**d) for d in json.loads(path.read_text())]
