"""The three tools an agent may call, with a deterministic environment.

Tool results are plain dicts so trajectories serialise cleanly. Errors are
returned as {"error": ...}, never raised, because how an agent handles a
tool error is one of the things we evaluate.
"""
from __future__ import annotations

import ast
import operator
from typing import Any, Dict, List

from .corpus import Filing, SECTIONS

TOOL_SPECS = [
    {
        "name": "search_filings",
        "description": "Find filings by company name or ticker. Returns matching (company, ticker, fiscal_year) entries.",
        "parameters": {"query": "string: company name or ticker"},
    },
    {
        "name": "get_section",
        "description": "Return the text of one section of one filing.",
        "parameters": {
            "ticker": "string",
            "fiscal_year": "string: FY2024 or FY2025",
            "section": "one of income_statement, balance_sheet, operations, risk_factors",
        },
    },
    {
        "name": "calculate",
        "description": "Evaluate an arithmetic expression with + - * / and parentheses. Returns a number.",
        "parameters": {"expression": "string"},
    },
]


class Environment:
    def __init__(self, filings: List[Filing], flaky: Dict[str, int] | None = None):
        self.filings = filings
        self.by_key = {(f.ticker, f.fiscal_year): f for f in filings}
        # flaky: {ticker: n} -> first n get_section calls for that ticker return a transient error
        self.flaky = dict(flaky or {})
        self.calls: List[Dict[str, Any]] = []

    # ---- tools -----------------------------------------------------------
    def search_filings(self, query: str) -> Dict[str, Any]:
        q = (query or "").strip().lower()
        hits = [
            {"company": f.company, "ticker": f.ticker, "fiscal_year": f.fiscal_year}
            for f in self.filings
            if q and (q in f.company.lower() or q == f.ticker.lower())
        ]
        return {"results": hits}

    def get_section(self, ticker: str, fiscal_year: str, section: str) -> Dict[str, Any]:
        if self.flaky.get(ticker, 0) > 0:
            self.flaky[ticker] -= 1
            return {"error": "transient_error: filing service unavailable, retry"}
        f = self.by_key.get((ticker, fiscal_year))
        if f is None:
            return {"error": f"not_found: no filing for {ticker} {fiscal_year}"}
        if section not in SECTIONS:
            return {"error": f"bad_section: {section}"}
        return {"ticker": ticker, "fiscal_year": fiscal_year, "section": section, "text": f.section_text(section)}

    def calculate(self, expression: str) -> Dict[str, Any]:
        try:
            return {"result": _safe_eval(expression)}
        except Exception as e:  # noqa: BLE001
            return {"error": f"calc_error: {e}"}

    # ---- dispatch --------------------------------------------------------
    def call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        fn = {"search_filings": self.search_filings, "get_section": self.get_section, "calculate": self.calculate}.get(name)
        if fn is None:
            out = {"error": f"unknown_tool: {name}"}
        else:
            try:
                out = fn(**args)
            except TypeError as e:
                out = {"error": f"bad_arguments: {e}"}
        self.calls.append({"tool": name, "args": args, "result": out})
        return out


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.USub: operator.neg}


def _safe_eval(expr: str) -> float:
    node = ast.parse(expr, mode="eval").body

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("unsupported expression")

    return round(float(ev(node)), 6)
