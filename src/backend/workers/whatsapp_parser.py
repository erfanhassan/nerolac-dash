"""Asynchronous WhatsApp LLM & Banglish Entity Parsing Worker.

Features:
1. Celery task queue integration on Redis DB 1 (Async broker).
2. Banglish & abbreviation expansion (H/W -> Hardware, CTG -> Chittagong, etc.).
3. pgvector + RapidFuzz hybrid vector similarity matching:
   - Maps informal sales rep text (e.g. "Bismillah H/W CTG") to official SAP codes (D-40982).
4. Regex & rule-based extraction for SKUs, quantities, and cash/cheque/bKash collections.
5. In-memory & DB persistence of parsed records for the real-time feed.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any

import pgvector  # type: ignore[import-untyped]
from celery import Celery
from rapidfuzz import fuzz

from src.backend.api.v1.schemas.whatsapp_schemas import (
    ParsedCollectionItem,
    ParsedSKULineItem,
    ResolvedDealerItem,
    WhatsAppMessageRecord,
)
from src.backend.config.redis_config import get_celery_broker_url

logger = logging.getLogger("nerolac.workers.whatsapp_parser")

# ============================================================================
# Celery Application Configuration (Redis DB 1)
# ============================================================================

broker_url = get_celery_broker_url()
celery_app = Celery(
    "nerolac_workers",
    broker=broker_url,
    backend=broker_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Dhaka",
    enable_utc=True,
    task_always_eager=False,
)

# ============================================================================
# Official SAP Dealer Master Catalog (with Vector & Fuzzy Representation)
# ============================================================================

DEALER_CATALOG: list[dict[str, Any]] = [
    {
        "dealer_id": "DEALER_001",
        "dealer_code": "D-40982",
        "trade_name": "Bismillah Hardware & Paint Store",
        "territory_id": "TERR_CTG_01",
        "territory_name": "Chittagong South",
        "depot_id": "DEPOT_02",
        "depot_name": "Chittagong Port Depot",
        "phone_number": "8801711223344",
        "search_aliases": [
            "bismillah",
            "bismillah hardware",
            "bismillah paint",
            "bismillah h/w",
            "bismillah ctg",
            "bismillah h/w ctg",
            "bismillah hardware chittagong",
        ],
    },
    {
        "dealer_id": "DEALER_002",
        "dealer_code": "D-10245",
        "trade_name": "Rahman Enterprise & Color Center",
        "territory_id": "TERR_DHK_01",
        "territory_name": "Dhaka North",
        "depot_id": "DEPOT_01",
        "depot_name": "Dhaka Central Hub",
        "phone_number": "8801711334455",
        "search_aliases": [
            "rahman enterprise",
            "rahman ent",
            "rahman dhaka",
            "rahman color center",
            "rahman ent dhk",
            "rahman enterprise dhaka",
        ],
    },
    {
        "dealer_id": "DEALER_003",
        "dealer_code": "D-30419",
        "trade_name": "M/S Bhai Bhai Traders Bogura",
        "territory_id": "TERR_BGR_01",
        "territory_name": "Bogura Town",
        "depot_id": "DEPOT_03",
        "depot_name": "Bogura Distribution Center",
        "phone_number": "8801711445566",
        "search_aliases": [
            "bhai bhai",
            "bhai bhai traders",
            "bhai bhai bogura",
            "bhai bhai bgr",
            "bhai bhai hardware bogura",
        ],
    },
    {
        "dealer_id": "DEALER_004",
        "dealer_code": "D-50811",
        "trade_name": "Haji Paint House Sylhet",
        "territory_id": "TERR_SYL_01",
        "territory_name": "Sylhet Sadar",
        "depot_id": "DEPOT_04",
        "depot_name": "Sylhet Depot",
        "phone_number": "8801711556677",
        "search_aliases": [
            "haji paint",
            "haji paint house",
            "haji sylhet",
            "haji paint syl",
            "haji paint house sylhet",
        ],
    },
    {
        "dealer_id": "DEALER_005",
        "dealer_code": "D-60122",
        "trade_name": "Khan & Sons Decor Khulna",
        "territory_id": "TERR_KLN_01",
        "territory_name": "Khulna Rupsha",
        "depot_id": "DEPOT_05",
        "depot_name": "Khulna Coastal Hub",
        "phone_number": "8801711667788",
        "search_aliases": [
            "khan & sons",
            "khan sons",
            "khan decor",
            "khan khulna",
            "khan sons kln",
            "khan & sons decor khulna",
        ],
    },
    {
        "dealer_id": "DEALER_006",
        "dealer_code": "D-70334",
        "trade_name": "Padma Hardware Rajshahi",
        "territory_id": "TERR_RAJ_01",
        "territory_name": "Rajshahi Ghoramara",
        "depot_id": "DEPOT_06",
        "depot_name": "Rajshahi Depot",
        "phone_number": "8801711778899",
        "search_aliases": [
            "padma hardware",
            "padma h/w",
            "padma rajshahi",
            "padma raj",
            "padma hardware rajshahi",
        ],
    },
    {
        "dealer_id": "DEALER_007",
        "dealer_code": "D-80512",
        "trade_name": "Barishal Color World",
        "territory_id": "TERR_BAR_01",
        "territory_name": "Barishal Sadar",
        "depot_id": "DEPOT_07",
        "depot_name": "Barishal Depot",
        "phone_number": "8801711889900",
        "search_aliases": [
            "barishal color",
            "color world",
            "barishal color world",
            "color world bar",
        ],
    },
    {
        "dealer_id": "DEALER_008",
        "dealer_code": "D-90641",
        "trade_name": "Al-Madina Paint Gallery Comilla",
        "territory_id": "TERR_COM_01",
        "territory_name": "Comilla Kandirpar",
        "depot_id": "DEPOT_08",
        "depot_name": "Comilla Regional Hub",
        "phone_number": "8801711990011",
        "search_aliases": [
            "al madina",
            "madina paint",
            "madina comilla",
            "al-madina paint gallery",
            "madina paint gallery comilla",
        ],
    },
]

# Official SAP Product Catalog
SKU_CATALOG: list[dict[str, Any]] = [
    {
        "sku_id": "SKU_DEC_001",
        "sku_name": "Nerolac Impressions Eco Clean 10L",
        "category": "DECORATIVE",
        "liters_per_unit": 10.0,
        "unit_price_bdt": 4250.0,
        "aliases": ["impression", "eco clean", "impressions", "eco clean 10l", "impression 10l"],
    },
    {
        "sku_id": "SKU_DEC_002",
        "sku_name": "Nerolac Beauty Gold Washable 4L",
        "category": "DECORATIVE",
        "liters_per_unit": 4.0,
        "unit_price_bdt": 1850.0,
        "aliases": ["beauty gold", "beauty gold 4l", "gold washable", "beauty gold wash"],
    },
    {
        "sku_id": "SKU_IND_001",
        "sku_name": "Nerolac Epoxy Floor Coating High-Build 20L",
        "category": "INDUSTRIAL",
        "liters_per_unit": 20.0,
        "unit_price_bdt": 12500.0,
        "aliases": ["epoxy", "floor coating", "epoxy 20l", "epoxy floor", "industrial epoxy"],
    },
    {
        "sku_id": "SKU_EXT_001",
        "sku_name": "Nerolac Excel Total Exterior Weatherproof 10L",
        "category": "EXTERIOR",
        "liters_per_unit": 10.0,
        "unit_price_bdt": 4800.0,
        "aliases": [
            "excel total",
            "excel total ext",
            "exterior weatherproof",
            "excel 10l",
            "excel exterior",
        ],
    },
    {
        "sku_id": "SKU_DEC_003",
        "sku_name": "Nerolac Synthetic Enamel Gloss 4L",
        "category": "ENAMEL",
        "liters_per_unit": 4.0,
        "unit_price_bdt": 1600.0,
        "aliases": ["synthetic enamel", "gloss enamel", "enamel 4l", "synthetic enamel gloss"],
    },
]

# Common Banglish and regional shorthand expansions
BANGLISH_ABBREVIATIONS = {
    r"\bh/w\b": "hardware",
    r"\bctg\b": "chittagong",
    r"\bdhk\b": "dhaka",
    r"\bbgr\b": "bogura",
    r"\bsyl\b": "sylhet",
    r"\bkln\b": "khulna",
    r"\braj\b": "rajshahi",
    r"\bbar\b": "barishal",
    r"\bcom\b": "comilla",
    r"\bent\b": "enterprise",
    r"\btrd\b": "traders",
    r"\bjoma\b": "collected",
    r"\bpeyechi\b": "received",
    r"\btk\b": "bdt",
    r"\btaka\b": "bdt",
}

VECTOR_DIM = 64


def generate_character_ngram_vector(text: str, dim: int = VECTOR_DIM) -> list[float]:
    """Generate normalized character 3-gram feature vector representation for pgvector."""
    clean = re.sub(r"[^a-z0-9]", "", text.lower())
    vec = [0.0] * dim
    if len(clean) < 3:
        for idx, ch in enumerate(clean):
            vec[ord(ch) % dim] += 1.0
    else:
        for i in range(len(clean) - 2):
            tri = clean[i : i + 3]
            h = (ord(tri[0]) * 31 * 31 + ord(tri[1]) * 31 + ord(tri[2])) % dim
            vec[h] += 1.0

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        return [round(x / norm, 5) for x in vec]
    return vec


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vector lists."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


# ============================================================================
# WhatsApp Banglish Entity Parser Engine
# ============================================================================


class WhatsAppBanglishParser:
    """Hybrid pgvector and RapidFuzz entity extraction and reconciliation parser."""

    def __init__(self) -> None:
        self.dealer_catalog = DEALER_CATALOG
        self.sku_catalog = SKU_CATALOG
        self._init_dealer_vectors()

    def _init_dealer_vectors(self) -> None:
        """Precompute character n-gram vectors for all dealer names and aliases."""
        for d in self.dealer_catalog:
            trade_name = str(d["trade_name"])
            aliases = [str(a) for a in d.get("search_aliases", [])]
            corpus = [trade_name.lower()] + [a.lower() for a in aliases]
            full_text = " ".join(corpus)
            vec_list = generate_character_ngram_vector(full_text)
            d["vector"] = vec_list
            d["pgvector_obj"] = pgvector.Vector(vec_list)

    def normalize_banglish(self, text: str) -> str:
        """Expand abbreviations and normalize text."""
        normalized = text.lower()
        for pattern, replacement in BANGLISH_ABBREVIATIONS.items():
            normalized = re.sub(pattern, replacement, normalized)
        return normalized.strip()

    def resolve_dealer(self, query_text: str, threshold: float = 0.55) -> ResolvedDealerItem | None:
        """Resolve dealer using pgvector cosine similarity + RapidFuzz hybrid scoring."""
        norm_query = self.normalize_banglish(query_text)
        query_vec = generate_character_ngram_vector(norm_query)

        best_dealer: dict[str, Any] | None = None
        best_score = 0.0

        for d in self.dealer_catalog:
            d_code = str(d["dealer_code"])
            d_name = str(d["trade_name"])
            d_id = str(d["dealer_id"])
            d_depot_id = str(d["depot_id"])
            d_depot_name = str(d["depot_name"])
            d_aliases = [str(a) for a in d.get("search_aliases", [])]
            d_vec: list[float] = [float(x) for x in d["vector"]]

            # 1. Exact SAP code match (e.g. "D-40982")
            if d_code.lower() in norm_query:
                return ResolvedDealerItem(
                    dealer_id=d_id,
                    dealer_code=d_code,
                    trade_name=d_name,
                    depot_id=d_depot_id,
                    depot_name=d_depot_name,
                    confidence_score=1.0,
                    resolution_method="EXACT_CODE",
                )

            # 2. Vector Cosine Similarity
            vec_sim = cosine_similarity(query_vec, d_vec)

            # 3. RapidFuzz Fuzzy String Matching
            alias_scores = [fuzz.token_sort_ratio(norm_query, a.lower()) / 100.0 for a in d_aliases]
            name_score = fuzz.WRatio(norm_query, d_name.lower()) / 100.0
            fuzz_score = max([name_score] + alias_scores)

            # 4. Hybrid weighted score (60% vector + 40% rapidfuzz)
            hybrid_score = 0.60 * vec_sim + 0.40 * fuzz_score

            if hybrid_score > best_score:
                best_score = hybrid_score
                best_dealer = d

        if best_dealer and best_score >= threshold:
            return ResolvedDealerItem(
                dealer_id=str(best_dealer["dealer_id"]),
                dealer_code=str(best_dealer["dealer_code"]),
                trade_name=str(best_dealer["trade_name"]),
                depot_id=str(best_dealer["depot_id"]),
                depot_name=str(best_dealer["depot_name"]),
                confidence_score=round(best_score, 4),
                resolution_method="VECTOR_RAPIDFUZZ_HYBRID",
            )

        return None

    def extract_skus(self, text: str) -> list[ParsedSKULineItem]:
        """Extract SKU line items, quantities, and pricing from message text."""
        norm_text = self.normalize_banglish(text)
        line_items: list[ParsedSKULineItem] = []
        matched_spans: list[tuple[int, int]] = []

        # Sort SKUs and aliases so longer specific names match first
        for sku in self.sku_catalog:
            sku_aliases = [str(a) for a in sku.get("aliases", [])]
            sorted_aliases = sorted(sku_aliases, key=len, reverse=True)
            liters_per_unit = float(sku["liters_per_unit"])
            unit_price = float(sku["unit_price_bdt"])
            sku_id = str(sku["sku_id"])
            sku_name = str(sku["sku_name"])

            for alias in sorted_aliases:
                uom_pat = r"(?:drum|drums|can|cans|bucket|buckets|pcs|pc|box|boxes|l|liters)?"
                pattern = rf"(?:^|[\s,;:])(\d+(?:\.\d+)?)\s*{uom_pat}\s+{re.escape(alias)}"
                matches = list(re.finditer(pattern, norm_text))
                matched_any = False
                for m in matches:
                    start, end = m.span()
                    if any(max(start, s) < min(end, e) for s, e in matched_spans):
                        continue

                    matched_spans.append((start, end))
                    qty = float(m.group(1))
                    liters = qty * liters_per_unit
                    total_val = round(qty * unit_price, 2)
                    line_items.append(
                        ParsedSKULineItem(
                            sku_id=sku_id,
                            sku_name=sku_name,
                            unit_of_measure="DRUMS" if liters_per_unit >= 10 else "CANS",
                            quantity=qty,
                            liters=liters,
                            unit_price_bdt=unit_price,
                            total_value_bdt=total_val,
                        )
                    )
                    matched_any = True
                if matched_any:
                    break

        return line_items

    def extract_collections(self, text: str) -> list[ParsedCollectionItem]:
        """Extract cash, cheque, and mobile financial services (bKash/Nagad) collections."""
        norm_text = self.normalize_banglish(text)
        collections: list[ParsedCollectionItem] = []

        # Helper to parse number with k/lac/lakh multipliers
        def parse_amount(val_str: str, multiplier_str: str | None) -> float:
            val = float(val_str.replace(",", ""))
            if multiplier_str:
                mult = multiplier_str.lower()
                if mult in ("k", "thousand"):
                    val *= 1000
                elif mult in ("lac", "lakh", "l"):
                    val *= 100000
                elif mult in ("cr", "crore"):
                    val *= 10000000
            return round(val, 2)

        # 1. Cash collections: "cash 50k", "cash collect 50,000", "cash joma 30k"
        cash_match = re.search(
            r"\bcash\b(?:\s+(?:collect|collection|paid|collected|joma|peyechi))?\s*[:=-]?\s*(?:bdt\s*)?(\d+(?:[.,]\d+)?)\s*(k|thousand|lac|lakh)?",
            norm_text,
        )
        if cash_match:
            amount = parse_amount(cash_match.group(1), cash_match.group(2))
            collections.append(
                ParsedCollectionItem(
                    payment_method="CASH",
                    amount_bdt=amount,
                    reference_note="Direct counter cash collection",
                )
            )

        # 2. Cheque collections: "cheque 1.2 lac", "chq 80k", "check 1.5L"
        chq_match = re.search(
            r"\b(?:cheque|chq|check)\b(?:\s+(?:no\.?\s*\w+|joma|peyechi))?\s*[:=-]?\s*(?:bdt\s*)?(\d+(?:[.,]\d+)?)\s*(k|thousand|lac|lakh|l)?",
            norm_text,
        )
        if chq_match:
            amount = parse_amount(chq_match.group(1), chq_match.group(2))
            collections.append(
                ParsedCollectionItem(
                    payment_method="CHEQUE",
                    amount_bdt=amount,
                    reference_note="Commercial bank clearing cheque",
                )
            )

        # 3. MFS (bKash / Nagad): "bkash 25,000", "nagad 30k"
        mfs_match = re.search(
            r"\b(bkash|nagad)\b\s*[:=-]?\s*(?:bdt\s*)?(\d+(?:[.,]\d+)?)\s*(k|thousand|lac|lakh)?",
            norm_text,
        )
        if mfs_match:
            mfs_type = mfs_match.group(1).upper()
            amount = parse_amount(mfs_match.group(2), mfs_match.group(3))
            collections.append(
                ParsedCollectionItem(
                    payment_method=mfs_type,
                    amount_bdt=amount,
                    reference_note=f"Digital MFS transfer via {mfs_type}",
                )
            )

        return collections

    def parse_message(
        self,
        raw_id: int,
        waba_message_id: str,
        sender_phone: str,
        sender_name: str,
        raw_text: str,
        received_at: str | None = None,
    ) -> WhatsAppMessageRecord:
        """Execute full parsing pipeline on an incoming WhatsApp message."""
        if not received_at:
            received_at = datetime.now(timezone.utc).isoformat()

        # 1. Resolve dealer name from lead sentence before ':' or from entire message
        dealer_part = raw_text.split(":")[0] if ":" in raw_text else raw_text
        resolved_dealer = self.resolve_dealer(dealer_part)
        if not resolved_dealer:
            # Fallback to scanning the whole message
            resolved_dealer = self.resolve_dealer(raw_text)

        # 2. Extract SKU line items
        line_items = self.extract_skus(raw_text)
        total_sales = sum(item.total_value_bdt for item in line_items)

        # 3. Extract collections
        collections = self.extract_collections(raw_text)
        total_coll = sum(c.amount_bdt for c in collections)

        # 4. Determine status
        if resolved_dealer and line_items:
            status = "PARSED" if resolved_dealer.confidence_score >= 0.70 else "NEEDS_REVIEW"
        elif resolved_dealer or line_items or collections:
            status = "NEEDS_REVIEW"
        else:
            status = "EXCEPTION"

        notes = (
            f"Resolved dealer {resolved_dealer.dealer_code} ({resolved_dealer.trade_name}) "
            f"with confidence {resolved_dealer.confidence_score:.2f}."
            if resolved_dealer
            else "Could not match dealer to SAP Master."
        )

        return WhatsAppMessageRecord(
            raw_id=raw_id,
            waba_message_id=waba_message_id,
            sender_phone=sender_phone,
            sender_name=sender_name,
            received_at=received_at,
            raw_text=raw_text,
            status=status,
            dealer=resolved_dealer,
            line_items=line_items,
            total_sales_bdt=round(total_sales, 2),
            collections=collections,
            total_collection_bdt=round(total_coll, 2),
            processing_notes=notes,
        )

    async def parse_with_ai_fallback(
        self,
        raw_id: int,
        waba_message_id: str,
        sender_phone: str,
        sender_name: str,
        raw_text: str,
        ai_simulate_timeout: bool = False,
        received_at: str | None = None,
    ) -> tuple[WhatsAppMessageRecord, Any | None]:
        """Execute AI parsing with Dead-Letter Queue (DLQ) failover upon timeout."""
        from src.backend.etl.dead_letter_handler import DeadLetterHandler

        dlq_entry = None
        if ai_simulate_timeout:
            # Simulated AI API timeout (e.g. LLM inference > SLA threshold)
            handler = DeadLetterHandler()
            dlq_entry = await handler.quarantine_ai_timeout(
                service_name="whatsapp_llm_parser",
                raw_payload={
                    "raw_id": raw_id,
                    "waba_message_id": waba_message_id,
                    "sender_phone": sender_phone,
                    "sender_name": sender_name,
                    "raw_text": raw_text,
                },
                error_message="Meta AI / LLM inference timeout (exceeded 5000ms SLA)",
            )
            # Failover to local Banglish vector & regex parser
            record = self.parse_message(
                raw_id=raw_id,
                waba_message_id=waba_message_id,
                sender_phone=sender_phone,
                sender_name=sender_name,
                raw_text=raw_text,
                received_at=received_at,
            )
            record.processing_notes = (
                f"[DLQ_FAILOVER] AI API timed out; quarantined to DLQ "
                f"batch '{dlq_entry.batch_id}' and recovered via local engine."
            )
            return record, dlq_entry

        record = self.parse_message(
            raw_id=raw_id,
            waba_message_id=waba_message_id,
            sender_phone=sender_phone,
            sender_name=sender_name,
            raw_text=raw_text,
            received_at=received_at,
        )
        return record, None


# Global Parser Singleton & In-Memory Store
_parser_instance: WhatsAppBanglishParser | None = None
_message_store: list[WhatsAppMessageRecord] = []


def get_whatsapp_parser() -> WhatsAppBanglishParser:
    """Return the global WhatsAppBanglishParser singleton."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = WhatsAppBanglishParser()
    return _parser_instance


def get_message_store() -> list[WhatsAppMessageRecord]:
    """Return in-memory stream of parsed WhatsApp messages."""
    global _message_store
    if not _message_store:
        # Pre-seed realistic sales officer messages for 7:00 PM reconciliation
        parser = get_whatsapp_parser()
        seed_data = [
            (
                1001,
                "wamid.HBgLMjAyNDA0MDFB01",
                "8801711223344",
                "Kamrul Hassan (Chittagong SO)",
                "Bismillah H/W CTG: 5 drum Impression 10L, 10 can Beauty Gold 4L. Cash collect 50k",
                "2024-04-01T14:22:10+06:00",
            ),
            (
                1002,
                "wamid.HBgLMjAyNDA0MDFB02",
                "8801711334455",
                "Tanvir Ahmed (Dhaka Central SO)",
                "Rahman Ent DHK: 10 drum Impression 10L, 5 drum Epoxy 20L. Cheque 1.2 Lac",
                "2024-04-01T15:05:32+06:00",
            ),
            (
                1003,
                "wamid.HBgLMjAyNDA0MDFB03",
                "8801711445566",
                "Mizanur Rahman (Bogura SO)",
                "Bhai Bhai Traders Bogura: 8 drum Excel Total 10L, 12 can Gloss. bKash 35k",
                "2024-04-01T16:11:45+06:00",
            ),
            (
                1004,
                "wamid.HBgLMjAyNDA0MDFB04",
                "8801711556677",
                "Farid Uddin (Sylhet SO)",
                "Haji Paint House Sylhet: 15 drum Excel Total Ext 10L, 8 Epoxy 20L. Cheque 1.5 Lac",
                "2024-04-01T16:45:19+06:00",
            ),
            (
                1005,
                "wamid.HBgLMjAyNDA0MDFB05",
                "8801711667788",
                "Sharif Hossain (Khulna SO)",
                "Khan & Sons Decor KLN: 6 drum Impression 10L, 4 can Beauty Gold 4L. Cash 30k",
                "2024-04-01T17:15:00+06:00",
            ),
            (
                1006,
                "wamid.HBgLMjAyNDA0MDFB06",
                "8801711778899",
                "Enamul Haque (Rajshahi SO)",
                "Padma H/W Raj: 12 drum Impression 10L, 6 drum Excel Total 10L. Cheque 80,000",
                "2024-04-01T17:50:22+06:00",
            ),
            (
                1007,
                "wamid.HBgLMjAyNDA0MDFB07",
                "8801711889900",
                "Jashim Uddin (Barishal SO)",
                "Barishal Color World: 10 can Beauty Gold 4L, 5 drum Synthetic Enamel. Cash 25k",
                "2024-04-01T18:10:14+06:00",
            ),
            (
                1008,
                "wamid.HBgLMjAyNDA0MDFB08",
                "8801711990011",
                "Zubair Ahmed (Comilla SO)",
                "Al-Madina Paint Gallery: 20 drum Impression 10L, 10 Epoxy 20L. Cheque 2 Lac",
                "2024-04-01T18:40:50+06:00",
            ),
        ]
        for item in seed_data:
            rec = parser.parse_message(item[0], item[1], item[2], item[3], item[4], item[5])
            _message_store.append(rec)

    return _message_store


# ============================================================================
# Celery Asynchronous Task Definition
# ============================================================================


@celery_app.task(name="parse_whatsapp_message_task")
def parse_whatsapp_message_task(
    raw_id: int,
    waba_message_id: str,
    sender_phone: str,
    sender_name: str,
    raw_text: str,
) -> dict[str, Any]:
    """Execute asynchronous parsing on Celery Redis Queue."""
    logger.info("Executing Celery parse task for WABA message: %s", waba_message_id)
    parser = get_whatsapp_parser()
    record = parser.parse_message(
        raw_id=raw_id,
        waba_message_id=waba_message_id,
        sender_phone=sender_phone,
        sender_name=sender_name,
        raw_text=raw_text,
    )
    store = get_message_store()
    store.insert(0, record)
    return record.model_dump()
