'use client';

import React, { useState, useMemo } from 'react';

export interface ParsedSKULineItem {
  sku_id: string;
  sku_name: string;
  unit_of_measure: string;
  quantity: number;
  liters: number;
  unit_price_bdt: number;
  total_value_bdt: number;
}

export interface ParsedCollectionItem {
  payment_method: string;
  amount_bdt: number;
  reference_note?: string | null;
}

export interface ResolvedDealerItem {
  dealer_id: string;
  dealer_code: string;
  trade_name: string;
  depot_id: string;
  depot_name: string;
  confidence_score: number;
  resolution_method: string;
}

export interface WhatsAppMessageRecord {
  raw_id: number;
  waba_message_id: string;
  sender_phone: string;
  sender_name: string;
  received_at: string;
  raw_text: string;
  status: string;
  dealer?: ResolvedDealerItem | null;
  line_items: ParsedSKULineItem[];
  total_sales_bdt: number;
  collections: ParsedCollectionItem[];
  total_collection_bdt: number;
  processing_notes?: string | null;
}

export interface WhatsAppMessageFeedResponse {
  total_messages_today: number;
  parsed_count: number;
  exception_count: number;
  total_reported_sales_bdt: number;
  total_collections_bdt: number;
  messages: WhatsAppMessageRecord[];
}

interface MessageStreamCardsProps {
  data: WhatsAppMessageFeedResponse | null;
  isLoading?: boolean;
  onRefresh?: () => void;
}

export function MessageStreamCards({
  data,
  isLoading = false,
  onRefresh,
}: MessageStreamCardsProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [depotFilter, setDepotFilter] = useState('ALL');

  const depots = useMemo(() => {
    if (!data?.messages) return ['ALL'];
    const unique = Array.from(
      new Set(data.messages.map((m) => m.dealer?.depot_name).filter((d): d is string => Boolean(d)))
    );
    return ['ALL', ...unique.sort()];
  }, [data]);

  const filteredMessages = useMemo(() => {
    if (!data?.messages) return [];

    return data.messages.filter((msg) => {
      // Search filter
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchesRep = msg.sender_name.toLowerCase().includes(q);
        const matchesPhone = msg.sender_phone.includes(q);
        const matchesText = msg.raw_text.toLowerCase().includes(q);
        const matchesDealer =
          msg.dealer?.trade_name.toLowerCase().includes(q) ||
          msg.dealer?.dealer_code.toLowerCase().includes(q);
        const matchesSKU = msg.line_items.some(
          (item) => item.sku_name.toLowerCase().includes(q) || item.sku_id.toLowerCase().includes(q)
        );
        if (!matchesRep && !matchesPhone && !matchesText && !matchesDealer && !matchesSKU) {
          return false;
        }
      }

      // Status filter
      if (statusFilter !== 'ALL' && msg.status !== statusFilter) {
        return false;
      }

      // Depot filter
      if (depotFilter !== 'ALL' && msg.dealer?.depot_name !== depotFilter) {
        return false;
      }

      return true;
    });
  }, [data, searchTerm, statusFilter, depotFilter]);

  const formatCurrency = (val: number) => {
    return `৳${new Intl.NumberFormat('en-BD', { maximumFractionDigits: 0 }).format(val)}`;
  };

  const getStatusBadgeStyle = (status: string) => {
    switch (status) {
      case 'PARSED':
        return {
          bg: '#ECFDF5',
          border: '#A7F3D0',
          text: '#065F46',
          label: 'PARSED & MATCHED',
        };
      case 'EXCEPTION':
        return {
          bg: '#FEF2F2',
          border: '#FECACA',
          text: '#991B1B',
          label: 'DISCREPANCY FLAGGED',
        };
      case 'NEEDS_REVIEW':
        return {
          bg: '#EFF6FF',
          border: '#BFDBFE',
          text: '#1E40AF',
          label: 'NEEDS SUPERVISOR REVIEW',
        };
      default:
        return {
          bg: '#FFFBEB',
          border: '#FDE68A',
          text: '#92400E',
          label: status,
        };
    }
  };

  return (
    <div
      id="whatsapp-stream-section"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      {/* Controls and Stream Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          backgroundColor: '#FFFFFF',
          padding: '16px 20px',
          borderRadius: '8px',
          border: '1px solid #E2E8F0',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: '#059669',
              boxShadow: '0 0 0 3px rgba(5, 150, 105, 0.2)',
            }}
          />
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A' }}>
              Real-Time WhatsApp Ingestion Stream
            </div>
            <div style={{ fontSize: '12px', color: '#64748B' }}>
              Asynchronous Webhook Listener &amp; Banglish Entity Parser (pgvector + RapidFuzz)
            </div>
          </div>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Search */}
          <input
            id="whatsapp-message-search"
            type="text"
            placeholder="Search rep, dealer, SKU, phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              width: '230px',
              backgroundColor: '#FFFFFF',
              color: '#0F172A',
              outline: 'none',
            }}
          />

          {/* Depot filter */}
          <select
            id="whatsapp-depot-filter"
            value={depotFilter}
            onChange={(e) => setDepotFilter(e.target.value)}
            style={{
              padding: '6px 10px',
              fontSize: '12px',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              backgroundColor: '#FFFFFF',
              color: '#0F172A',
              cursor: 'pointer',
            }}
          >
            {depots.map((d) => (
              <option key={d} value={d}>
                {d === 'ALL' ? 'All Regional Depots' : d}
              </option>
            ))}
          </select>

          {/* Status filter */}
          <select
            id="whatsapp-status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              padding: '6px 10px',
              fontSize: '12px',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              backgroundColor: '#FFFFFF',
              color: '#0F172A',
              cursor: 'pointer',
            }}
          >
            <option value="ALL">All Parsing Statuses</option>
            <option value="PARSED">Parsed &amp; Matched</option>
            <option value="EXCEPTION">Discrepancy Flagged</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
          </select>

          {/* Refresh Button */}
          {onRefresh && (
            <button
              id="whatsapp-refresh-feed-btn"
              onClick={onRefresh}
              disabled={isLoading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                color: '#334155',
                backgroundColor: '#F1F5F9',
                border: '1px solid #CBD5E1',
                borderRadius: '4px',
                cursor: isLoading ? 'not-allowed' : 'pointer',
              }}
            >
              {isLoading ? 'Refreshing...' : '↻ Refresh Stream'}
            </button>
          )}
        </div>
      </div>

      {/* Messages Stream Container */}
      <div
        id="whatsapp-message-cards-stream"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))',
          gap: '16px',
        }}
      >
        {filteredMessages.length === 0 ? (
          <div
            style={{
              gridColumn: '1 / -1',
              padding: '48px 24px',
              textAlign: 'center',
              backgroundColor: '#F8FAFC',
              borderRadius: '8px',
              border: '1px dashed #CBD5E1',
              color: '#64748B',
            }}
          >
            {isLoading
              ? 'Loading WhatsApp message stream...'
              : 'No WhatsApp messages match your criteria.'}
          </div>
        ) : (
          filteredMessages.map((msg) => {
            const statusStyle = getStatusBadgeStyle(msg.status);
            return (
              <div
                key={msg.raw_id}
                id={`whatsapp-card-${msg.raw_id}`}
                style={{
                  backgroundColor: '#FFFFFF',
                  borderRadius: '8px',
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden',
                }}
              >
                {/* Card Header */}
                <div
                  style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid #F1F5F9',
                    backgroundColor: '#FAFAFA',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '10px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div
                      style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        backgroundColor: '#25D366',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#FFFFFF',
                        fontWeight: 700,
                        fontSize: '13px',
                      }}
                    >
                      WA
                    </div>
                    <div>
                      <div
                        style={{
                          fontSize: '13px',
                          fontWeight: 700,
                          color: '#0F172A',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        {msg.sender_name}
                      </div>
                      <div
                        style={{
                          fontSize: '11px',
                          color: '#64748B',
                          fontVariantNumeric: 'tabular-nums',
                        }}
                      >
                        {msg.sender_phone} • {msg.received_at}
                      </div>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <span
                    style={{
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '10px',
                      fontWeight: 700,
                      letterSpacing: '0.5px',
                      backgroundColor: statusStyle.bg,
                      color: statusStyle.text,
                      border: `1px solid ${statusStyle.border}`,
                      textTransform: 'uppercase',
                    }}
                  >
                    {statusStyle.label}
                  </span>
                </div>

                {/* Card Body */}
                <div
                  style={{
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '14px',
                    flex: 1,
                  }}
                >
                  {/* Raw Banglish Message Speech Bubble */}
                  <div
                    style={{
                      position: 'relative',
                      backgroundColor: '#F8FAFC',
                      borderLeft: '4px solid #25D366',
                      borderRadius: '0 6px 6px 0',
                      padding: '10px 14px',
                      fontSize: '12px',
                      fontStyle: 'italic',
                      color: '#1E293B',
                      lineHeight: '1.5',
                      boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)',
                    }}
                  >
                    <span
                      style={{
                        position: 'absolute',
                        top: '-8px',
                        left: '10px',
                        backgroundColor: '#25D366',
                        color: '#FFFFFF',
                        fontSize: '9px',
                        fontWeight: 700,
                        padding: '1px 5px',
                        borderRadius: '3px',
                        fontStyle: 'normal',
                      }}
                    >
                      RAW BANGLISH REP TEXT
                    </span>
                    &ldquo;{msg.raw_text}&rdquo;
                  </div>

                  {/* Resolved SAP Dealer Chip */}
                  {msg.dealer && (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        backgroundColor: '#EFF6FF',
                        border: '1px solid #BFDBFE',
                        borderRadius: '6px',
                        gap: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          style={{
                            fontFamily: 'monospace',
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '2px 6px',
                            backgroundColor: '#1E40AF',
                            color: '#FFFFFF',
                            borderRadius: '3px',
                          }}
                        >
                          SAP {msg.dealer.dealer_code}
                        </span>
                        <div>
                          <div style={{ fontSize: '12px', fontWeight: 700, color: '#1E3A8A' }}>
                            {msg.dealer.trade_name}
                          </div>
                          <div style={{ fontSize: '11px', color: '#3B82F6' }}>
                            {msg.dealer.depot_name}
                          </div>
                        </div>
                      </div>

                      {/* Vector Similarity Confidence Badge */}
                      <div style={{ textAlign: 'right' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            color: '#047857',
                            backgroundColor: '#D1FAE5',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontVariantNumeric: 'tabular-nums',
                          }}
                        >
                          {(msg.dealer.confidence_score * 100).toFixed(1)}% match
                        </span>
                        <div style={{ fontSize: '9px', color: '#64748B', marginTop: '2px' }}>
                          pgvector + RapidFuzz
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Extracted SKU Line Items Table */}
                  {msg.line_items.length > 0 && (
                    <div>
                      <div
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          color: '#475569',
                          marginBottom: '6px',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                        }}
                      >
                        Extracted SKUs &amp; Volumes
                      </div>
                      <div
                        style={{
                          border: '1px solid #E2E8F0',
                          borderRadius: '4px',
                          overflow: 'hidden',
                        }}
                      >
                        <table
                          style={{
                            width: '100%',
                            borderCollapse: 'collapse',
                            fontSize: '11px',
                          }}
                        >
                          <thead>
                            <tr
                              style={{
                                backgroundColor: '#F8FAFC',
                                borderBottom: '1px solid #E2E8F0',
                              }}
                            >
                              <th
                                style={{ padding: '6px 8px', textAlign: 'left', color: '#64748B' }}
                              >
                                SKU Name
                              </th>
                              <th
                                style={{ padding: '6px 8px', textAlign: 'right', color: '#64748B' }}
                              >
                                Volume
                              </th>
                              <th
                                style={{ padding: '6px 8px', textAlign: 'right', color: '#64748B' }}
                              >
                                Unit Price
                              </th>
                              <th
                                style={{ padding: '6px 8px', textAlign: 'right', color: '#64748B' }}
                              >
                                Total
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {msg.line_items.map((item, idx) => (
                              <tr
                                key={idx}
                                style={{
                                  borderBottom:
                                    idx === msg.line_items.length - 1
                                      ? 'none'
                                      : '1px solid #F1F5F9',
                                }}
                              >
                                <td
                                  style={{ padding: '6px 8px', color: '#0F172A', fontWeight: 500 }}
                                >
                                  {item.sku_name}
                                </td>
                                <td
                                  style={{
                                    padding: '6px 8px',
                                    textAlign: 'right',
                                    fontWeight: 600,
                                    fontVariantNumeric: 'tabular-nums',
                                    color: '#0F172A',
                                  }}
                                >
                                  {item.liters} L
                                </td>
                                <td
                                  style={{
                                    padding: '6px 8px',
                                    textAlign: 'right',
                                    fontVariantNumeric: 'tabular-nums',
                                    color: '#64748B',
                                  }}
                                >
                                  ৳{item.unit_price_bdt}
                                </td>
                                <td
                                  style={{
                                    padding: '6px 8px',
                                    textAlign: 'right',
                                    fontWeight: 700,
                                    fontVariantNumeric: 'tabular-nums',
                                    color: '#0F172A',
                                  }}
                                >
                                  {formatCurrency(item.total_value_bdt)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Collections Extracted */}
                  {msg.collections.length > 0 && (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        flexWrap: 'wrap',
                        padding: '8px 12px',
                        backgroundColor: '#F5F3FF',
                        border: '1px solid #DDD6FE',
                        borderRadius: '6px',
                      }}
                    >
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          color: '#5B21B6',
                        }}
                      >
                        Collection:
                      </span>
                      {msg.collections.map((col, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            backgroundColor: '#EDE9FE',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            color: '#4C1D95',
                            fontWeight: 600,
                            fontVariantNumeric: 'tabular-nums',
                          }}
                        >
                          <span style={{ fontWeight: 700 }}>{col.payment_method}:</span>
                          <span>{formatCurrency(col.amount_bdt)}</span>
                          {col.reference_note && (
                            <span style={{ fontSize: '10px', color: '#6D28D9' }}>
                              ({col.reference_note})
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Card Footer */}
                <div
                  style={{
                    padding: '10px 16px',
                    borderTop: '1px solid #F1F5F9',
                    backgroundColor: '#FAFAFA',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div style={{ fontSize: '10px', color: '#94A3B8' }}>
                    WABA ID:{' '}
                    <code style={{ fontSize: '9px' }}>{msg.waba_message_id.slice(0, 16)}...</code>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '11px', color: '#64748B' }}>Total Order:</span>
                    <span
                      style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: '#D32F2F',
                        fontVariantNumeric: 'tabular-nums',
                      }}
                    >
                      {formatCurrency(msg.total_sales_bdt)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
