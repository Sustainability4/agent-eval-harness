"""agenteval: a small harness for rubric-based evaluation of tool-use agent trajectories.

Pipeline:
  corpus  -> questions -> trajectories (simulated or LLM-driven)
          -> human scores (CSV)  +  LLM-as-judge scores (JSON)
          -> agreement statistics (human vs judge, judge vs ground truth)
"""

__version__ = "0.1.0"
