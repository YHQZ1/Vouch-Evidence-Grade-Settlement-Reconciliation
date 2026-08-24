"""Evaluation-only contracts and harness for Vouch.

This package is deliberately outside :mod:`app`.  Runtime code may not import
it, synthetic-data code, or ground-truth artifacts.
"""

from evaluation.agent_metrics import AgentOperationalMetrics, score_agent_runs
from evaluation.contracts import EvaluationReport, FractionMetric

__all__ = [
    "AgentOperationalMetrics",
    "EvaluationReport",
    "FractionMetric",
    "score_agent_runs",
]
