"""
Dossier generation and export package.
"""

from src.dossier.generator import EvidenceDossierGenerator
from src.dossier.pdf_exporter import CourtDossierPDFExporter
from src.dossier.multi_entity_dossier import MultiEntityDossierGenerator
from src.dossier.font_loader import register_thai_fonts, resolve_thai_font, shape_thai_text
from src.dossier.quarto_converter import (
    convert_document,
    is_quarto_installed,
    get_quarto_version,
    QuartoNotInstalledError,
    ensure_docx_reference_template,
)

__all__ = [
    "EvidenceDossierGenerator",
    "CourtDossierPDFExporter",
    "MultiEntityDossierGenerator",
    "register_thai_fonts",
    "resolve_thai_font",
    "shape_thai_text",
    "convert_document",
    "is_quarto_installed",
    "get_quarto_version",
    "QuartoNotInstalledError",
    "ensure_docx_reference_template",
]
