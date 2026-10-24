"""Synthetic corpus of fictional company filings.

Every company, number and risk factor here is invented. The corpus is small on
purpose: the point is a fully known ground truth, not realism of scale.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List
import json
import pathlib

FISCAL_YEARS = ["FY2024", "FY2025"]

SECTIONS = ["income_statement", "balance_sheet", "operations", "risk_factors"]


@dataclass
class Filing:
    company: str
    ticker: str
    fiscal_year: str
    sector: str
    revenue_musd: float
    net_income_musd: float
    total_debt_musd: float
    cash_musd: float
    employees: int
    segments: Dict[str, float]  # segment -> revenue share (%)
    risk_factors: List[str] = field(default_factory=list)

    def section_text(self, section: str) -> str:
        fy = self.fiscal_year
        if section == "income_statement":
            return (
                f"{self.company} ({self.ticker}) {fy} income statement. "
                f"Total revenue: USD {self.revenue_musd:,.1f} million. "
                f"Net income: USD {self.net_income_musd:,.1f} million."
            )
        if section == "balance_sheet":
            return (
                f"{self.company} ({self.ticker}) {fy} balance sheet. "
                f"Total debt: USD {self.total_debt_musd:,.1f} million. "
                f"Cash and equivalents: USD {self.cash_musd:,.1f} million."
            )
        if section == "operations":
            segs = "; ".join(f"{k}: {v:.0f}% of revenue" for k, v in self.segments.items())
            return (
                f"{self.company} ({self.ticker}) {fy} operations. "
                f"Employees at year end: {self.employees:,}. Segment mix: {segs}."
            )
        if section == "risk_factors":
            items = " ".join(f"({i + 1}) {r}" for i, r in enumerate(self.risk_factors))
            return f"{self.company} ({self.ticker}) {fy} risk factors, in order of stated priority: {items}"
        raise KeyError(section)

    def to_dict(self):
        return asdict(self)


def build_corpus() -> List[Filing]:
    base = [
        # company, ticker, sector, FY2024 (rev, ni, debt, cash, emp), FY2025 (...), segments, risks FY24, risks FY25
        ("Halvard Energy", "HVE", "Energy",
         (4120.0, 312.5, 1850.0, 640.0, 6200), (4575.0, 388.0, 1720.0, 790.0, 6350),
         {"Upstream": 58, "Refining": 30, "Trading": 12},
         ["Crude price volatility", "Refinery outage risk", "Carbon pricing regulation"],
         ["Carbon pricing regulation", "Crude price volatility", "Refinery outage risk"]),
        ("Meridian Logistics", "MRL", "Industrials",
         (2210.0, 145.0, 980.0, 210.0, 14800), (2065.0, 98.5, 1040.0, 185.0, 14100),
         {"Freight": 70, "Warehousing": 22, "Customs": 8},
         ["Fuel cost pass-through lag", "Port congestion", "Labour disputes"],
         ["Labour disputes", "Fuel cost pass-through lag", "Port congestion"]),
        ("Cobalt Ridge Mining", "CRM", "Materials",
         (1580.0, 220.0, 450.0, 380.0, 3900), (1910.0, 341.0, 420.0, 560.0, 4100),
         {"Cobalt": 64, "Nickel": 28, "Copper": 8},
         ["Battery demand concentration", "Permitting delays", "Water availability"],
         ["Battery demand concentration", "Water availability", "Permitting delays"]),
        ("Northgate Financial", "NGF", "Financials",
         (3340.0, 610.0, 7200.0, 2900.0, 9100), (3520.0, 655.0, 7450.0, 3100.0, 9300),
         {"Retail banking": 45, "Wealth": 35, "Markets": 20},
         ["Credit cycle deterioration", "Deposit outflow", "Model risk in credit scoring"],
         ["Model risk in credit scoring", "Credit cycle deterioration", "Deposit outflow"]),
        ("Verdant Foods", "VRF", "Consumer Staples",
         (5410.0, 402.0, 2300.0, 510.0, 22000), (5690.0, 371.0, 2450.0, 470.0, 22600),
         {"Packaged": 52, "Fresh": 33, "Beverages": 15},
         ["Input cost inflation", "Retailer concentration", "Product recall"],
         ["Retailer concentration", "Input cost inflation", "Product recall"]),
        ("Lumen Semiconductor", "LMS", "Technology",
         (2890.0, 455.0, 300.0, 1250.0, 5100), (3610.0, 702.0, 280.0, 1680.0, 5600),
         {"Data centre": 61, "Automotive": 24, "Consumer": 15},
         ["Export control exposure", "Single-foundry dependency", "Demand cyclicality"],
         ["Single-foundry dependency", "Export control exposure", "Demand cyclicality"]),
        ("Atlas Shipping Benchmarks", "ASB", "Energy Services",
         (640.0, 88.0, 120.0, 95.0, 820), (705.0, 61.0, 140.0, 80.0, 860),
         {"Tanker indices": 55, "Dry bulk indices": 30, "Data licensing": 15},
         ["Index methodology challenge", "Data vendor dependency", "Regulatory benchmark rules"],
         ["Regulatory benchmark rules", "Index methodology challenge", "Data vendor dependency"]),
        ("Pinecrest Healthcare", "PCH", "Healthcare",
         (1975.0, 160.0, 820.0, 300.0, 11200), (2140.0, 201.0, 790.0, 350.0, 11500),
         {"Hospitals": 66, "Diagnostics": 24, "Pharmacy": 10},
         ["Reimbursement rate changes", "Clinician shortage", "Cyber incident"],
         ["Cyber incident", "Reimbursement rate changes", "Clinician shortage"]),
    ]
    filings: List[Filing] = []
    for company, ticker, sector, fy24, fy25, segs, r24, r25 in base:
        for fy, vals, risks in (("FY2024", fy24, r24), ("FY2025", fy25, r25)):
            rev, ni, debt, cash, emp = vals
            filings.append(Filing(company, ticker, fy, sector, rev, ni, debt, cash, emp, dict(segs), list(risks)))
    return filings


def save_corpus(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([f.to_dict() for f in build_corpus()], indent=2))


def load_corpus(path: pathlib.Path | None = None) -> List[Filing]:
    if path is None or not path.exists():
        return build_corpus()
    return [Filing(**d) for d in json.loads(path.read_text())]
