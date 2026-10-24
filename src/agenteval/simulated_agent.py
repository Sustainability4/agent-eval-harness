"""Scripted agent that produces trajectories with known, injected failure modes.

For every question we first build the clean trajectory by executing the gold
plan against the environment, then mutate it according to one failure mode.
Each trajectory carries its injected mode and the implied gold rubric scores.
"""
from __future__ import annotations

import copy
import random
from typing import Dict, List

from .corpus import build_corpus
from .questions import Question, build_questions
from .rubric import FAILURE_MODES, FAILURE_MODE_IDS
from .tools import Environment
from .trajectory import Step, Trajectory

CALC_TYPES = {"yoy_change", "ratio", "margin"}


def _other_fy(fy: str) -> str:
    return "FY2024" if fy == "FY2025" else "FY2025"


def _answer_sentence(q: Question, value_text: str) -> str:
    return f"{value_text}"


def _run_plan(env: Environment, q: Question, plan: List[Dict]) -> List[Step]:
    steps: List[Step] = [Step("plan", _plan_text(q))]
    for p in plan:
        res = env.call(p["tool"], p["args"])
        steps.append(Step("tool_call", {"tool": p["tool"], "args": p["args"]}))
        steps.append(Step("tool_result", res))
    return steps


def _plan_text(q: Question) -> str:
    t = {
        "lookup": "Find the filing, read the relevant section, report the value with units.",
        "yoy_change": "Find the filing, read both fiscal years, compute the percentage change.",
        "ratio": "Find the filing, read the balance sheet, divide total debt by cash.",
        "compare": "Find both filings, read the same section for each, compare the values.",
        "risk": "Find the filing, read the risk factors section, report the first-listed item.",
        "margin": "Find the filing, read the income statement, compute net income over revenue.",
    }
    return t[q.qtype]


def _fab(v: float, mult: float) -> float:
    return round(v * mult, 1)


def _clean_answer(q: Question) -> str:
    return q.gold_answer


def build_simulated_trajectories(seed: int = 11) -> List[Trajectory]:
    rng = random.Random(seed)
    filings = build_corpus()
    qs = build_questions()
    by_key = {(f.ticker, f.fiscal_year): f for f in filings}

    # Assign modes: six of each of the eight modes = 48, plus two more clean = 50.
    pool = [m for m in FAILURE_MODE_IDS for _ in range(6)] + ["clean", "clean"]
    rng.shuffle(pool)
    # arithmetic_error only makes sense on calc questions: swap assignments to satisfy that.
    qlist = list(qs)
    rng.shuffle(qlist)
    assignment: Dict[str, str] = {}
    calc_qs = [q for q in qlist if q.qtype in CALC_TYPES]
    other_qs = [q for q in qlist if q.qtype not in CALC_TYPES]
    arith = [m for m in pool if m == "arithmetic_error"]
    rest = [m for m in pool if m != "arithmetic_error"]
    for q, m in zip(calc_qs, arith):
        assignment[q.qid] = m
    remaining = [q for q in qlist if q.qid not in assignment]
    for q, m in zip(remaining, rest):
        assignment[q.qid] = m

    trajs: List[Trajectory] = []
    for q in qs:
        mode = assignment[q.qid]
        env = Environment(filings)
        tid = f"S{int(q.qid[1:]):02d}"
        tr = Trajectory(tid=tid, qid=q.qid, question=q.text, source="simulated",
                        injected_failure=mode, gold_scores=dict(FAILURE_MODES[mode]["gold"]))

        if mode == "clean":
            tr.steps = _run_plan(env, q, q.gold_plan)
            tr.final_answer = _clean_answer(q)

        elif mode == "wrong_tool":
            steps = [Step("plan", "Compute the figure directly with the calculator.")]
            expr = f"{q.text.split(chr(39))[0]} figure"
            res = env.call("calculate", {"expression": expr})
            steps += [Step("tool_call", {"tool": "calculate", "args": {"expression": expr}}), Step("tool_result", res)]
            tr.steps = steps
            if q.gold_value is not None:
                tr.final_answer = _fabricated_answer(q, 1.17)
            else:
                tr.final_answer = _fabricated_text_answer(q, by_key)

        elif mode == "stale_context":
            plan = copy.deepcopy(q.gold_plan)
            for p in plan:
                if p["tool"] == "get_section":
                    p["args"]["fiscal_year"] = _other_fy(p["args"]["fiscal_year"])
            if q.qtype == "yoy_change":
                # Both years now point at FY2024: the agent computes a 0% change.
                for p in plan:
                    if p["tool"] == "get_section":
                        p["args"]["fiscal_year"] = "FY2024"
                    if p["tool"] == "calculate":
                        a = _metric_value(q, by_key, "FY2024")
                        p["args"]["expression"] = f"({a} - {a}) / {a} * 100"
                tr.steps = _run_plan(env, q, plan)
                tr.final_answer = "+0.0%"
            else:
                for p in plan:
                    if p["tool"] == "calculate":
                        p["args"]["expression"] = _recompute_expression(q, by_key, _other_fy(_q_fy(q)))
                tr.steps = _run_plan(env, q, plan)
                tr.final_answer = _answer_for_year(q, by_key, _other_fy(_q_fy(q)))

        elif mode == "unsupported_claim":
            tr.steps = _run_plan(env, q, q.gold_plan)
            extra = _unsupported_extra(q, by_key, rng)
            tr.final_answer = f"{_clean_answer(q)}. {extra}"

        elif mode == "tool_error_ignored":
            first_ticker = next(p["args"]["ticker"] for p in q.gold_plan if p["tool"] == "get_section")
            env = Environment(filings, flaky={first_ticker: 1})
            # The first get_section errors and the agent does not retry. If a calculation follows,
            # the value it never retrieved is replaced by an invented one, and the answer follows the calc.
            plan = copy.deepcopy(q.gold_plan)
            first_get = next(p for p in plan if p["tool"] == "get_section")
            missing_fy = first_get["args"]["fiscal_year"]
            calc = next((p for p in plan if p["tool"] == "calculate"), None)
            if calc is not None:
                real = _metric_value(q, by_key, missing_fy) if q.qtype == "yoy_change" else None
                if q.qtype == "yoy_change":
                    calc["args"]["expression"] = calc["args"]["expression"].replace(str(real), str(_fab(real, 0.93)), 1)
                else:  # ratio / margin: both operands came from the one failed call
                    f = by_key[(first_get["args"]["ticker"], missing_fy)]
                    if q.qtype == "ratio":
                        calc["args"]["expression"] = f"{_fab(f.total_debt_musd, 0.93)} / {_fab(f.cash_musd, 1.04)}"
                    else:
                        calc["args"]["expression"] = f"{_fab(f.net_income_musd, 0.93)} / {_fab(f.revenue_musd, 1.04)} * 100"
            tr.steps = _run_plan(env, q, plan)
            if calc is not None:
                wrong = next(s.content.get("result") for s in tr.steps if s.kind == "tool_result" and "result" in s.content)
                tr.final_answer = _format_like_gold(q, wrong)
            elif q.gold_value is not None:
                tr.final_answer = _fabricated_answer(q, 0.93)
            else:
                tr.final_answer = _fabricated_text_answer(q, by_key)

        elif mode == "loop":
            plan = copy.deepcopy(q.gold_plan)
            first_get = next(i for i, p in enumerate(plan) if p["tool"] == "get_section")
            plan = plan[:first_get + 1] + [plan[first_get]] * 3 + plan[first_get + 1:]
            tr.steps = _run_plan(env, q, plan)
            tr.final_answer = _clean_answer(q)

        elif mode == "premature_termination":
            plan = [p for p in q.gold_plan if p["tool"] == "search_filings"]
            tr.steps = _run_plan(env, q, plan)
            if q.gold_value is not None:
                tr.final_answer = _fabricated_answer(q, 1.08)
            else:
                tr.final_answer = _fabricated_text_answer(q, by_key)

        elif mode == "arithmetic_error":
            plan = copy.deepcopy(q.gold_plan)
            for p in plan:
                if p["tool"] == "calculate":
                    p["args"]["expression"] = _swap_operands(p["args"]["expression"])
            tr.steps = _run_plan(env, q, plan)
            wrong = next(s.content.get("result") for s in tr.steps if s.kind == "tool_result" and "result" in s.content)
            tr.final_answer = _format_like_gold(q, wrong)

        else:
            raise ValueError(mode)

        tr.steps.append(Step("final_answer", tr.final_answer))
        trajs.append(tr)
    return trajs


# ---- helpers -----------------------------------------------------------------

def _q_fy(q: Question) -> str:
    return q.required_sources[0]["fiscal_year"]


def _metric_attr(q: Question) -> str:
    text = q.text.lower()
    for name, attr in (("net income", "net_income_musd"), ("revenue", "revenue_musd"), ("total debt", "total_debt_musd"),
                       ("cash and equivalents", "cash_musd"), ("employee", "employees")):
        if name in text:
            return attr
    return "revenue_musd"


def _metric_value(q: Question, by_key, fy: str) -> float:
    t = q.required_sources[0]["ticker"]
    return getattr(by_key[(t, fy)], _metric_attr(q))


def _recompute_expression(q: Question, by_key, fy: str) -> str:
    t = q.required_sources[0]["ticker"]
    f = by_key[(t, fy)]
    if q.qtype == "ratio":
        return f"{f.total_debt_musd} / {f.cash_musd}"
    if q.qtype == "margin":
        return f"{f.net_income_musd} / {f.revenue_musd} * 100"
    return "0"


def _answer_for_year(q: Question, by_key, fy: str) -> str:
    t = q.required_sources[0]["ticker"]
    f = by_key[(t, fy)]
    if q.qtype == "lookup":
        v = getattr(f, _metric_attr(q))
        return f"{v:,} employees" if _metric_attr(q) == "employees" else f"{v:,.1f} USD million"
    if q.qtype == "ratio":
        return f"{f.total_debt_musd / f.cash_musd:.2f}x"
    if q.qtype == "margin":
        return f"{f.net_income_musd / f.revenue_musd * 100:.1f}%"
    if q.qtype == "risk":
        return f.risk_factors[0]
    if q.qtype == "compare":
        a, b = q.required_sources[0]["ticker"], q.required_sources[1]["ticker"]
        fa, fb = by_key[(a, fy)], by_key[(b, fy)]
        attr = _metric_attr(q)
        va, vb = getattr(fa, attr), getattr(fb, attr)
        w = fa if va > vb else fb
        return f"{w.company} ({max(va, vb):,.1f} vs {min(va, vb):,.1f} USD million)"
    return q.gold_answer


def _fabricated_answer(q: Question, mult: float) -> str:
    v = _fab(q.gold_value, mult)
    if q.qtype == "lookup":
        if "employee" in q.text:
            return f"{int(v):,} employees"
        return f"{v:,.1f} USD million"
    if q.qtype == "yoy_change":
        return f"{v:+.1f}%"
    if q.qtype == "ratio":
        return f"{v:.2f}x"
    if q.qtype == "margin":
        return f"{v:.1f}%"
    return str(v)


def _fabricated_text_answer(q: Question, by_key) -> str:
    if q.qtype == "risk":
        t, fy = q.required_sources[0]["ticker"], q.required_sources[0]["fiscal_year"]
        return by_key[(t, fy)].risk_factors[-1]  # the last-listed risk, presented as the top one
    if q.qtype == "compare":
        a, b = q.required_sources[0]["ticker"], q.required_sources[1]["ticker"]
        fy = q.required_sources[0]["fiscal_year"]
        fa, fb = by_key[(a, fy)], by_key[(b, fy)]
        attr = _metric_attr(q)
        va, vb = getattr(fa, attr), getattr(fb, attr)
        loser = fb if va > vb else fa  # name the wrong company
        return f"{loser.company} ({_fab(max(va, vb), 1.05):,.1f} vs {_fab(min(va, vb), 0.95):,.1f} USD million)"
    return "Unable to determine."


def _unsupported_extra(q: Question, by_key, rng: random.Random) -> str:
    t = q.required_sources[0]["ticker"]
    f = by_key[(t, q.required_sources[0]["fiscal_year"])]
    choices = [
        f"This was driven by a {rng.randint(9, 23)}% increase in volumes in the {list(f.segments)[0]} segment.",
        f"Management guided to USD {_fab(f.revenue_musd, 1.12):,.0f} million of revenue next year.",
        f"The company also repurchased USD {rng.randint(40, 180)} million of shares during the year.",
        f"Analyst consensus had expected a figure roughly {rng.randint(3, 9)}% lower.",
    ]
    return rng.choice(choices)


def _swap_operands(expr: str) -> str:
    # "(b - a) / a * 100" -> "(b - a) / b * 100" ; "x / y" -> "y / x" ; "ni / rev * 100" -> "rev / ni * 100"
    if expr.startswith("("):
        inner, tail = expr[1:].split(")", 1)
        b, a = [s.strip() for s in inner.split("-")]
        return f"({b} - {a}) / {b} * 100"
    parts = expr.split("/")
    if len(parts) == 2:
        left, right = parts[0].strip(), parts[1].strip()
        if "*" in right:
            r, mult = [s.strip() for s in right.split("*")]
            return f"{r} / {left} * {mult}"
        return f"{right} / {left}"
    return expr


def _format_like_gold(q: Question, v: float) -> str:
    if q.qtype == "yoy_change":
        return f"{v:+.1f}%"
    if q.qtype == "ratio":
        return f"{v:.2f}x"
    if q.qtype == "margin":
        return f"{v:.1f}%"
    return str(v)
