"""
Forensic visual user interface package.
"""

from src.ui.dashboard_generator import ForensicDashboardGenerator
from src.ui.multi_entity_dashboard import MultiEntityDashboardGenerator
from src.ui.victim_dashboard import VictimDashboardGenerator

__all__ = [
    "ForensicDashboardGenerator",
    "MultiEntityDashboardGenerator",
    "VictimDashboardGenerator",
]
