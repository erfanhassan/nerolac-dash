'use client';

import React, { useState, useMemo } from 'react';

export interface ReconciliationExceptionItem {
  rank: number;
  dealer_code: string;
  dealer_name: string;
  depot_id: string;
  depot_name: string;
  sales_rep_name: string;
  sales_rep_phone: string;
  whatsapp_sales_bdt: number;
  sap_invoiced_sales_bdt: number;
  variance_bdt: number;
  variance_pct: number;
  exception_type: string;
  exception_reason: string;
  action_guidance: string;
}

export interface DepotReconSummary {
  depot_id: string;
  depot_name: string;
  total_whatsapp_bdt: number;
  total_sap_bdt: number;
  variance_bdt: number;
  match_rate_pct: number;
  exception_count: number;
}

export interface DailyReconciliationResponse {
  reconciliation_date: string;
  reconciliation_time_bst: string;
  overall_status: string;
  overall_match_rate_pct: number;
  total_whatsapp_sales_bdt: number;
  total_sap_invoiced_bdt: number;
  net_variance_bdt: number;
  total_exceptions_count: number;
  top_10_exceptions: ReconciliationExceptionItem[];
  depot_summaries: DepotReconSummary[];
}

interface ReconciliationDashboardProps {
  data: DailyReconciliationResponse | null;
  isLoading?: boolean;
  onTriggerRecon?: () => Promise<void>;
}

export function ReconciliationDashboard({
  data,
  isLoading = false,
  onTriggerRecon,
}: ReconciliationDashboardProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDepot, setSelectedDepot] = useState('ALL');
  const [selectedType, setSelectedType] = useState('ALL');
  const [isReconciling, setIsReconciling] = useState(false);
  const [expandedRank, setExpandedRank] = useState<number | null>(null);

  const depots = useMemo(() => {
    if (!data?.depot_summaries) return ['ALL'];
    const names = data.depot_summaries.map((d) => d.depot_name);
    return ['ALL', ...names.sort()];
  }, [data]);

  const exceptionTypes = useMemo(() => {
    if (!data?.top_10_exceptions) return ['ALL'];
    const types = Array.from(new Set(data.top_10_exceptions.map((e) => e.exception_type)));
    return ['ALL', ...types.sort()];
  }, [data]);

  const filteredExceptions = useMemo(() => {
    if (!data?.top_10_exceptions) return [];

    return data.top_10_exceptions.filter((exc) => {
      // Search filter
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchesCode = exc.dealer_code.toLowerCase().includes(q);
        const matchesName = exc.dealer_name.toLowerCase().includes(q);
        const matchesRep = exc.sales_rep_name.toLowerCase().includes(q);
        const matchesDepot = exc.depot_name.toLowerCase().includes(q);
        const matchesReason = exc.exception_reason.toLowerCase().includes(q);
        if (!matchesCode && !matchesName && !matchesRep && !matchesDepot && !matchesReason) {
          return false;
        }
      }

      // Depot filter
      if (selectedDepot !== 'ALL' && exc.depot_name !== selectedDepot) {
        return false;
      }

      // Exception type filter
      if (selectedType !== 'ALL' && exc.exception_type !== selectedType) {
        return false;
      }

      return true;
    });
  }, [data, searchTerm, selectedDepot, selectedType]);

  const formatCurrency = (val: number | undefined) => {
    if (val === undefined || isNaN(val)) return '—';
    return `৳${new Intl.NumberFormat('en-BD', { maximumFractionDigits: 0 }).format(val)}`;
  };

  const handleRunRecon = async () => {
    if (!onTriggerRecon || isReconciling) return;
    setIsReconciling(true);
    try {
      await onTriggerRecon();
    } finally {
      setIsReconciling(false);
    }
  };

  const exportExceptionsCSV = () => {
    if (!data || !filteredExceptions.length) return;

    const headers = [
      'Rank',
      'SAP Dealer Code',
      'Dealer Name',
      'Depot Code',
      'Depot Name',
      'Sales Rep Name',
      'Sales Rep Phone',
      'WhatsApp Sales (BDT)',
      'SAP Invoiced Sales (BDT)',
      'Variance (BDT)',
      'Variance (%)',
      'Exception Type',
      'Diagnosis / Reason',
      'Action Guidance',
    ];

    const rows = filteredExceptions.map((e) => [
      e.rank,
      `"${e.dealer_code}"`,
      `"${e.dealer_name.replace(/"/g, '""')}"`,
      `"${e.depot_id}"`,
      `"${e.depot_name}"`,
      `"${e.sales_rep_name}"`,
      `"${e.sales_rep_phone}"`,
      e.whatsapp_sales_bdt,
      e.sap_invoiced_sales_bdt,
      e.variance_bdt,
      e.variance_pct,
      `"${e.exception_type}"`,
      `"${e.exception_reason.replace(/"/g, '""')}"`,
      `"${e.action_guidance.replace(/"/g, '""')}"`,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    const dateStr = data.reconciliation_date || new Date().toISOString().slice(0, 10);
    link.setAttribute('download', `Nerolac_7PM_Reconciliation_Exceptions_${dateStr}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getExceptionBadge = (type: string) => {
    switch (type) {
      case 'OVER_REPORTED':
        return {
          bg: '#FEF2F2',
          border: '#FECACA',
          text: '#DC2626',
          label: 'OVER-REPORTED (+)',
        };
      case 'UNDER_REPORTED':
        return {
          bg: '#FFFBEB',
          border: '#FDE68A',
          text: '#D97706',
          label: 'UNDER-REPORTED (-)',
        };
      case 'MISSING_WHATSAPP_REPORT':
        return {
          bg: '#F5F3FF',
          border: '#DDD6FE',
          text: '#7C3AED',
          label: 'NO WHATSAPP LOG',
        };
      case 'SAP_INVOICE_PENDING':
        return {
          bg: '#EFF6FF',
          border: '#BFDBFE',
          text: '#2563EB',
          label: 'SAP INVOICE PENDING',
        };
      default:
        return {
          bg: '#F1F5F9',
          border: '#CBD5E1',
          text: '#475569',
          label: type,
        };
    }
  };

  return (
    <div
      id="recon-dashboard-section"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
      }}
    >
      {/* 7:00 PM Engine Header Banner */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          backgroundColor: '#FFFFFF',
          padding: '16px 20px',
          borderRadius: '8px',
          border: '1px solid #E2E8F0',
          borderLeft: '4px solid #D32F2F',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#D32F2F',
                backgroundColor: '#FEE2E2',
                padding: '2px 8px',
                borderRadius: '4px',
                letterSpacing: '0.5px',
              }}
            >
              MODULE 4 ENGINE
            </span>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A' }}>
              7:00 PM SAP Daily Sales Reconciliation Engine
            </div>
          </div>
          <div style={{ fontSize: '12px', color: '#64748B', marginTop: '4px' }}>
            Automated Evening Audit comparing Field Rep WhatsApp Orders vs. SAP S/4HANA Invoiced
            Ledger at 19:00:00 BST.
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              padding: '6px 12px',
              backgroundColor: '#F8FAFC',
              border: '1px solid #E2E8F0',
              borderRadius: '4px',
              fontSize: '11px',
              color: '#334155',
            }}
          >
            Cutoff Schedule:{' '}
            <strong style={{ color: '#0F172A' }}>
              {data?.reconciliation_time_bst || '19:00:00 BST'}
            </strong>
          </div>

          <button
            id="btn-run-recon-now"
            onClick={handleRunRecon}
            disabled={isReconciling || isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              fontSize: '12px',
              fontWeight: 600,
              color: '#FFFFFF',
              backgroundColor: isReconciling ? '#94A3B8' : '#D32F2F',
              border: 'none',
              borderRadius: '4px',
              cursor: isReconciling ? 'not-allowed' : 'pointer',
              boxShadow: '0 1px 2px rgba(211, 47, 47, 0.2)',
            }}
          >
            {isReconciling ? '⚡ Running Audit...' : '⚡ Run 7:00 PM SAP Recon Now'}
          </button>
        </div>
      </div>

      {/* Executive KPI Summary Cards */}
      <div
        id="recon-kpi-summary-cards"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
        }}
      >
        {/* KPI 1: WhatsApp Sales */}
        <div
          id="kpi-total-whatsapp-sales"
          style={{
            backgroundColor: '#FFFFFF',
            padding: '16px 20px',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            borderTop: '3px solid #25D366',
          }}
        >
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: '#64748B',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            WhatsApp Self-Reported Sales
          </div>
          <div
            style={{
              fontSize: '22px',
              fontWeight: 700,
              color: '#0F172A',
              margin: '6px 0 2px 0',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {formatCurrency(data?.total_whatsapp_sales_bdt)}
          </div>
          <div style={{ fontSize: '11px', color: '#059669', fontWeight: 600 }}>
            Field Reps Self-Reported
          </div>
        </div>

        {/* KPI 2: SAP Invoiced */}
        <div
          id="kpi-total-sap-invoiced"
          style={{
            backgroundColor: '#FFFFFF',
            padding: '16px 20px',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            borderTop: '3px solid #1E40AF',
          }}
        >
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: '#64748B',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            SAP Invoiced Sales (7:00 PM)
          </div>
          <div
            style={{
              fontSize: '22px',
              fontWeight: 700,
              color: '#0F172A',
              margin: '6px 0 2px 0',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {formatCurrency(data?.total_sap_invoiced_bdt)}
          </div>
          <div style={{ fontSize: '11px', color: '#1E40AF', fontWeight: 600 }}>
            Official Ledger (VA05 / FAGLL03)
          </div>
        </div>

        {/* KPI 3: Net Variance */}
        <div
          id="kpi-net-variance"
          style={{
            backgroundColor: '#FFFFFF',
            padding: '16px 20px',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            borderTop: '3px solid #D32F2F',
          }}
        >
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: '#64748B',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Net Variance (WhatsApp - SAP)
          </div>
          <div
            style={{
              fontSize: '22px',
              fontWeight: 700,
              color: (data?.net_variance_bdt ?? 0) >= 0 ? '#DC2626' : '#2563EB',
              margin: '6px 0 2px 0',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {(data?.net_variance_bdt ?? 0) >= 0 ? '+' : ''}
            {formatCurrency(data?.net_variance_bdt)}
          </div>
          <div style={{ fontSize: '11px', color: '#64748B' }}>
            {(data?.net_variance_bdt ?? 0) >= 0
              ? 'Net Over-reported in Field'
              : 'Net Under-reported'}
          </div>
        </div>

        {/* KPI 4: Match Rate */}
        <div
          id="kpi-recon-match-rate"
          style={{
            backgroundColor: '#FFFFFF',
            padding: '16px 20px',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            borderTop: '3px solid #059669',
          }}
        >
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: '#64748B',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Overall Match Rate
          </div>
          <div
            style={{
              fontSize: '22px',
              fontWeight: 700,
              color: '#059669',
              margin: '6px 0 2px 0',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {(data?.overall_match_rate_pct ?? 0).toFixed(1)}%
          </div>
          <div style={{ fontSize: '11px', color: '#64748B' }}>Aligned across 8 regional depots</div>
        </div>

        {/* KPI 5: Exception Count */}
        <div
          id="kpi-exception-count"
          style={{
            backgroundColor: '#FFFFFF',
            padding: '16px 20px',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            borderTop: '3px solid #D97706',
          }}
        >
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: '#64748B',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Discrepancies Requiring Action
          </div>
          <div
            style={{
              fontSize: '22px',
              fontWeight: 700,
              color: '#D97706',
              margin: '6px 0 2px 0',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {data?.total_exceptions_count ?? 0}
          </div>
          <div style={{ fontSize: '11px', color: '#64748B' }}>Audit exceptions ranked below</div>
        </div>
      </div>

      {/* Top-10 Exception Table Container */}
      <div
        id="recon-top10-exceptions-container"
        style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '8px',
          border: '1px solid #E2E8F0',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Table Header and Controls */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #E2E8F0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A' }}>
              Top-10 Daily Reconciliation Exceptions (7:00 PM SAP Ledger Audit)
            </div>
            <div style={{ fontSize: '12px', color: '#64748B' }}>
              Variance between WhatsApp self-reported orders and SAP billing at daily cutoff
            </div>
          </div>

          {/* Action Row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {/* Search Input */}
            <input
              id="recon-search-input"
              type="text"
              placeholder="Search dealer, SAP code, rep..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                border: '1px solid #CBD5E1',
                borderRadius: '4px',
                width: '210px',
                backgroundColor: '#FFFFFF',
                color: '#0F172A',
                outline: 'none',
              }}
            />

            {/* Depot Filter */}
            <select
              id="recon-depot-select"
              value={selectedDepot}
              onChange={(e) => setSelectedDepot(e.target.value)}
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
                  {d === 'ALL' ? 'All Depots' : d}
                </option>
              ))}
            </select>

            {/* Exception Type Filter */}
            <select
              id="recon-type-select"
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
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
              <option value="ALL">All Exception Types</option>
              {exceptionTypes
                .filter((t) => t !== 'ALL')
                .map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, ' ')}
                  </option>
                ))}
            </select>

            {/* CSV Export Button */}
            <button
              id="recon-export-csv-btn"
              onClick={exportExceptionsCSV}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                color: '#0F172A',
                backgroundColor: '#F8FAFC',
                border: '1px solid #CBD5E1',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              📥 Export Exceptions (CSV)
            </button>
          </div>
        </div>

        {/* High-Density Exception Table */}
        <div style={{ overflowX: 'auto' }}>
          <table
            id="recon-exceptions-table"
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '12px',
            }}
          >
            <thead>
              <tr style={{ backgroundColor: '#F8FAFC', borderBottom: '1px solid #E2E8F0' }}>
                <th
                  style={{
                    padding: '10px 12px',
                    textAlign: 'center',
                    width: '50px',
                    color: '#64748B',
                  }}
                >
                  Rank
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'left', color: '#64748B' }}>
                  SAP Dealer Code
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'left', color: '#64748B' }}>
                  Dealer Name &amp; Depot
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'left', color: '#64748B' }}>
                  Sales Representative
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'right', color: '#64748B' }}>
                  WhatsApp (BDT)
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'right', color: '#64748B' }}>
                  SAP Invoiced (BDT)
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'right', color: '#64748B' }}>
                  Variance (BDT)
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'right', color: '#64748B' }}>
                  Variance %
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'center', color: '#64748B' }}>
                  Exception Type
                </th>
                <th style={{ padding: '10px 12px', textAlign: 'left', color: '#64748B' }}>
                  Diagnosis &amp; Action
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredExceptions.length === 0 ? (
                <tr>
                  <td
                    colSpan={10}
                    style={{
                      padding: '36px',
                      textAlign: 'center',
                      color: '#64748B',
                    }}
                  >
                    No reconciliation exceptions match your filter criteria.
                  </td>
                </tr>
              ) : (
                filteredExceptions.map((exc) => {
                  const badge = getExceptionBadge(exc.exception_type);
                  const isExpanded = expandedRank === exc.rank;

                  return (
                    <React.Fragment key={exc.rank}>
                      <tr
                        style={{
                          borderBottom: '1px solid #F1F5F9',
                          backgroundColor: isExpanded ? '#F8FAFC' : '#FFFFFF',
                          cursor: 'pointer',
                        }}
                        onClick={() => setExpandedRank(isExpanded ? null : exc.rank)}
                      >
                        {/* Rank */}
                        <td
                          style={{
                            padding: '10px 12px',
                            textAlign: 'center',
                            fontWeight: 700,
                            color: exc.rank <= 3 ? '#DC2626' : '#64748B',
                            fontVariantNumeric: 'tabular-nums',
                          }}
                        >
                          #{exc.rank}
                        </td>

                        {/* SAP Code */}
                        <td style={{ padding: '10px 12px' }}>
                          <span
                            style={{
                              fontFamily: 'monospace',
                              fontWeight: 700,
                              fontSize: '11px',
                              padding: '2px 6px',
                              backgroundColor: '#EFF6FF',
                              border: '1px solid #BFDBFE',
                              borderRadius: '3px',
                              color: '#1E40AF',
                            }}
                          >
                            {exc.dealer_code}
                          </span>
                        </td>

                        {/* Dealer Name & Depot */}
                        <td style={{ padding: '10px 12px' }}>
                          <div style={{ fontWeight: 600, color: '#0F172A' }}>{exc.dealer_name}</div>
                          <div style={{ fontSize: '11px', color: '#64748B' }}>{exc.depot_name}</div>
                        </td>

                        {/* Sales Rep */}
                        <td style={{ padding: '10px 12px' }}>
                          <div style={{ color: '#0F172A', fontWeight: 500 }}>
                            {exc.sales_rep_name}
                          </div>
                          <div
                            style={{
                              fontSize: '11px',
                              color: '#64748B',
                              fontVariantNumeric: 'tabular-nums',
                            }}
                          >
                            {exc.sales_rep_phone}
                          </div>
                        </td>

                        {/* WhatsApp Sales */}
                        <td
                          style={{
                            padding: '10px 12px',
                            textAlign: 'right',
                            fontWeight: 600,
                            fontVariantNumeric: 'tabular-nums',
                            color: '#0F172A',
                          }}
                        >
                          {formatCurrency(exc.whatsapp_sales_bdt)}
                        </td>

                        {/* SAP Invoiced */}
                        <td
                          style={{
                            padding: '10px 12px',
                            textAlign: 'right',
                            fontWeight: 600,
                            fontVariantNumeric: 'tabular-nums',
                            color: '#0F172A',
                          }}
                        >
                          {formatCurrency(exc.sap_invoiced_sales_bdt)}
                        </td>

                        {/* Variance BDT */}
                        <td
                          style={{
                            padding: '10px 12px',
                            textAlign: 'right',
                            fontWeight: 700,
                            fontVariantNumeric: 'tabular-nums',
                            color: exc.variance_bdt > 0 ? '#DC2626' : '#2563EB',
                          }}
                        >
                          {exc.variance_bdt > 0 ? '+' : ''}
                          {formatCurrency(exc.variance_bdt)}
                        </td>

                        {/* Variance % */}
                        <td
                          style={{
                            padding: '10px 12px',
                            textAlign: 'right',
                            fontWeight: 700,
                            fontVariantNumeric: 'tabular-nums',
                            color: Math.abs(exc.variance_pct) > 15 ? '#DC2626' : '#D97706',
                          }}
                        >
                          {exc.variance_pct > 0 ? '+' : ''}
                          {exc.variance_pct.toFixed(1)}%
                        </td>

                        {/* Exception Badge */}
                        <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                          <span
                            style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 700,
                              backgroundColor: badge.bg,
                              color: badge.text,
                              border: `1px solid ${badge.border}`,
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {badge.label}
                          </span>
                        </td>

                        {/* Reason Snippet */}
                        <td style={{ padding: '10px 12px', maxWidth: '240px' }}>
                          <div
                            style={{
                              fontSize: '11px',
                              color: '#334155',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: isExpanded ? 'normal' : 'nowrap',
                            }}
                          >
                            {exc.exception_reason}
                          </div>
                        </td>
                      </tr>

                      {/* Expandable Diagnosis Drawer */}
                      {isExpanded && (
                        <tr style={{ backgroundColor: '#F8FAFC' }}>
                          <td
                            colSpan={10}
                            style={{ padding: '14px 20px', borderBottom: '1px solid #E2E8F0' }}
                          >
                            <div
                              style={{
                                display: 'grid',
                                gridTemplateColumns: '1fr 1fr',
                                gap: '16px',
                                backgroundColor: '#FFFFFF',
                                padding: '12px 16px',
                                borderRadius: '6px',
                                border: '1px solid #E2E8F0',
                              }}
                            >
                              <div>
                                <div
                                  style={{
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    color: '#DC2626',
                                    marginBottom: '4px',
                                  }}
                                >
                                  PRIMARY DISCREPANCY DIAGNOSIS
                                </div>
                                <div
                                  style={{ fontSize: '12px', color: '#1E293B', lineHeight: '1.4' }}
                                >
                                  {exc.exception_reason}
                                </div>
                              </div>
                              <div>
                                <div
                                  style={{
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    color: '#059669',
                                    marginBottom: '4px',
                                  }}
                                >
                                  RECOMMENDED ACTION GUIDANCE
                                </div>
                                <div
                                  style={{ fontSize: '12px', color: '#1E293B', lineHeight: '1.4' }}
                                >
                                  {exc.action_guidance}
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Regional Depot Breakdown Summary Grid */}
      {data?.depot_summaries && data.depot_summaries.length > 0 && (
        <div
          id="recon-depot-breakdown"
          style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            padding: '16px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: '#0F172A' }}>
              8 Regional Depots Reconciliation Performance Breakdown
            </div>
            <div style={{ fontSize: '11px', color: '#64748B' }}>
              Depot ledger alignment at 7:00 PM cutoff
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '12px',
            }}
          >
            {data.depot_summaries.map((depot) => (
              <div
                key={depot.depot_id}
                style={{
                  padding: '12px 14px',
                  backgroundColor: '#F8FAFC',
                  borderRadius: '6px',
                  border: '1px solid #E2E8F0',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <div style={{ fontWeight: 700, fontSize: '12px', color: '#0F172A' }}>
                    {depot.depot_name}
                  </div>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      padding: '1px 6px',
                      borderRadius: '3px',
                      backgroundColor: depot.match_rate_pct >= 90 ? '#D1FAE5' : '#FEF3C7',
                      color: depot.match_rate_pct >= 90 ? '#065F46' : '#92400E',
                    }}
                  >
                    {depot.match_rate_pct.toFixed(1)}% Match
                  </span>
                </div>

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '11px',
                    color: '#64748B',
                  }}
                >
                  <div>
                    WA:{' '}
                    <strong style={{ color: '#0F172A' }}>
                      {formatCurrency(depot.total_whatsapp_bdt)}
                    </strong>
                  </div>
                  <div>
                    SAP:{' '}
                    <strong style={{ color: '#0F172A' }}>
                      {formatCurrency(depot.total_sap_bdt)}
                    </strong>
                  </div>
                </div>

                {/* Progress bar */}
                <div
                  style={{
                    width: '100%',
                    height: '6px',
                    backgroundColor: '#E2E8F0',
                    borderRadius: '3px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(100, depot.match_rate_pct)}%`,
                      height: '100%',
                      backgroundColor: depot.match_rate_pct >= 90 ? '#059669' : '#D97706',
                    }}
                  />
                </div>

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '10px',
                    color: '#64748B',
                  }}
                >
                  <span>
                    Variance:{' '}
                    <strong style={{ color: depot.variance_bdt >= 0 ? '#DC2626' : '#2563EB' }}>
                      {depot.variance_bdt >= 0 ? '+' : ''}
                      {formatCurrency(depot.variance_bdt)}
                    </strong>
                  </span>
                  <span>
                    Exceptions:{' '}
                    <strong style={{ color: '#D97706' }}>{depot.exception_count}</strong>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
