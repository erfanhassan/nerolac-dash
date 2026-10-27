'use client';

import React, { useState, useEffect } from 'react';
import { DemandFanChart, DemandForecastResponse } from '@/components/supply_chain/DemandFanChart';
import { MRPActionTable, MRPProposalsResponse } from '@/components/supply_chain/MRPActionTable';

export default function SupplyChainDashboardPage() {
  const [selectedDepot, setSelectedDepot] = useState<string>('ALL');
  const [selectedSku, setSelectedSku] = useState<string>('ALL');

  const [forecastData, setForecastData] = useState<DemandForecastResponse | null>(null);
  const [mrpData, setMrpData] = useState<MRPProposalsResponse | null>(null);

  const [isLoadingForecast, setIsLoadingForecast] = useState<boolean>(true);
  const [isLoadingMRP, setIsLoadingMRP] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch forecast data
  const fetchForecast = async (depot: string, sku: string) => {
    setIsLoadingForecast(true);
    setErrorMsg(null);
    try {
      const params = new URLSearchParams();
      if (depot !== 'ALL') params.set('depot_id', depot);
      if (sku !== 'ALL') params.set('sku_id', sku);

      const url = `/api/v1/supply-chain/forecast${params.toString() ? `?${params.toString()}` : ''}`;
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to load forecast (HTTP ${res.status})`);
      }
      const data: DemandForecastResponse = await res.json();
      setForecastData(data);
    } catch (err: any) {
      console.error('Forecast fetch failed:', err);
      setErrorMsg(err.message || 'Error fetching forecast');
    } finally {
      setIsLoadingForecast(false);
    }
  };

  // Fetch MRP data
  const fetchMRP = async (depot: string) => {
    setIsLoadingMRP(true);
    try {
      const params = new URLSearchParams();
      if (depot !== 'ALL') params.set('depot_id', depot);

      const url = `/api/v1/supply-chain/mrp-proposals${params.toString() ? `?${params.toString()}` : ''}`;
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to load MRP proposals (HTTP ${res.status})`);
      }
      const data: MRPProposalsResponse = await res.json();
      setMrpData(data);
    } catch (err: any) {
      console.error('MRP proposals fetch failed:', err);
    } finally {
      setIsLoadingMRP(false);
    }
  };

  useEffect(() => {
    fetchForecast(selectedDepot, selectedSku);
    fetchMRP(selectedDepot);
  }, [selectedDepot, selectedSku]);

  const formatLiters = (val: number | undefined) => {
    if (val === undefined || isNaN(val)) return '—';
    return `${new Intl.NumberFormat('en-BD', { maximumFractionDigits: 0 }).format(val)} L`;
  };

  const formatCurrency = (val: number | undefined) => {
    if (val === undefined || isNaN(val)) return '৳0';
    return `৳${new Intl.NumberFormat('en-BD', { maximumFractionDigits: 0 }).format(val)}`;
  };

  return (
    <div
      style={{
        maxWidth: '1440px',
        margin: '0 auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
      }}
    >
      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '4px',
                height: '24px',
                backgroundColor: '#D32F2F',
                borderRadius: '2px',
              }}
            />
            <h1
              style={{
                fontSize: '22px',
                fontWeight: 700,
                color: '#0F172A',
                margin: 0,
                letterSpacing: '-0.3px',
              }}
            >
              Supply Chain Control Center (Module 3)
            </h1>
          </div>
          <p
            style={{
              fontSize: '13px',
              color: '#64748B',
              margin: '4px 0 0 12px',
            }}
          >
            LightGBM + Prophet ML Demand Forecasting • BOM Explosion & Purchase Reorder Proposals
            (SAP MB52 / ME2L / VA05)
          </p>
        </div>

        {/* Global Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Depot Selector */}
          <div>
            <label
              htmlFor="scm-depot-select"
              style={{
                display: 'block',
                fontSize: '11px',
                fontWeight: 600,
                color: '#64748B',
                marginBottom: '4px',
              }}
            >
              REGIONAL DEPOT
            </label>
            <select
              id="scm-depot-select"
              value={selectedDepot}
              onChange={(e) => setSelectedDepot(e.target.value)}
              style={{
                padding: '6px 10px',
                fontSize: '13px',
                fontWeight: 600,
                border: '1px solid #CBD5E1',
                borderRadius: '4px',
                backgroundColor: '#FFFFFF',
                color: '#0F172A',
                outline: 'none',
              }}
            >
              <option value="ALL">All Hubs (Bangladesh Operations)</option>
              <option value="DEPOT_01">Dhaka Central Hub</option>
              <option value="DEPOT_02">Chittagong Port Depot</option>
              <option value="DEPOT_03">Bogura Distribution Center</option>
              <option value="DEPOT_04">Sylhet Depot</option>
              <option value="DEPOT_05">Khulna Coastal Hub</option>
              <option value="DEPOT_06">Rajshahi Depot</option>
              <option value="DEPOT_07">Barishal Depot</option>
              <option value="DEPOT_08">Comilla Regional Hub</option>
            </select>
          </div>

          {/* SKU Selector */}
          <div>
            <label
              htmlFor="scm-sku-select"
              style={{
                display: 'block',
                fontSize: '11px',
                fontWeight: 600,
                color: '#64748B',
                marginBottom: '4px',
              }}
            >
              PRODUCT CATEGORY
            </label>
            <select
              id="scm-sku-select"
              value={selectedSku}
              onChange={(e) => setSelectedSku(e.target.value)}
              style={{
                padding: '6px 10px',
                fontSize: '13px',
                fontWeight: 600,
                border: '1px solid #CBD5E1',
                borderRadius: '4px',
                backgroundColor: '#FFFFFF',
                color: '#0F172A',
                outline: 'none',
              }}
            >
              <option value="ALL">All Product Categories</option>
              <option value="SKU_DEC_001">Nerolac Impressions Eco Clean 10L</option>
              <option value="SKU_DEC_002">Nerolac Beauty Gold Washable 4L</option>
              <option value="SKU_IND_001">Nerolac Epoxy Floor Coating High-Build 20L</option>
              <option value="SKU_EXT_001">Nerolac Excel Total Exterior 10L</option>
            </select>
          </div>

          {/* Refresh Action */}
          <div style={{ alignSelf: 'flex-end' }}>
            <button
              type="button"
              onClick={() => {
                fetchForecast(selectedDepot, selectedSku);
                fetchMRP(selectedDepot);
              }}
              style={{
                padding: '7px 12px',
                backgroundColor: '#F8FAFC',
                border: '1px solid #CBD5E1',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 600,
                color: '#334155',
                cursor: 'pointer',
              }}
            >
              ↻ Refresh
            </button>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: '#FEF2F2',
            border: '1px solid #FECACA',
            borderRadius: '6px',
            color: '#991B1B',
            fontSize: '13px',
          }}
        >
          {errorMsg}
        </div>
      )}

      {/* Executive Metric Cards Row */}
      <div
        id="scm-executive-kpi-cards"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '16px',
        }}
      >
        {/* Card 1: Month 0 Firm SAP Orders */}
        <div
          id="kpi-m0-firm-demand"
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #1E3A8A',
            borderRadius: '6px',
            padding: '16px',
          }}
        >
          <div
            style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', letterSpacing: '0.5px' }}
          >
            MONTH 0 FIRM SAP ORDERS (MAR 2024)
          </div>
          <div
            style={{
              fontSize: '24px',
              fontWeight: 700,
              color: '#0F172A',
              margin: '6px 0',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {formatLiters(forecastData?.month_0_firm_liters)}
          </div>
          <div style={{ fontSize: '12px', color: '#1E3A8A', fontWeight: 600 }}>
            ● Committed Production Schedule (100% Certainty)
          </div>
        </div>

        {/* Card 2: Month +1 ML Forecast */}
        <div
          id="kpi-m1-forecast"
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #D32F2F',
            borderRadius: '6px',
            padding: '16px',
          }}
        >
          <div
            style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', letterSpacing: '0.5px' }}
          >
            MONTH +1 ML PREDICTION (APR 2024)
          </div>
          <div
            style={{
              fontSize: '24px',
              fontWeight: 700,
              color: '#D32F2F',
              margin: '6px 0',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {formatLiters(forecastData?.month_1_forecast_liters)}
          </div>
          <div style={{ fontSize: '12px', color: '#64748B' }}>
            Ensemble LightGBM (55%) + Prophet (45%)
          </div>
        </div>

        {/* Card 3: Month +2 ML Forecast */}
        <div
          id="kpi-m2-forecast"
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #D97706',
            borderRadius: '6px',
            padding: '16px',
          }}
        >
          <div
            style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', letterSpacing: '0.5px' }}
          >
            MONTH +2 ML PREDICTION (MAY 2024)
          </div>
          <div
            style={{
              fontSize: '24px',
              fontWeight: 700,
              color: '#D97706',
              margin: '6px 0',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {formatLiters(forecastData?.month_2_forecast_liters)}
          </div>
          <div style={{ fontSize: '12px', color: '#64748B' }}>
            Uncertainty Range: ±80% & ±95% Fan Bands
          </div>
        </div>

        {/* Card 4: MRP Reorder Commitments */}
        <div
          id="kpi-mrp-commitment"
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #059669',
            borderRadius: '6px',
            padding: '16px',
          }}
        >
          <div
            style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', letterSpacing: '0.5px' }}
          >
            RECOMMENDED REORDER COMMITMENT
          </div>
          <div
            style={{
              fontSize: '24px',
              fontWeight: 700,
              color: '#059669',
              margin: '6px 0',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {formatCurrency(mrpData?.total_recommended_po_bdt)}
          </div>
          <div
            style={{
              fontSize: '12px',
              color: mrpData?.critical_alerts_count ? '#DC2626' : '#64748B',
              fontWeight: 600,
            }}
          >
            {mrpData?.critical_alerts_count
              ? `⚠️ ${mrpData.critical_alerts_count} Critical Shortfalls Requiring Indent`
              : 'All Materials Within Safety Stock'}
          </div>
        </div>
      </div>

      {/* Section 1: ECharts Demand Fan Chart */}
      <DemandFanChart forecastData={forecastData} isLoading={isLoadingForecast} />

      {/* Section 2: High-Density MRP Action Table */}
      <MRPActionTable data={mrpData} isLoading={isLoadingMRP} />
    </div>
  );
}
