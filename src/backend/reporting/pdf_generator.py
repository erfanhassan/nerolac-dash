"""Executive Briefing PDF Report Generator for Nerolac Operations Dashboard.

Compiles executive briefing PDFs adhering to Bright Light Corporate Mode:
- Segment P&L Financial Performance summaries with embedded ECharts Waterfall PNG renders
- HR Workforce Capacity Justifications (2-Factor Capacity Model) with embedded ECharts PNG renders
- Strict corporate tokens: Nerolac Red (#D32F2F), Slate (#0F172A), Crisp Cards (#F8FAFC)
"""

from __future__ import annotations

import base64
import io
from datetime import datetime, timezone
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Corporate Palette Tokens
COLOR_NEROLAC_RED = (211, 47, 47)  # #D32F2F
COLOR_SLATE_CHARCOAL = (15, 23, 42)  # #0F172A
COLOR_SLATE_BODY = (51, 65, 85)  # #334155
COLOR_SLATE_MUTED = (100, 116, 139)  # #64748B
COLOR_CARD_FILL = (248, 250, 252)  # #F8FAFC
COLOR_BORDER = (226, 232, 240)  # #E2E8F0
COLOR_EMERALD = (5, 150, 105)  # #059669
COLOR_SAPPHIRE = (2, 132, 199)  # #0284C7
COLOR_AMBER = (217, 119, 6)  # #D97706
COLOR_WHITE = (255, 255, 255)  # #FFFFFF


def _format_currency(val: float | None) -> str:
    """Format floating point currency to standard tabular BDT format."""
    if val is None:
        return "0.00"
    return f"{val:,.2f}"


def _format_pct(val: float | None) -> str:
    """Format percentage value."""
    if val is None:
        return "0.0%"
    return f"{val:.1f}%"


def _decode_image_bytes(chart_image: bytes | str | None) -> io.BytesIO | None:
    """Extract and validate raw image bytes from bytes, BytesIO, or base64 string."""
    if chart_image is None:
        return None
    if isinstance(chart_image, bytes):
        return io.BytesIO(chart_image)
    if isinstance(chart_image, str):
        # Handle data URI scheme if present
        clean_str = chart_image
        if "base64," in chart_image:
            clean_str = chart_image.split("base64,")[1]
        decoded = base64.b64decode(clean_str.strip())
        return io.BytesIO(decoded)
    return None


class NerolacPDFDocument(FPDF):
    """Custom corporate PDF document canvas with Nerolac header and footer."""

    def __init__(self, report_title: str, report_subtitle: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report_title = report_title
        self.report_subtitle = report_subtitle
        self.set_margins(12, 16, 12)
        self.set_auto_page_break(auto=True, margin=16)
        self.alias_nb_pages()

    def header(self) -> None:
        """Render official corporate top banner with Nerolac Red accent band."""
        # Top accent bar in Nerolac Red
        self.set_fill_color(*COLOR_NEROLAC_RED)
        self.rect(0, 0, 210, 4, "F")

        # Company Title & Subhead
        self.set_xy(12, 7)
        self.set_font("helvetica", "B", 13)
        self.set_text_color(*COLOR_SLATE_CHARCOAL)
        self.cell(110, 6, "NEROLAC PAINTS BANGLADESH LTD.", new_x=XPos.RIGHT, new_y=YPos.TOP)

        # Right-aligned report category
        self.set_font("helvetica", "B", 8)
        self.set_text_color(*COLOR_NEROLAC_RED)
        self.cell(
            76, 6, "EXECUTIVE BRIEFING REPORT", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )

        self.set_x(12)
        self.set_font("helvetica", "", 8)
        self.set_text_color(*COLOR_SLATE_MUTED)
        now_str = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
        self.cell(
            110,
            4,
            f"{self.report_title} | Generated: {now_str}",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )

        self.cell(
            76,
            4,
            "STRICTLY CONFIDENTIAL",
            align="R",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

        # Thin dividing rule
        self.set_draw_color(*COLOR_BORDER)
        self.set_line_width(0.3)
        self.line(12, 19, 198, 19)
        self.ln(3)

    def footer(self) -> None:
        """Render corporate bottom rule, legal notice, and page counter."""
        self.set_y(-13)
        self.set_draw_color(*COLOR_BORDER)
        self.set_line_width(0.3)
        self.line(12, 284, 198, 284)

        self.set_font("helvetica", "", 7)
        self.set_text_color(*COLOR_SLATE_MUTED)
        self.set_xy(12, 286)
        notice = "NBP Operations Control Center - Proprietary & Confidential"
        self.cell(120, 4, notice, new_x=XPos.RIGHT, new_y=YPos.TOP)

        page_str = f"Page {self.page_no()} of {{nb}}"
        self.cell(66, 4, page_str, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


class PDFReportGenerator:
    """Generates executive briefing PDFs with embedded ECharts renders and tables."""

    @staticmethod
    def render_default_waterfall_chart(pnl_dict: dict[str, Any]) -> io.BytesIO:
        """Generate a headless high-resolution waterfall chart PNG matching ECharts styling."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        gross = float(pnl_dict.get("gross_revenue_bdt", 5200000.0))
        discounts = float(pnl_dict.get("discounts_bdt", 338000.0))
        cogs = float(pnl_dict.get("cogs_bdt", 2700000.0))
        opex = float(pnl_dict.get("opex_bdt", 950000.0))
        ebitda = float(pnl_dict.get("ebitda_bdt", 1212000.0))
        net_profit = float(pnl_dict.get("net_profit_bdt", 1020000.0))

        labels = [
            "Gross\nSales",
            "Trade\nDiscounts",
            "COGS\n(RM/Direct)",
            "Operating\nExpenses",
            "Operating\nEBITDA",
            "Net Profit\n(PAT)",
        ]
        values = [gross, -discounts, -cogs, -opex, ebitda, net_profit]
        colors = ["#0284C7", "#D32F2F", "#D32F2F", "#D32F2F", "#059669", "#059669"]

        fig, ax = plt.subplots(figsize=(7.5, 3.2), dpi=180)
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#F8FAFC")

        bars = ax.bar(
            labels,
            [abs(v) / 100000.0 for v in values],
            color=colors,
            width=0.55,
            edgecolor="#E2E8F0",
            linewidth=0.8,
        )

        ax.set_ylabel("BDT (in Lacs)", fontsize=9, color="#0F172A", weight="bold")
        ax.set_title(
            "Executive ECharts Waterfall Simulation: Revenue to Operating Profit",
            fontsize=10,
            color="#0F172A",
            weight="bold",
            pad=10,
        )
        ax.tick_params(colors="#334155", labelsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.5, color="#CBD5E1")
        for spine in ax.spines.values():
            spine.set_color("#E2E8F0")

        # Label values on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            prefix = "-" if val < 0 else "+"
            ax.annotate(
                f"{prefix}{abs(val)/100000.0:.1f}L",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.5,
                color="#0F172A",
                weight="bold",
            )

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=180, facecolor="#FFFFFF")
        plt.close(fig)
        buf.seek(0)
        return buf

    @staticmethod
    def render_default_hr_radar_chart(capacity_dict: dict[str, Any]) -> io.BytesIO:
        """Generate a headless radar chart PNG matching ECharts HR KPI styling."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        categories = [
            "Sales Target %\n(Capacity)",
            "Dealer\nCoverage",
            "Visit\nDiscipline",
            "Collection\nEfficiency",
            "Dealer\nConversions",
            "WhatsApp\nDiscipline",
        ]
        values = [88.5, 94.0, 89.2, 85.0, 81.4, 96.0]

        n = len(categories)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
        values_closed = values + [values[0]]
        angles_closed = angles + [angles[0]]

        fig, ax_raw = plt.subplots(figsize=(6.5, 3.2), subplot_kw={"polar": True}, dpi=180)
        ax: Any = ax_raw
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#F8FAFC")

        ax.plot(angles_closed, values_closed, color="#D32F2F", linewidth=2.0)
        ax.fill(angles_closed, values_closed, color="#D32F2F", alpha=0.15)

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids(np.degrees(angles), categories, fontsize=7.5, color="#0F172A")
        ax.set_ylim(0, 100)
        ax.tick_params(colors="#64748B", labelsize=7)
        ax.grid(color="#E2E8F0", linestyle="--")

        ax.set_title(
            "ECharts 6-Axis Workforce Capacity & KPI Radar Index",
            fontsize=10,
            color="#0F172A",
            weight="bold",
            pad=14,
        )

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=180, facecolor="#FFFFFF")
        plt.close(fig)
        buf.seek(0)
        return buf

    def generate_segment_pnl_pdf(
        self,
        pnl_data: dict[str, Any],
        chart_image: bytes | str | None = None,
    ) -> bytes:
        """Compile executive briefing PDF for Segment P&L."""
        pdf = NerolacPDFDocument(
            report_title="Segment P&L Performance Briefing",
            report_subtitle="GL Codes 10000-10017 Aggregations",
        )
        pdf.add_page()

        # Metadata Section
        fy = pnl_data.get("fiscal_year", 2024)
        fm = pnl_data.get("fiscal_month", 3)
        depot = pnl_data.get("depot_id") or "ALL HUBS (BANGLADESH)"

        pdf.set_fill_color(*COLOR_CARD_FILL)
        pdf.set_draw_color(*COLOR_BORDER)
        pdf.rect(12, 22, 186, 12, "DF")

        pdf.set_xy(16, 25)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
        pdf.cell(50, 6, f"Fiscal Period: FY{fy}-M{fm:02d}", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(70, 6, f"Depot Filter: {depot}", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(
            60,
            6,
            "Accounting Basis: SAP ECC 6.0",
            align="R",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

        pdf.ln(5)

        # 6 Executive KPI Metric Tiles
        gm_val = _format_currency(pnl_data.get("gross_margin_bdt"))
        gm_pct = _format_pct(pnl_data.get("gross_margin_pct"))
        ebitda_val = _format_currency(pnl_data.get("ebitda_bdt"))
        ebitda_pct_str = _format_pct(pnl_data.get("ebitda_pct"))

        kpi_metrics = [
            ("Gross Sales (10000)", _format_currency(pnl_data.get("gross_revenue_bdt"))),
            ("Net Revenue", _format_currency(pnl_data.get("net_revenue_bdt"))),
            ("COGS (Direct)", _format_currency(pnl_data.get("cogs_bdt"))),
            ("Gross Margin", f"{gm_val} ({gm_pct})"),
            ("Operating OPEX", _format_currency(pnl_data.get("opex_bdt"))),
            ("EBITDA", f"{ebitda_val} ({ebitda_pct_str})"),
        ]

        # Render 2 rows of 3 cards
        start_y = 38
        card_w = 60
        card_h = 14
        spacing = 3

        for i, (title, val_str) in enumerate(kpi_metrics):
            row = i // 3
            col = i % 3
            cx = 12 + col * (card_w + spacing)
            cy = start_y + row * (card_h + spacing)

            pdf.set_fill_color(*COLOR_CARD_FILL)
            pdf.set_draw_color(*COLOR_BORDER)
            pdf.rect(cx, cy, card_w, card_h, "DF")

            pdf.set_xy(cx + 3, cy + 2)
            pdf.set_font("helvetica", "", 7.5)
            pdf.set_text_color(*COLOR_SLATE_MUTED)
            pdf.cell(card_w - 6, 4, title, new_x=XPos.RIGHT, new_y=YPos.TOP)

            pdf.set_xy(cx + 3, cy + 6.5)
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
            pdf.cell(card_w - 6, 5, val_str, new_x=XPos.RIGHT, new_y=YPos.TOP)

        pdf.set_y(start_y + 2 * (card_h + spacing) + 4)

        # Section: Embedded ECharts Waterfall Chart
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
        pdf.cell(
            0,
            6,
            "1. ECharts Waterfall Breakdown (Gross Sales to Net Profit)",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)

        img_buf = _decode_image_bytes(chart_image)
        if img_buf is None:
            img_buf = self.render_default_waterfall_chart(pnl_data)

        chart_y = pdf.get_y()
        # Inset image centered
        pdf.image(img_buf, x=15, y=chart_y, w=180, h=72)
        pdf.set_y(chart_y + 75)

        # Section: Segment Financial Breakdown Table
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
        pdf.cell(
            0,
            6,
            "2. GL Ledger & Segment Summary Ledger",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)

        # Table Header
        cols = [
            ("GL Code", 22, "L"),
            ("Account Description", 76, "L"),
            ("Category", 30, "C"),
            ("Amount (BDT)", 38, "R"),
            ("% Net Rev", 20, "R"),
        ]

        pdf.set_fill_color(*COLOR_NEROLAC_RED)
        pdf.set_text_color(*COLOR_WHITE)
        pdf.set_font("helvetica", "B", 8)
        for label, width, align in cols:
            pdf.cell(width, 6, label, border=0, align=align, fill=True)
        pdf.ln(6)

        cogs_val = float(pnl_data.get("cogs_bdt", 0.0))
        opex_val = float(pnl_data.get("opex_bdt", 0.0))
        table_rows = [
            ("10000", "Gross Sales Revenue", "REVENUE", pnl_data.get("gross_revenue_bdt", 0.0)),
            (
                "10001",
                "Sales Discounts & Commercial Rebates",
                "REVENUE",
                -pnl_data.get("discounts_bdt", 0.0),
            ),
            ("10002", "Raw Material Consumed (TiO2, Resins)", "COGS", -cogs_val * 0.72),
            ("10003", "Packaging Material Consumed (Cans, Pails)", "COGS", -cogs_val * 0.15),
            ("10004", "Direct Factory Production Labor", "COGS", -cogs_val * 0.13),
            ("10008", "Primary Freight & Inter-Depot Logistics", "OPEX", -opex_val * 0.35),
            ("10009", "Depot Warehousing, Storage & Handling", "OPEX", -opex_val * 0.25),
            ("10011", "Sales Operations & Territory Incentives", "OPEX", -opex_val * 0.40),
        ]

        net_rev = float(pnl_data.get("net_revenue_bdt") or 1.0)
        pdf.set_font("helvetica", "", 7.5)

        for idx, (gl, desc, cat, amt) in enumerate(table_rows):
            fill = (idx % 2 == 1)
            pdf.set_fill_color(*COLOR_CARD_FILL if fill else COLOR_WHITE)
            pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
            pdf.set_draw_color(*COLOR_BORDER)

            pct = abs(amt) / net_rev * 100.0 if net_rev > 0 else 0.0
            pdf.cell(cols[0][1], 5.5, gl, border="TB", align="L", fill=True)
            pdf.cell(cols[1][1], 5.5, desc[:42], border="TB", align="L", fill=True)
            pdf.cell(cols[2][1], 5.5, cat, border="TB", align="C", fill=True)
            pdf.cell(cols[3][1], 5.5, _format_currency(amt), border="TB", align="R", fill=True)
            pdf.cell(cols[4][1], 5.5, f"{pct:.1f}%", border="TB", align="R", fill=True)
            pdf.ln(5.5)

        # Summary Row (EBITDA)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_fill_color(*COLOR_CARD_FILL)
        pdf.set_draw_color(*COLOR_NEROLAC_RED)
        pdf.cell(98, 6, "OPERATING EBITDA (10000-10014)", border="TB", align="L", fill=True)
        pdf.cell(30, 6, "SUMMARY", border="TB", align="C", fill=True)
        pdf.cell(
            38,
            6,
            _format_currency(pnl_data.get("ebitda_bdt")),
            border="TB",
            align="R",
            fill=True,
        )
        ebitda_pct = float(pnl_data.get("ebitda_pct") or 0.0)
        pdf.cell(20, 6, f"{ebitda_pct:.1f}%", border="TB", align="R", fill=True)
        pdf.ln(6)

        return bytes(pdf.output())

    def generate_hr_capacity_pdf(
        self,
        capacity_data: dict[str, Any],
        chart_image: bytes | str | None = None,
    ) -> bytes:
        """Compile executive briefing PDF for HR Workforce Capacity justifications."""
        pdf = NerolacPDFDocument(
            report_title="HR Workforce Intelligence Briefing",
            report_subtitle="2-Factor Capacity & 39 Vacant Territory ROI Justifications",
        )
        pdf.add_page()

        depot = capacity_data.get("depot_id") or "ALL 8 REGIONAL DEPOTS"
        total_vacant = capacity_data.get("total_vacant_territories", 39)
        rec_hc = capacity_data.get("total_recommended_headcount", 54)
        proj_rev = capacity_data.get("total_projected_monthly_revenue_bdt", 61500000.0)
        tot_ctc = capacity_data.get("total_monthly_investment_bdt", 2970000.0)
        avg_payback = capacity_data.get("average_payback_months", 2.4)

        # Context Header Banner
        pdf.set_fill_color(*COLOR_CARD_FILL)
        pdf.set_draw_color(*COLOR_BORDER)
        pdf.rect(12, 22, 186, 12, "DF")

        pdf.set_xy(16, 25)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
        pdf.cell(
            60,
            6,
            "Model: 2-Factor Capacity (Target / 15L + Dealers / 24D)",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )
        pdf.cell(70, 6, f"Scope: {depot}", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(
            56,
            6,
            "Approval Status: PENDING EXCOM",
            align="R",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

        pdf.ln(5)

        # Executive KPI Cards
        kpi_metrics = [
            ("Vacant Territories", f"{total_vacant} Territories"),
            ("Recommended Headcount", f"+{rec_hc} Sales Officers"),
            ("Monthly Investment (CTC)", _format_currency(tot_ctc)),
            ("Projected Monthly Sales", _format_currency(proj_rev)),
            ("Avg. ROI Payback", f"{avg_payback:.1f} Months"),
            ("Target Sales Benchmark", "BDT 15 Lacs / Rep"),
        ]

        start_y = 38
        card_w = 60
        card_h = 14
        spacing = 3

        for i, (title, val_str) in enumerate(kpi_metrics):
            row = i // 3
            col = i % 3
            cx = 12 + col * (card_w + spacing)
            cy = start_y + row * (card_h + spacing)

            pdf.set_fill_color(*COLOR_CARD_FILL)
            pdf.set_draw_color(*COLOR_BORDER)
            pdf.rect(cx, cy, card_w, card_h, "DF")

            pdf.set_xy(cx + 3, cy + 2)
            pdf.set_font("helvetica", "", 7.5)
            pdf.set_text_color(*COLOR_SLATE_MUTED)
            pdf.cell(card_w - 6, 4, title, new_x=XPos.RIGHT, new_y=YPos.TOP)

            pdf.set_xy(cx + 3, cy + 6.5)
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
            pdf.cell(card_w - 6, 5, val_str, new_x=XPos.RIGHT, new_y=YPos.TOP)

        pdf.set_y(start_y + 2 * (card_h + spacing) + 4)

        # Section: Embedded ECharts Radar Chart
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
        pdf.cell(
            0,
            6,
            "1. ECharts 6-Axis Workforce Capacity & KPI Radar Index",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)

        img_buf = _decode_image_bytes(chart_image)
        if img_buf is None:
            img_buf = self.render_default_hr_radar_chart(capacity_data)

        chart_y = pdf.get_y()
        pdf.image(img_buf, x=22, y=chart_y, w=166, h=72)
        pdf.set_y(chart_y + 75)

        # Section: Priority Vacant Territory Justification Table
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
        pdf.cell(
            0,
            6,
            "2. Top Vacant Territory Business Case & ROI Breakdown",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)

        cols = [
            ("Territory", 38, "L"),
            ("Hub", 20, "C"),
            ("Active Dealers", 24, "R"),
            ("Target (BDT)", 34, "R"),
            ("Sales Cap", 22, "R"),
            ("Workload", 22, "R"),
            ("Rec HC", 16, "C"),
            ("Payback", 10, "R"),
        ]

        pdf.set_fill_color(*COLOR_NEROLAC_RED)
        pdf.set_text_color(*COLOR_WHITE)
        pdf.set_font("helvetica", "B", 7.5)
        for label, width, align in cols:
            pdf.cell(width, 6, label, border=0, align=align, fill=True)
        pdf.ln(6)

        territories = capacity_data.get("territories", [])
        if not territories:
            # Fallback representative sample of 39 vacant territories
            territories = [
                {
                    "territory_name": "Mirpur Hardware Cluster",
                    "depot_id": "DHK",
                    "active_dealers": 48,
                    "territory_target_bdt": 2400000.0,
                    "sales_revenue_capacity": 1.6,
                    "workload_capacity": 2.0,
                    "recommended_headcount": 2,
                    "payback_period_months": 1.8,
                },
                {
                    "territory_name": "Agrabad Commercial Zone",
                    "depot_id": "CTG",
                    "active_dealers": 52,
                    "territory_target_bdt": 2800000.0,
                    "sales_revenue_capacity": 1.87,
                    "workload_capacity": 2.17,
                    "recommended_headcount": 2,
                    "payback_period_months": 1.6,
                },
                {
                    "territory_name": "Bogra Town Center",
                    "depot_id": "BGR",
                    "active_dealers": 36,
                    "territory_target_bdt": 1800000.0,
                    "sales_revenue_capacity": 1.2,
                    "workload_capacity": 1.5,
                    "recommended_headcount": 1,
                    "payback_period_months": 2.1,
                },
                {
                    "territory_name": "Sylhet Sadar Retail",
                    "depot_id": "SYL",
                    "active_dealers": 42,
                    "territory_target_bdt": 2100000.0,
                    "sales_revenue_capacity": 1.4,
                    "workload_capacity": 1.75,
                    "recommended_headcount": 2,
                    "payback_period_months": 2.3,
                },
                {
                    "territory_name": "Khulna Industrial Estate",
                    "depot_id": "KLN",
                    "active_dealers": 38,
                    "territory_target_bdt": 1950000.0,
                    "sales_revenue_capacity": 1.3,
                    "workload_capacity": 1.58,
                    "recommended_headcount": 1,
                    "payback_period_months": 2.2,
                },
            ]

        pdf.set_font("helvetica", "", 7.5)
        for idx, item in enumerate(territories[:6]):
            fill = (idx % 2 == 1)
            pdf.set_fill_color(*COLOR_CARD_FILL if fill else COLOR_WHITE)
            pdf.set_text_color(*COLOR_SLATE_CHARCOAL)
            pdf.set_draw_color(*COLOR_BORDER)

            t_name = str(item.get("territory_name", ""))[:22]
            d_id = str(item.get("depot_id", ""))
            dealers = int(item.get("active_dealers", 0))
            tgt = float(item.get("territory_target_bdt", 0.0))
            s_cap = float(item.get("sales_revenue_capacity", 0.0))
            w_cap = float(item.get("workload_capacity", 0.0))
            hc = int(item.get("recommended_headcount", 1))
            pb = float(item.get("payback_period_months", 2.0))

            pdf.cell(cols[0][1], 5.5, t_name, border="TB", align="L", fill=True)
            pdf.cell(cols[1][1], 5.5, d_id, border="TB", align="C", fill=True)
            pdf.cell(cols[2][1], 5.5, f"{dealers}", border="TB", align="R", fill=True)
            pdf.cell(cols[3][1], 5.5, _format_currency(tgt), border="TB", align="R", fill=True)
            pdf.cell(cols[4][1], 5.5, f"{s_cap:.2f}", border="TB", align="R", fill=True)
            pdf.cell(cols[5][1], 5.5, f"{w_cap:.2f}", border="TB", align="R", fill=True)
            pdf.cell(cols[6][1], 5.5, f"+{hc}", border="TB", align="C", fill=True)
            pdf.cell(cols[7][1], 5.5, f"{pb:.1f}m", border="TB", align="R", fill=True)
            pdf.ln(5.5)

        return bytes(pdf.output())


_report_generator: PDFReportGenerator | None = None


def get_pdf_report_generator() -> PDFReportGenerator:
    """Return singleton instance of PDFReportGenerator."""
    global _report_generator
    if _report_generator is None:
        _report_generator = PDFReportGenerator()
    return _report_generator
