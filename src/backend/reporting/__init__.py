"""Reporting and Document Generation Module for Nerolac Operations Dashboard.

Provides executive briefing PDF generation with embedded ECharts renders
and formatted Excel (.xlsx) exports with accounting formulas.
"""

from __future__ import annotations

from src.backend.reporting.excel_generator import (
    ExcelReportExporter,
    get_excel_report_exporter,
)
from src.backend.reporting.pdf_generator import (
    PDFReportGenerator,
    get_pdf_report_generator,
)

__all__ = [
    "ExcelReportExporter",
    "PDFReportGenerator",
    "get_excel_report_exporter",
    "get_pdf_report_generator",
]
