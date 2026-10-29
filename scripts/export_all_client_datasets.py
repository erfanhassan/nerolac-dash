#!/usr/bin/env python3
"""Export Complete Operational Datasets for Nerolac Dashboard.

Generates comprehensive, downloadable CSV files for all 4 operational modules:
1. exports/annual_operating_budget_aop.csv
2. exports/ar_ap_aging_summary.csv
3. exports/invoiced_sales_register.csv
4. exports/warehouse_inventory_stock_mb52.csv
5. exports/procurement_purchase_orders_me2l.csv
6. exports/master_data_skus_and_dealers.csv
7. exports/employee_master_and_kpi_scores.csv
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = REPO_ROOT / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 10 Depots
DEPOTS = [
    ("DEPOT_01", "Dhaka Central Hub", "DHAKA", "Tejgaon Industrial Area, Dhaka"),
    ("DEPOT_02", "Chittagong Port Hub", "CHITTAGONG", "Nasirabad I/A, Chittagong"),
    ("DEPOT_03", "Sylhet Depot", "SYLHET", "Mendibag, Sylhet"),
    ("DEPOT_04", "Bogra Depot", "RAJSHAHI", "Station Road, Bogra"),
    ("DEPOT_05", "Rajshahi Depot", "RAJSHAHI", "Sapura I/A, Rajshahi"),
    ("DEPOT_06", "Khulna Depot", "KHULNA", "Khalishpur, Khulna"),
    ("DEPOT_07", "Mymensingh Depot", "MYMENSINGH", "Maskanda, Mymensingh"),
    ("DEPOT_08", "Comilla Depot", "CHITTAGONG", "Paduar Bazar, Comilla"),
    ("DEPOT_09", "Barisal Depot", "BARISAL", "Rupatali, Barisal"),
    ("DEPOT_10", "Rangpur Depot", "RANGPUR", "Dhap, Rangpur"),
]

# SKUs
SKU_CATALOG = [
    (
        "SKU_DEC_01",
        "DEC_EXT_EXCEL_WHITE",
        "Nerolac Excel Mica Marble Exterior White",
        "DECORATIVE",
        "EXTERIOR_EMULSION",
        "20L",
        7800.00,
        390.00,
    ),
    (
        "SKU_DEC_02",
        "DEC_INT_BEAUTY_GOLD",
        "Nerolac Beauty Gold Washable Interior White",
        "DECORATIVE",
        "INTERIOR_EMULSION",
        "20L",
        6500.00,
        325.00,
    ),
    (
        "SKU_DEC_03",
        "DEC_ENAM_SYN_GLOSS",
        "Nerolac Synthetic Gloss Enamel Signal Red",
        "DECORATIVE",
        "ENAMEL",
        "4L",
        1850.00,
        462.50,
    ),
    (
        "SKU_DEC_04",
        "DEC_PRIM_WATER_BASED",
        "Nerolac Excel Water-Based Primer",
        "DECORATIVE",
        "PRIMER",
        "20L",
        3800.00,
        190.00,
    ),
    (
        "SKU_IND_01",
        "IND_EPOXY_PRIMER_GREY",
        "Nerolac 2K High-Build Epoxy Primer Grey",
        "INDUSTRIAL",
        "EPOXY_COATING",
        "20L",
        9200.00,
        460.00,
    ),
    (
        "SKU_IND_02",
        "IND_PU_TOPCOAT_GLOSS",
        "Nerolac Nerothane Polyurethane Gloss Topcoat",
        "INDUSTRIAL",
        "PU_COATING",
        "20L",
        11500.00,
        575.00,
    ),
    (
        "SKU_IND_03",
        "IND_FLOOR_COAT_GREEN",
        "Nerolac Floor Armor Self-Leveling Green",
        "INDUSTRIAL",
        "FLOOR_COATING",
        "20L",
        10800.00,
        540.00,
    ),
    (
        "SKU_AUTO_01",
        "AUT_REFIN_CLEAR_COAT",
        "Nerolac Carbolac High-Solid 2K Clear Coat",
        "AUTOMOTIVE",
        "AUTO_REFINISH",
        "5L",
        4200.00,
        840.00,
    ),
    (
        "SKU_WOOD_01",
        "WOD_POLY_CLEAR_GLOSS",
        "Nerolac Wonderwood Melamine Polyurethane",
        "WOOD_FINISH",
        "WOOD_COATING",
        "4L",
        2400.00,
        600.00,
    ),
    (
        "SKU_COAT_01",
        "CON_WATERPROOF_SEAL",
        "Nerolac Perma Damp-Stop Waterproofing",
        "CONSTRUCTION",
        "WATERPROOFING",
        "20L",
        5200.00,
        260.00,
    ),
]

# Dealers
DEALERS = [
    (
        "DLR_DHK_001",
        "Bismillah Paint & Hardware",
        "DEPOT_01",
        "Dhaka Sadar",
        "+8801711000001",
        3500000.00,
        1850000.00,
        "PLATINUM",
    ),
    (
        "DLR_DHK_002",
        "Mayer Doa Colors Center",
        "DEPOT_01",
        "Mirpur",
        "+8801711000002",
        2500000.00,
        1420000.00,
        "GOLD",
    ),
    (
        "DLR_DHK_003",
        "Al-Madina Traders",
        "DEPOT_01",
        "Uttara",
        "+8801711000003",
        2000000.00,
        950000.00,
        "GOLD",
    ),
    (
        "DLR_CTG_001",
        "Karnaphuli Paint House",
        "DEPOT_02",
        "Agrabad",
        "+8801811000001",
        4000000.00,
        2650000.00,
        "PLATINUM",
    ),
    (
        "DLR_CTG_002",
        "Chattogram Hardware Store",
        "DEPOT_02",
        "Chawkbazar",
        "+8801811000002",
        2200000.00,
        1100000.00,
        "GOLD",
    ),
    (
        "DLR_SYL_001",
        "Surma Paint Palace",
        "DEPOT_03",
        "Zindabazar",
        "+8801911000001",
        1800000.00,
        920000.00,
        "SILVER",
    ),
    (
        "DLR_BOG_001",
        "North Bengal Color Agency",
        "DEPOT_04",
        "Satmatha",
        "+8801711000004",
        1900000.00,
        1050000.00,
        "SILVER",
    ),
    (
        "DLR_RAJ_001",
        "Padma Paint Distributors",
        "DEPOT_05",
        "Shaheb Bazar",
        "+8801711000005",
        2100000.00,
        1300000.00,
        "GOLD",
    ),
    (
        "DLR_KHU_001",
        "Rupsha Color World",
        "DEPOT_06",
        "Dakbangla",
        "+8801611000001",
        2000000.00,
        1180000.00,
        "SILVER",
    ),
    (
        "DLR_MYM_001",
        "Brahmaputra Paint Gallery",
        "DEPOT_07",
        "Choto Bazar",
        "+8801911000002",
        1700000.00,
        890000.00,
        "SILVER",
    ),
    (
        "DLR_COM_001",
        "Gomti Paint Supply",
        "DEPOT_08",
        "Kandirpar",
        "+8801811000003",
        2200000.00,
        1250000.00,
        "GOLD",
    ),
    (
        "DLR_BAR_001",
        "Kirtankhola Hardware",
        "DEPOT_09",
        "Sadars Road",
        "+8801611000002",
        1500000.00,
        780000.00,
        "SILVER",
    ),
    (
        "DLR_RNG_001",
        "Teesta Paint & Varnishes",
        "DEPOT_10",
        "Jahaj Company",
        "+8801711000006",
        1600000.00,
        840000.00,
        "SILVER",
    ),
]


def export_annual_operating_budget():
    """1. Annual Operating Plan (AOP) Budget by Depot and Fiscal Month."""
    filepath = EXPORTS_DIR / "annual_operating_budget_aop.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "budget_id",
                "fiscal_year",
                "fiscal_month",
                "calendar_period",
                "depot_id",
                "depot_name",
                "target_gross_revenue_bdt",
                "target_trade_discount_bdt",
                "target_net_revenue_bdt",
                "budgeted_cogs_bdt",
                "budgeted_gross_margin_bdt",
                "budgeted_opex_bdt",
                "budgeted_ebitda_bdt",
                "budgeted_nopat_bdt",
                "approved_by",
            ]
        )

        bid = 1000
        for yr in [2024, 2025]:
            for mo in range(1, 13):
                cal_period = f"{yr}-{mo:02d}"
                # Base growth trend
                growth_factor = 1.0 + (yr - 2024) * 0.12 + (mo * 0.015)
                for did, dname, _, _ in DEPOTS:
                    bid += 1
                    base_rev = (
                        32_000_000.0
                        * growth_factor
                        * (1.3 if did == "DEPOT_01" else (1.15 if did == "DEPOT_02" else 0.85))
                    )
                    disc = base_rev * 0.055
                    net_rev = base_rev - disc
                    cogs = net_rev * 0.62
                    gm = net_rev - cogs
                    opex = net_rev * 0.22
                    ebitda = gm - opex
                    nopat = ebitda * 0.725  # Corporate tax 27.5%

                    writer.writerow(
                        [
                            bid,
                            yr,
                            mo,
                            cal_period,
                            did,
                            dname,
                            round(base_rev, 2),
                            round(disc, 2),
                            round(net_rev, 2),
                            round(cogs, 2),
                            round(gm, 2),
                            round(opex, 2),
                            round(ebitda, 2),
                            round(nopat, 2),
                            "Executive Board / CFO Nerolac",
                        ]
                    )
    print(f"✓ Exported: {filepath} ({filepath.stat().st_size:,} bytes)")


def export_ar_ap_aging_summary():
    """2. AR (Receivables) and AP (Payables) Aging Summary."""
    filepath = EXPORTS_DIR / "ar_ap_aging_summary.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "aging_id",
                "entry_type",
                "entity_code",
                "entity_name",
                "depot_id",
                "depot_name",
                "current_amount_bdt",
                "days_1_30_bdt",
                "days_31_60_bdt",
                "days_61_90_bdt",
                "days_90_plus_bdt",
                "total_outstanding_bdt",
                "credit_limit_bdt",
                "risk_rating",
                "dso_or_dpo_days",
                "as_of_date",
            ]
        )

        aid = 500
        # AR - Dealers
        for did, trade_name, depot_id, district, _, cr_lim, cur_bal, tier in DEALERS:
            aid += 1
            dep_name = next(d[1] for d in DEPOTS if d[0] == depot_id)
            c_amt = cur_bal * 0.40
            d1_30 = cur_bal * 0.35
            d31_60 = cur_bal * 0.15
            d61_90 = cur_bal * 0.07
            d90_plus = cur_bal * 0.03
            risk = "CRITICAL" if d90_plus > 50000 else ("HIGH" if d61_90 > 100000 else "LOW")
            writer.writerow(
                [
                    aid,
                    "RECEIVABLE",
                    did,
                    trade_name,
                    depot_id,
                    dep_name,
                    round(c_amt, 2),
                    round(d1_30, 2),
                    round(d31_60, 2),
                    round(d61_90, 2),
                    round(d90_plus, 2),
                    round(cur_bal, 2),
                    round(cr_lim, 2),
                    risk,
                    42.5,
                    "2026-10-27",
                ]
            )

        # AP - Suppliers
        SUPPLIERS = [
            ("VND_CHEM_01", "Chemours Singapore Pte", "DEPOT_01", 18500000.0, 30000000.0),
            ("VND_BASF_01", "BASF Bangladesh Ltd", "DEPOT_01", 14200000.0, 25000000.0),
            ("VND_WACK_01", "Wacker Polymers Malaysia", "DEPOT_02", 9800000.0, 20000000.0),
            ("VND_EGYP_01", "Al-Ahram Extenders Egypt", "DEPOT_02", 6400000.0, 15000000.0),
            ("VND_BNGL_01", "Bengal Packaging Ltd", "DEPOT_01", 4200000.0, 10000000.0),
            ("VND_ERL_01", "Eastern Refinery Ltd", "DEPOT_02", 7600000.0, 15000000.0),
        ]
        for vid, vname, did, out_bal, cr_lim in SUPPLIERS:
            aid += 1
            dep_name = next(d[1] for d in DEPOTS if d[0] == did)
            c_amt = out_bal * 0.50
            d1_30 = out_bal * 0.35
            d31_60 = out_bal * 0.12
            d61_90 = out_bal * 0.03
            d90_plus = 0.0
            writer.writerow(
                [
                    aid,
                    "PAYABLE",
                    vid,
                    vname,
                    did,
                    dep_name,
                    round(c_amt, 2),
                    round(d1_30, 2),
                    round(d31_60, 2),
                    round(d61_90, 2),
                    round(d90_plus, 2),
                    round(out_bal, 2),
                    round(cr_lim, 2),
                    "LOW",
                    38.0,
                    "2026-10-27",
                ]
            )
    print(f"✓ Exported: {filepath} ({filepath.stat().st_size:,} bytes)")


def export_invoiced_sales_register():
    """3. Invoiced Sales Register (VA05 / Billing Document Ledger)."""
    filepath = EXPORTS_DIR / "invoiced_sales_register.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "invoice_number",
                "billing_date",
                "fiscal_year",
                "fiscal_month",
                "depot_id",
                "depot_name",
                "dealer_id",
                "dealer_name",
                "sku_code",
                "sku_name",
                "category",
                "quantity_liters",
                "unit_price_bdt",
                "gross_amount_bdt",
                "discount_bdt",
                "net_revenue_bdt",
                "sap_billing_doc_type",
                "payment_status",
            ]
        )

        inv_id = 900000
        start_date = date(2025, 1, 1)
        end_date = date(2025, 12, 31)
        curr = start_date

        while curr <= end_date:
            # 8-12 daily invoice lines across depots
            for _ in range(10):
                inv_id += 1
                dep = random.choice(DEPOTS)
                dlr = random.choice([d for d in DEALERS if d[2] == dep[0]] or [DEALERS[0]])
                sku = random.choice(SKU_CATALOG)

                liters = random.choice([200, 400, 800, 1200, 2000, 3500])
                unit_price = sku[7]
                gross = liters * unit_price
                disc = gross * (0.05 if dlr[7] == "PLATINUM" else 0.03)
                net = gross - disc

                writer.writerow(
                    [
                        f"INV-SAP-{inv_id}",
                        curr.isoformat(),
                        curr.year,
                        curr.month,
                        dep[0],
                        dep[1],
                        dlr[0],
                        dlr[1],
                        sku[1],
                        sku[2],
                        sku[3],
                        liters,
                        round(unit_price, 2),
                        round(gross, 2),
                        round(disc, 2),
                        round(net, 2),
                        "F2_STANDARD_INVOICE",
                        "SETTLED",
                    ]
                )
            curr += timedelta(days=1)
    print(f"✓ Exported: {filepath} ({filepath.stat().st_size:,} bytes)")


def export_warehouse_inventory_stock():
    """4. Warehouse Inventory Stock (MB52 Raw Materials & Finished Goods)."""
    filepath = EXPORTS_DIR / "warehouse_inventory_stock_mb52.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "material_code",
                "material_name",
                "category",
                "material_type",
                "storage_location",
                "depot_id",
                "depot_name",
                "current_stock_quantity",
                "uom",
                "safety_stock_threshold",
                "reorder_point",
                "unit_valuation_bdt",
                "total_stock_value_bdt",
                "lead_time_days",
                "stockout_risk_status",
                "as_of_date",
            ]
        )

        # Raw Materials
        BOM_RMS = [
            (
                "RM_TIO2_RUTILE",
                "Titanium Dioxide Rutile Grade (R-902+)",
                "TIO2",
                "RAW_MATERIAL",
                42500.0,
                65000.0,
                75000.0,
                385.00,
                35,
                "CRITICAL_STOCKOUT_RISK",
            ),
            (
                "RM_RESIN_ACRYLIC",
                "Pure Acrylic Emulsion Polymer (50% solids)",
                "RESIN",
                "RAW_MATERIAL",
                58000.0,
                85000.0,
                95000.0,
                240.00,
                21,
                "REORDER_REQUIRED",
            ),
            (
                "RM_RESIN_STYRENE",
                "Styrene Acrylic Binder Emulsion",
                "RESIN",
                "RAW_MATERIAL",
                82000.0,
                75000.0,
                80000.0,
                210.00,
                18,
                "HEALTHY_STOCK",
            ),
            (
                "RM_RESIN_EPOXY",
                "Liquid Epoxy Resin (Bisphenol-A)",
                "RESIN",
                "RAW_MATERIAL",
                18200.0,
                32000.0,
                36000.0,
                350.00,
                28,
                "CRITICAL_STOCKOUT_RISK",
            ),
            (
                "RM_SOLVENT_MTO",
                "Mineral Turpentine Oil (High Flash)",
                "SOLVENT",
                "RAW_MATERIAL",
                125000.0,
                110000.0,
                120000.0,
                120.00,
                14,
                "HEALTHY_STOCK",
            ),
            (
                "RM_SOLVENT_XYLENE",
                "Xylene Technical Grade (Aromatic)",
                "SOLVENT",
                "RAW_MATERIAL",
                34000.0,
                48000.0,
                52000.0,
                165.00,
                21,
                "REORDER_REQUIRED",
            ),
            (
                "RM_EXT_CALCIUM_CARB",
                "Precipitated Calcium Carbonate Ultra-Fine",
                "EXTENDER",
                "RAW_MATERIAL",
                210000.0,
                180000.0,
                190000.0,
                42.00,
                10,
                "HEALTHY_STOCK",
            ),
            (
                "RM_EXT_TALC_MICRON",
                "Micronized Talc (L-100 Mesh)",
                "EXTENDER",
                "RAW_MATERIAL",
                95000.0,
                90000.0,
                92000.0,
                56.00,
                12,
                "HEALTHY_STOCK",
            ),
            (
                "PKG_CAN_20L_METAL",
                "20L Nerolac Printed Steel Pail",
                "PACKAGING",
                "PACKAGING_MATERIAL",
                14500.0,
                22000.0,
                25000.0,
                240.00,
                15,
                "REORDER_REQUIRED",
            ),
            (
                "PKG_CAN_4L_METAL",
                "4L Nerolac Printed Metal Can",
                "PACKAGING",
                "PACKAGING_MATERIAL",
                38000.0,
                30000.0,
                32000.0,
                95.00,
                15,
                "HEALTHY_STOCK",
            ),
        ]

        for did, dname, _, _ in DEPOTS:
            for rcode, rname, cat, mtype, cur_stk, safe_stk, rop, ucost, lead, status in BOM_RMS:
                # Factor per depot
                factor = 1.0 if did == "DEPOT_01" else 0.35
                c_stk = round(cur_stk * factor, 1)
                s_stk = round(safe_stk * factor, 1)
                r_stk = round(rop * factor, 1)
                t_val = round(c_stk * ucost, 2)
                st_status = (
                    "CRITICAL_STOCKOUT_RISK"
                    if c_stk < s_stk
                    else ("REORDER_REQUIRED" if c_stk < r_stk else "HEALTHY_STOCK")
                )
                writer.writerow(
                    [
                        rcode,
                        rname,
                        cat,
                        mtype,
                        f"SLOC_{did}_MAIN",
                        did,
                        dname,
                        c_stk,
                        "KG" if "PKG" not in rcode else "PIECES",
                        s_stk,
                        r_stk,
                        ucost,
                        t_val,
                        lead,
                        st_status,
                        "2026-10-27",
                    ]
                )

            # Finished Goods per Depot
            for sku in SKU_CATALOG:
                fg_stk = random.randint(1200, 8500)
                fg_safe = 3000
                fg_rop = 4500
                st_stat = "CRITICAL_STOCKOUT_RISK" if fg_stk < fg_safe else "HEALTHY_STOCK"
                writer.writerow(
                    [
                        sku[0],
                        sku[2],
                        sku[3],
                        "FINISHED_GOODS",
                        f"SLOC_{did}_FG",
                        did,
                        dname,
                        fg_stk,
                        "LITERS",
                        fg_safe,
                        fg_rop,
                        sku[7],
                        round(fg_stk * sku[7], 2),
                        7,
                        st_stat,
                        "2026-10-27",
                    ]
                )
    print(f"✓ Exported: {filepath} ({filepath.stat().st_size:,} bytes)")


def export_procurement_purchase_orders():
    """5. Procurement & Purchase Orders (ME2L Register with Supplier Variances)."""
    filepath = EXPORTS_DIR / "procurement_purchase_orders_me2l.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "po_number",
                "purchase_order_date",
                "delivery_due_date",
                "material_code",
                "material_name",
                "category",
                "supplier_code",
                "supplier_name",
                "destination_depot_id",
                "destination_depot_name",
                "ordered_quantity_kg",
                "unit_price_bdt",
                "contracted_benchmark_price_bdt",
                "price_variance_pct",
                "is_flagged_amber_variance",
                "total_po_value_bdt",
                "po_status",
            ]
        )

        POS = [
            (
                "PO-2026-0891",
                "2026-03-01",
                "2026-04-05",
                "RM_TIO2_RUTILE",
                "Titanium Dioxide Rutile Grade (R-902+)",
                "TIO2",
                "VND_CHEM_01",
                "Chemours Singapore Pte",
                "DEPOT_01",
                "Dhaka Central Hub",
                45000.0,
                365.00,
                365.00,
                0.0,
                False,
                "RELEASED",
            ),
            (
                "PO-2026-0892",
                "2026-03-05",
                "2026-04-10",
                "RM_TIO2_RUTILE",
                "Titanium Dioxide Rutile Grade (R-902+)",
                "TIO2",
                "VND_TRON_01",
                "Tronox Pigments Australia",
                "DEPOT_02",
                "Chittagong Port Hub",
                30000.0,
                392.50,
                365.00,
                7.5,
                True,
                "APPROVED_AMBER",
            ),
            (
                "PO-2026-0893",
                "2026-03-08",
                "2026-03-29",
                "RM_RESIN_ACRYLIC",
                "Pure Acrylic Emulsion Polymer",
                "RESIN",
                "VND_BASF_01",
                "BASF Bangladesh Ltd",
                "DEPOT_01",
                "Dhaka Central Hub",
                60000.0,
                240.00,
                240.00,
                0.0,
                False,
                "IN_TRANSIT",
            ),
            (
                "PO-2026-0894",
                "2026-03-10",
                "2026-03-31",
                "RM_RESIN_ACRYLIC",
                "Pure Acrylic Emulsion Polymer",
                "RESIN",
                "VND_DOW_01",
                "Dow Chemical International",
                "DEPOT_02",
                "Chittagong Port Hub",
                35000.0,
                256.80,
                240.00,
                7.0,
                True,
                "APPROVED_AMBER",
            ),
            (
                "PO-2026-0895",
                "2026-03-12",
                "2026-03-30",
                "RM_RESIN_STYRENE",
                "Styrene Acrylic Binder Emulsion",
                "RESIN",
                "VND_WACK_01",
                "Wacker Polymers Malaysia",
                "DEPOT_02",
                "Chittagong Port Hub",
                50000.0,
                210.00,
                210.00,
                0.0,
                False,
                "IN_TRANSIT",
            ),
            (
                "PO-2026-0896",
                "2026-03-14",
                "2026-04-11",
                "RM_RESIN_EPOXY",
                "Liquid Epoxy Resin (Bisphenol-A)",
                "RESIN",
                "VND_KUMH_01",
                "Kumho P&B Chemicals Korea",
                "DEPOT_01",
                "Dhaka Central Hub",
                25000.0,
                378.00,
                350.00,
                8.0,
                True,
                "APPROVED_AMBER",
            ),
            (
                "PO-2026-0897",
                "2026-03-15",
                "2026-03-29",
                "RM_SOLVENT_MTO",
                "Mineral Turpentine Oil (High Flash)",
                "SOLVENT",
                "VND_ERL_01",
                "Eastern Refinery Ltd",
                "DEPOT_02",
                "Chittagong Port Hub",
                80000.0,
                120.00,
                120.00,
                0.0,
                False,
                "DELIVERED",
            ),
            (
                "PO-2026-0898",
                "2026-03-18",
                "2026-03-28",
                "RM_EXT_CALCIUM_CARB",
                "Precipitated Calcium Carbonate Ultra-Fine",
                "EXTENDER",
                "VND_EGYP_01",
                "Al-Ahram Extenders Egypt",
                "DEPOT_01",
                "Dhaka Central Hub",
                100000.0,
                42.00,
                42.00,
                0.0,
                False,
                "IN_TRANSIT",
            ),
            (
                "PO-2026-0899",
                "2026-03-20",
                "2026-04-05",
                "PKG_CAN_20L_METAL",
                "20L Nerolac Printed Steel Pail",
                "PACKAGING",
                "VND_BNGL_01",
                "Bengal Packaging Ltd",
                "DEPOT_01",
                "Dhaka Central Hub",
                15000.0,
                240.00,
                240.00,
                0.0,
                False,
                "RELEASED",
            ),
            (
                "PO-2026-0900",
                "2026-03-22",
                "2026-04-07",
                "PKG_CAN_20L_METAL",
                "20L Nerolac Printed Steel Pail",
                "PACKAGING",
                "VND_STD_01",
                "Standard Can Makers BD",
                "DEPOT_02",
                "Chittagong Port Hub",
                10000.0,
                255.00,
                240.00,
                6.25,
                True,
                "APPROVED_AMBER",
            ),
        ]

        for po in POS:
            total_val = po[10] * po[11]
            writer.writerow(
                [
                    po[0],
                    po[1],
                    po[2],
                    po[3],
                    po[4],
                    po[5],
                    po[6],
                    po[7],
                    po[8],
                    po[9],
                    po[10],
                    po[11],
                    po[12],
                    po[13],
                    po[14],
                    round(total_val, 2),
                    po[15],
                ]
            )
    print(f"✓ Exported: {filepath} ({filepath.stat().st_size:,} bytes)")


def export_master_data():
    """6. Master Data: SKUs, Dealers, and Regional Depots."""
    filepath = EXPORTS_DIR / "master_data_skus_and_dealers.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "entity_type",
                "entity_id",
                "code",
                "name_or_title",
                "parent_depot_id",
                "parent_depot_name",
                "category_or_tier",
                "sub_category_or_district",
                "pack_or_credit_limit",
                "unit_price_or_balance",
                "active_status",
            ]
        )

        # Depots
        for did, dname, reg, addr in DEPOTS:
            writer.writerow(["DEPOT", did, did, dname, did, dname, reg, addr, "N/A", 0.0, "ACTIVE"])

        # SKUs
        for sku in SKU_CATALOG:
            writer.writerow(
                [
                    "SKU",
                    sku[0],
                    sku[1],
                    sku[2],
                    "ALL_DEPOTS",
                    "National Catalog",
                    sku[3],
                    sku[4],
                    sku[5],
                    sku[6],
                    "ACTIVE",
                ]
            )

        # Dealers
        for dlr in DEALERS:
            dep_name = next(d[1] for d in DEPOTS if d[0] == dlr[2])
            writer.writerow(
                [
                    "DEALER",
                    dlr[0],
                    dlr[0],
                    dlr[1],
                    dlr[2],
                    dep_name,
                    dlr[7],
                    dlr[3],
                    dlr[5],
                    dlr[6],
                    "ACTIVE",
                ]
            )
    print(f"✓ Exported: {filepath} ({filepath.stat().st_size:,} bytes)")


def export_employee_master_and_kpi_scores():
    """7. Employee Master, 39 Vacant Territories, and 6-Axis KPI Scores."""
    filepath = EXPORTS_DIR / "employee_master_and_kpi_scores.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "record_type",
                "employee_or_territory_id",
                "code",
                "full_name_or_territory",
                "designation_or_type",
                "depot_id",
                "depot_name",
                "monthly_target_bdt",
                "sales_kpi_score_30pct",
                "collections_kpi_score_20pct",
                "coverage_kpi_score_15pct",
                "conversion_kpi_score_15pct",
                "reviews_kpi_score_10pct",
                "whatsapp_discipline_score_10pct",
                "composite_kpi_score_100pct",
                "monthly_ctc_bdt",
                "margin_contribution_bdt",
                "quadrant_classification",
            ]
        )

        # 24 Active Officers
        DESIGNATIONS = [
            "Field Sales Officer",
            "Senior Territory Executive",
            "Area Sales Manager",
            "Depot Key Accounts Lead",
        ]
        for i in range(1, 25):
            emp_id = f"EMP_{i:03d}"
            emp_code = f"NR-BD-{1000 + i}"
            names = ["Ashiqur", "Tanvir", "Mahmud", "Nazmul", "Kamrul", "Rezaul"]
            name = f"Executive Officer {i:02d} ({names[i % 6]})"
            desig = DESIGNATIONS[i % len(DESIGNATIONS)]
            dep = DEPOTS[i % len(DEPOTS)]
            target = 1_800_000.0 + (i * 50_000.0)

            # Scores (out of 100)
            s_sales = min(100.0, 75.0 + (i * 1.5))
            s_coll = min(100.0, 70.0 + (i * 1.2))
            s_cov = min(100.0, 80.0 + (i * 0.8))
            s_conv = min(100.0, 72.0 + (i * 1.1))
            s_rev = min(100.0, 85.0 + (i * 0.5))
            s_wa = min(100.0, 90.0 + (i * 0.4))

            # Composite (weights: 30%, 20%, 15%, 15%, 10%, 10%)
            comp = (
                (s_sales * 0.30)
                + (s_coll * 0.20)
                + (s_cov * 0.15)
                + (s_conv * 0.15)
                + (s_rev * 0.10)
                + (s_wa * 0.10)
            )

            ctc = 65_000.0 + (i * 3_500.0)
            margin = target * 0.32

            quadrant = (
                "STARS"
                if comp >= 85 and margin >= 650000
                else (
                    "HEAVY_HITTERS"
                    if margin >= 600000
                    else ("RAMP_UP" if comp >= 75 else "VALUE_DESTROYERS")
                )
            )

            writer.writerow(
                [
                    "ACTIVE_EMPLOYEE",
                    emp_id,
                    emp_code,
                    name,
                    desig,
                    dep[0],
                    dep[1],
                    round(target, 2),
                    round(s_sales, 1),
                    round(s_coll, 1),
                    round(s_cov, 1),
                    round(s_conv, 1),
                    round(s_rev, 1),
                    round(s_wa, 1),
                    round(comp, 1),
                    round(ctc, 2),
                    round(margin, 2),
                    quadrant,
                ]
            )

        # 39 Vacant Territories Capacity Models
        for j in range(1, 40):
            tid = f"TERR_V{j:02d}"
            tcode = f"TR-BD-{200 + j}"
            tname = f"Vacant Territory Area {j:02d}"
            dep = DEPOTS[j % len(DEPOTS)]
            target = 2_200_000.0 + (j * 40_000.0)
            dealers_count = 35 + (j % 25)
            visit_freq = 2.0

            # 2-Factor Capacity
            sales_cap = target / 1_500_000.0  # 15 Lacs standard
            workload_cap = (dealers_count * visit_freq) / 24.0  # 24 days
            combined_req_headcount = max(1, round((sales_cap + workload_cap) / 2))

            writer.writerow(
                [
                    "VACANT_TERRITORY_CAPACITY",
                    tid,
                    tcode,
                    tname,
                    f"Requires {combined_req_headcount} FSO (Dealers: {dealers_count})",
                    dep[0],
                    dep[1],
                    round(target, 2),
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    75_000.0 * combined_req_headcount,
                    round(target * 0.30, 2),
                    "VACANT_UNASSIGNED",
                ]
            )

    print(f"✓ Exported: {filepath} ({filepath.stat().st_size:,} bytes)")


if __name__ == "__main__":
    print("=" * 70)
    print("  NEROLAC DASH: EXPORTING COMPLETE CLIENT DATASETS (ALL 4 MODULES)")
    print("=" * 70)
    export_annual_operating_budget()
    export_ar_ap_aging_summary()
    export_invoiced_sales_register()
    export_warehouse_inventory_stock()
    export_procurement_purchase_orders()
    export_master_data()
    export_employee_master_and_kpi_scores()
    print("=" * 70)
    print("  ALL 7 OPERATIONAL DATASETS EXPORTED SUCCESSFULLY TO /exports/ ✨")
    print("=" * 70)
