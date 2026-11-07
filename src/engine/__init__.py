"""
Forensic calculation and optimization engine package.
"""

from src.engine.flow_matcher import FlowMatchingEngine
from src.engine.cycle_detector import CycleDetector
from src.engine.behavioral import ForensicBehavioralSignals, SuspicionScoringEngine
from src.engine.victim_tracer import (
    VictimFlowTracer,
    VictimTraceResult,
    DispersalDestination,
    ProportionalClaim,
    slugify_victim_name,
)

__all__ = [
    "FlowMatchingEngine",
    "CycleDetector",
    "ForensicBehavioralSignals",
    "SuspicionScoringEngine",
    "VictimFlowTracer",
    "VictimTraceResult",
    "DispersalDestination",
    "ProportionalClaim",
    "slugify_victim_name",
]
