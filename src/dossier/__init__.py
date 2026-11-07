"""
Dossier generation and export package.
"""

from src.dossier.generator import EvidenceDossierGenerator
from src.dossier.pdf_exporter import CourtDossierPDFExporter
from src.dossier.multi_entity_dossier import MultiEntityDossierGenerator
from src.dossier.font_loader import register_thai_fonts, resolve_thai_font, shape_thai_text

__all__ = [
    "EvidenceDossierGenerator",
    "CourtDossierPDFExporter",
    "MultiEntityDossierGenerator",
    "register_thai_fonts",
    "resolve_thai_font",
    "shape_thai_text",
]
