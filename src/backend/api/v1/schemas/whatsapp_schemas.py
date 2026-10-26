"""Pydantic v2 Schemas for Module 4: WhatsApp Field Intelligence & 7:00 PM SAP Recon.

Contracts for:
1. Meta WhatsApp Webhook Ingestion & Handshake
2. Real-time Parsed WhatsApp Message Stream
3. 7:00 PM Daily Reconciliation & Top-10 Exception Lists
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# 1. Meta WhatsApp Webhook Ingestion Schemas
# ============================================================================


class MetaWebhookTextMessage(BaseModel):
    """WhatsApp text message body."""

    body: str = Field(..., description="Raw text sent by sales officer in Banglish")


class MetaWebhookMessageItem(BaseModel):
    """Single WhatsApp message payload from Meta Cloud API."""

    model_config = ConfigDict(extra="ignore")

    from_number: str = Field(..., alias="from", description="Sender WhatsApp phone number")
    id: str = Field(..., description="Unique WABA message ID (e.g. wamid.HBgL...)")
    timestamp: str = Field(..., description="Unix epoch timestamp as string")
    type: str = Field("text", description="Message type (text, audio, image)")
    text: MetaWebhookTextMessage | None = Field(None, description="Text message container")


class MetaWebhookContact(BaseModel):
    """Contact profile details."""

    model_config = ConfigDict(extra="ignore")

    profile: dict[str, str] = Field(default_factory=dict)
    wa_id: str = Field(..., description="WhatsApp user ID")


class MetaWebhookValue(BaseModel):
    """Inner payload value from Meta Webhook event."""

    model_config = ConfigDict(extra="ignore")

    messaging_product: str = Field("whatsapp", description="Product identifier")
    metadata: dict[str, Any] = Field(default_factory=dict)
    contacts: list[MetaWebhookContact] = Field(default_factory=list)
    messages: list[MetaWebhookMessageItem] = Field(default_factory=list)


class MetaWebhookChange(BaseModel):
    """Change item in Meta Webhook entry."""

    model_config = ConfigDict(extra="ignore")

    value: MetaWebhookValue
    field: str = Field("messages", description="Event field")


class MetaWebhookEntry(BaseModel):
    """Entry wrapper in Meta Webhook payload."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="WhatsApp Business Account ID")
    changes: list[MetaWebhookChange] = Field(default_factory=list)


class MetaWebhookPayload(BaseModel):
    """Root Meta WhatsApp Webhook event payload."""

    model_config = ConfigDict(extra="ignore")

    object: str = Field("whatsapp_business_account", description="Meta object type")
    entry: list[MetaWebhookEntry] = Field(default_factory=list)


class WebhookIngestResponse(BaseModel):
    """Immediate HTTP 200 OK acknowledgement response."""

    status: str = Field("ok", description="Status code")
    message: str = Field("EVENT_RECEIVED", description="Meta acknowledgement message")
    waba_message_ids: list[str] = Field(default_factory=list, description="Ingested message IDs")
    queued_task_ids: list[str] = Field(default_factory=list, description="Celery async task IDs")


# ============================================================================
# 2. Parsed WhatsApp Entity & Message Stream Schemas
# ============================================================================


class ParsedSKULineItem(BaseModel):
    """Extracted SKU and quantity line item."""

    sku_id: str = Field(..., description="Matched SKU Master Code (e.g. SKU_DEC_001)")
    sku_name: str = Field(..., description="Human-readable SKU name")
    unit_of_measure: str = Field("LITERS", description="LITERS, DRUMS, CANS")
    quantity: float = Field(..., description="Parsed quantity in UoM")
    liters: float = Field(..., description="Standardized volume in Liters")
    unit_price_bdt: float = Field(..., description="List price per liter/unit in BDT")
    total_value_bdt: float = Field(..., description="Total line item revenue in BDT")


class ParsedCollectionItem(BaseModel):
    """Extracted payment collection record."""

    payment_method: str = Field(..., description="CASH, CHEQUE, BKASH, NAGAD, BANK_TRANSFER")
    amount_bdt: float = Field(..., description="Collected amount in BDT")
    reference_note: str | None = Field(None, description="Bank / cheque notes if mentioned")


class ResolvedDealerItem(BaseModel):
    """Fuzzy/vector resolved SAP Dealer Master record."""

    dealer_id: str = Field(..., description="Internal DB UUID or key")
    dealer_code: str = Field(..., description="Official SAP Dealer Master Code (e.g. D-40982)")
    trade_name: str = Field(..., description="Official registered trade name")
    depot_id: str = Field(..., description="Assigned SAP regional depot (e.g. DEPOT_02)")
    depot_name: str = Field(..., description="Depot title (e.g. Chittagong Port Depot)")
    confidence_score: float = Field(..., description="Resolution confidence (0.00 to 1.00)")
    resolution_method: str = Field(
        "VECTOR_RAPIDFUZZ_HYBRID",
        description="Resolution engine: VECTOR_RAPIDFUZZ_HYBRID, EXACT_CODE, FUZZY_NAME",
    )


class WhatsAppMessageRecord(BaseModel):
    """Enriched WhatsApp message record for dashboard feed."""

    raw_id: int = Field(..., description="Internal database ID")
    waba_message_id: str = Field(..., description="Meta unique message ID")
    sender_phone: str = Field(..., description="Sales officer phone number")
    sender_name: str = Field("Sales Officer", description="Sales officer name")
    received_at: str = Field(..., description="ISO 8601 timestamp in Asia/Dhaka")
    raw_text: str = Field(..., description="Original raw Banglish message")
    status: str = Field(
        ...,
        description="Status: RECEIVED, PROCESSING, PARSED, EXCEPTION, NEEDS_REVIEW",
    )
    dealer: ResolvedDealerItem | None = Field(None, description="Resolved SAP Dealer")
    line_items: list[ParsedSKULineItem] = Field(default_factory=list, description="Extracted SKUs")
    total_sales_bdt: float = Field(0.0, description="Total self-reported sales amount in BDT")
    collections: list[ParsedCollectionItem] = Field(
        default_factory=list, description="Extracted collections"
    )
    total_collection_bdt: float = Field(0.0, description="Total collected amount in BDT")
    processing_notes: str | None = Field(None, description="Parser telemetry & extraction notes")


class WhatsAppMessageFeedResponse(BaseModel):
    """Real-time message feed response for dashboard view."""

    total_messages_today: int = Field(..., description="Total WhatsApp messages received today")
    parsed_count: int = Field(..., description="Successfully parsed messages count")
    exception_count: int = Field(..., description="Messages requiring supervisor review")
    total_reported_sales_bdt: float = Field(..., description="Aggregate self-reported sales in BDT")
    total_collections_bdt: float = Field(..., description="Aggregate collections in BDT")
    messages: list[WhatsAppMessageRecord] = Field(..., description="Sequential message feed cards")


# ============================================================================
# 3. 7:00 PM Daily Sales Reconciliation Schemas
# ============================================================================


class ReconciliationExceptionItem(BaseModel):
    """Top-10 exception item comparing WhatsApp vs. SAP billing."""

    rank: int = Field(..., description="Exception severity rank (1 to 10)")
    dealer_code: str = Field(..., description="Official SAP Dealer Master Code (e.g. D-40982)")
    dealer_name: str = Field(..., description="Registered trade name")
    depot_id: str = Field(..., description="Regional depot code")
    depot_name: str = Field(..., description="Regional depot name")
    sales_rep_name: str = Field(..., description="Assigned Field Officer")
    sales_rep_phone: str = Field(..., description="Officer phone number")
    whatsapp_sales_bdt: float = Field(
        ..., description="Self-reported sales amount on WhatsApp in BDT"
    )
    sap_invoiced_sales_bdt: float = Field(
        ..., description="Official SAP invoiced sales amount in BDT"
    )
    variance_bdt: float = Field(..., description="Variance (WhatsApp - SAP) in BDT")
    variance_pct: float = Field(..., description="Percentage variance vs SAP")
    exception_type: str = Field(
        ...,
        description="OVER_REPORTED, UNDER_REPORTED, MISSING_WHATSAPP_REPORT, SAP_INVOICE_PENDING",
    )
    exception_reason: str = Field(..., description="Detailed audit diagnosis")
    action_guidance: str = Field(..., description="Recommended management action")


class DepotReconSummary(BaseModel):
    """Depot-level daily reconciliation breakdown."""

    depot_id: str
    depot_name: str
    total_whatsapp_bdt: float
    total_sap_bdt: float
    variance_bdt: float
    match_rate_pct: float
    exception_count: int


class DailyReconciliationResponse(BaseModel):
    """Complete 7:00 PM Daily Reconciliation Dashboard response."""

    reconciliation_date: str = Field(..., description="Reconciliation Date (YYYY-MM-DD)")
    reconciliation_time_bst: str = Field(
        "19:00:00 BST", description="Scheduled execution timestamp"
    )
    overall_status: str = Field(
        ..., description="RECONCILED, BALANCED_WITH_EXCEPTIONS, VARIANCE_FLAGGED"
    )
    overall_match_rate_pct: float = Field(
        ..., description="Percentage of sales volume perfectly matched"
    )
    total_whatsapp_sales_bdt: float = Field(
        ..., description="Total self-reported sales across all depots in BDT"
    )
    total_sap_invoiced_bdt: float = Field(
        ..., description="Total SAP invoiced revenue across all depots in BDT"
    )
    net_variance_bdt: float = Field(..., description="Net variance (WhatsApp - SAP) in BDT")
    total_exceptions_count: int = Field(..., description="Count of flagged discrepancies")
    top_10_exceptions: list[ReconciliationExceptionItem] = Field(
        ..., description="Top 10 highest-variance exceptions"
    )
    depot_summaries: list[DepotReconSummary] = Field(..., description="Summary across all 8 depots")
