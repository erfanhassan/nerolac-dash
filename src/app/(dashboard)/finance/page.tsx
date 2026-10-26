'use client';

import React, { useState, useEffect } from 'react';
import {
  SegmentPnLWaterfallChart,
  WaterfallDataPoint,
} from '@/components/finance/SegmentPnLWaterfallChart';
import { PnLTreeGrid, PnLTreeNode } from '@/components/finance/PnLTreeGrid';
import {
  SupplierVarianceTable,
  SupplierPurchaseRecord,
} from '@/components/finance/SupplierVarianceTable';
import { CashflowSimulator } from '@/components/finance/CashflowSimulator';
import {
  ARAPAgingOverview,
  AgingBucketSummary,
  AgingEntityRecord,
} from '@/components/finance/ARAPAgingOverview';

interface PnLResponse {
  fiscal_year: number;
  fiscal_month: number;
  gross_revenue_bdt: number;
  discounts_bdt: number;
  net_revenue_bdt: number;
  cogs_bdt: number;
  gross_margin_bdt: number;
  gross_margin_pct: number;
  opex_bdt: number;
  ebitda_bdt: number;
  ebitda_pct: number;
  net_profit_bdt: number;
  net_profit_pct: number;
  waterfall_series: WaterfallDataPoint[];
  tree_grid_rows: PnLTreeNode[];
}

interface SupplierVarianceResponse {
  total_materials_evaluated: number;
  flagged_variance_count: number;
  max_variance_pct: number;
  records: SupplierPurchaseRecord[];
}

interface AgingResponse {
  as_of_date: string;
  total_receivables_bdt: number;
  total_payables_bdt: number;
  net_working_capital_bdt: number;
  dso_days: number;
  dpo_days: number;
  buckets: AgingBucketSummary[];
  entity_records: AgingEntityRecord[];
}

export default function FinanceControlCenterPage() {
  const [selectedYear, setSelectedYear] = useState<number>(2024);
  const [selectedMonth, setSelectedMonth] = useState<number>(3);
  const [selectedDepot, setSelectedDepot] = useState<string>('ALL');

  const [pnlData, setPnlData] = useState<PnLResponse | null>(null);
  const [varianceData, setVarianceData] = useState<SupplierVarianceResponse | null>(null);
  const [agingData, setAgingData] = useState<AgingResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchFinanceData = async () => {
    setIsLoading(true);
    try {
      const depotQuery = selectedDepot !== 'ALL' ? `&depot_id=${selectedDepot}` : '';

      // 1. Fetch Segment P&L (GL 10000–10017)
      const pnlPromise = fetch(
        `/api/v1/finance/segment-pnl?fiscal_year=${selectedYear}&fiscal_month=${selectedMonth}${depotQuery}`
      ).then((r) => (r.ok ? r.json() : null));

      // 2. Fetch Supplier Price Variances
      const variancePromise = fetch(
        `/api/v1/finance/supplier-variance${selectedDepot !== 'ALL' ? `?depot_id=${selectedDepot}` : ''}`
      ).then((r) => (r.ok ? r.json() : null));

      // 3. Fetch AR / AP Aging Schedule
      const agingPromise = fetch(
        `/api/v1/finance/ar-ap-aging${selectedDepot !== 'ALL' ? `?depot_id=${selectedDepot}` : ''}`
      ).then((r) => (r.ok ? r.json() : null));

      const [pnlRes, varianceRes, agingRes] = await Promise.all([
        pnlPromise,
        variancePromise,
        agingPromise,
      ]);

      setPnlData(pnlRes);
      setVarianceData(varianceRes);
      setAgingData(agingRes);
    } catch (err) {
      console.error('Failed to load finance control center live feeds:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFinanceData();
  }, [selectedYear, selectedMonth, selectedDepot]);

  const formatBDT = (val: number) => {
    return new Intl.NumberFormat('en-BD', {
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto' }}>
      {/* Page Header and Global Period Filters */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '20px',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '20px',
              fontWeight: 800,
              color: '#0F172A',
              letterSpacing: '-0.3px',
            }}
          >
            Finance Control Center
          </h1>
          <p style={{ fontSize: '13px', color: '#64748B', marginTop: '2px' }}>
            SAP Trial Balances (GL 10000–10017), Supplier Spreads, and Treasury Cash Simulation
          </p>
        </div>

        {/* Global Filter Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '6px',
            padding: '6px 12px',
          }}
        >
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Period:</span>

          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            style={{
              fontSize: '12px',
              padding: '3px 8px',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              backgroundColor: '#FFFFFF',
              color: '#0F172A',
            }}
          >
            <option value={2026}>FY 2026</option>
            <option value={2025}>FY 2025</option>
            <option value={2024}>FY 2024</option>
          </select>

          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(Number(e.target.value))}
            style={{
              fontSize: '12px',
              padding: '3px 8px',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              backgroundColor: '#FFFFFF',
              color: '#0F172A',
            }}
          >
            <option value={1}>Jan</option>
            <option value={2}>Feb</option>
            <option value={3}>Mar (Q1 Close)</option>
            <option value={4}>Apr</option>
            <option value={5}>May</option>
            <option value={6}>Jun (Q2 Close)</option>
          </select>

          <span
            style={{
              width: '1px',
              height: '14px',
              backgroundColor: '#CBD5E1',
              margin: '0 4px',
            }}
          />

          <span style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Depot:</span>
          <select
            value={selectedDepot}
            onChange={(e) => setSelectedDepot(e.target.value)}
            style={{
              fontSize: '12px',
              padding: '3px 8px',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              backgroundColor: '#FFFFFF',
              color: '#0F172A',
            }}
          >
            <option value="ALL">All 8 Bangladesh Depots</option>
            <option value="DEPOT_01">DEPOT_01 - Dhaka Central</option>
            <option value="DEPOT_02">DEPOT_02 - Chittagong</option>
            <option value="DEPOT_03">DEPOT_03 - Sylhet</option>
            <option value="DEPOT_04">DEPOT_04 - Rajshahi</option>
            <option value="DEPOT_05">DEPOT_05 - Khulna</option>
          </select>
        </div>
      </div>

      {/* Top Corporate Metric Tiles */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '12px',
          marginBottom: '20px',
        }}
      >
        {/* Metric 1: Net Revenue */}
        <div className="corporate-card">
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
            Net Sales Revenue (GL 10000–10001)
          </div>
          <div
            id="kpi-net-revenue"
            className="tabular-nums"
            style={{
              fontSize: '20px',
              fontWeight: 800,
              color: '#0F172A',
              marginTop: '4px',
            }}
          >
            {pnlData ? `৳${formatBDT(pnlData.net_revenue_bdt)}` : '...'}
          </div>
          <div style={{ fontSize: '11px', color: '#059669', fontWeight: 600, marginTop: '2px' }}>
            ● Gross Sales: {pnlData ? `৳${formatBDT(pnlData.gross_revenue_bdt)}` : '...'}
          </div>
        </div>

        {/* Metric 2: Gross Margin */}
        <div className="corporate-card">
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
            Gross Contribution Margin
          </div>
          <div
            id="kpi-gross-margin"
            className="tabular-nums"
            style={{
              fontSize: '20px',
              fontWeight: 800,
              color: '#059669',
              marginTop: '4px',
            }}
          >
            {pnlData ? `${pnlData.gross_margin_pct.toFixed(1)}%` : '...'}
          </div>
          <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
            ৳{pnlData ? formatBDT(pnlData.gross_margin_bdt) : '...'} Margin
          </div>
        </div>

        {/* Metric 3: EBITDA Margin */}
        <div className="corporate-card">
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
            Operating EBITDA
          </div>
          <div
            id="kpi-ebitda"
            className="tabular-nums"
            style={{
              fontSize: '20px',
              fontWeight: 800,
              color: '#1E3A8A',
              marginTop: '4px',
            }}
          >
            {pnlData ? `${pnlData.ebitda_pct.toFixed(1)}%` : '...'}
          </div>
          <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
            ৳{pnlData ? formatBDT(pnlData.ebitda_bdt) : '...'} EBITDA
          </div>
        </div>

        {/* Metric 4: Net Working Capital */}
        <div className="corporate-card">
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
            Net Working Capital Gap (AR - AP)
          </div>
          <div
            id="kpi-working-capital"
            className="tabular-nums"
            style={{
              fontSize: '20px',
              fontWeight: 800,
              color: agingData && agingData.net_working_capital_bdt >= 0 ? '#0F172A' : '#D32F2F',
              marginTop: '4px',
            }}
          >
            {agingData ? `৳${formatBDT(agingData.net_working_capital_bdt)}` : '...'}
          </div>
          <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
            DSO: {agingData ? `${agingData.dso_days}d` : '...'} | DPO:{' '}
            {agingData ? `${agingData.dpo_days}d` : '...'}
          </div>
        </div>
      </div>

      {/* 1. Apache ECharts Segment P&L Waterfall & TanStack Tree Grid */}
      <section id="section-segment-pnl">
        <SegmentPnLWaterfallChart
          data={pnlData ? pnlData.waterfall_series : []}
          isLoading={isLoading}
        />

        <PnLTreeGrid data={pnlData ? pnlData.tree_grid_rows : []} isLoading={isLoading} />
      </section>

      {/* 2. Real-Time Cash Flow Scenario Simulator */}
      <section id="section-cashflow-simulator">
        <CashflowSimulator />
      </section>

      {/* 3. Raw Material Supplier Price Variance Analysis */}
      <section id="section-supplier-variance">
        <SupplierVarianceTable
          records={varianceData ? varianceData.records : []}
          flaggedCount={varianceData ? varianceData.flagged_variance_count : 0}
          totalEvaluated={varianceData ? varianceData.total_materials_evaluated : 0}
          isLoading={isLoading}
        />
      </section>

      {/* 4. AR / AP Aging & Working Capital Overview */}
      <section id="section-ar-ap-aging">
        <ARAPAgingOverview
          totalAR={agingData ? agingData.total_receivables_bdt : 0}
          totalAP={agingData ? agingData.total_payables_bdt : 0}
          netWorkingCapital={agingData ? agingData.net_working_capital_bdt : 0}
          dso={agingData ? agingData.dso_days : 0}
          dpo={agingData ? agingData.dpo_days : 0}
          buckets={agingData ? agingData.buckets : []}
          entities={agingData ? agingData.entity_records : []}
          isLoading={isLoading}
        />
      </section>
    </div>
  );
}
