'use client';

import React, { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';

export interface MonthlyCashflowProjection {
  month_index: number;
  month_label: string;
  opening_balance_bdt: number;
  ar_collected_bdt: number;
  cash_sales_bdt: number;
  total_inflow_bdt: number;
  ap_disbursed_bdt: number;
  opex_disbursed_bdt: number;
  capex_disbursed_bdt: number;
  total_outflow_bdt: number;
  net_cashflow_bdt: number;
  closing_balance_bdt: number;
}

export interface CashflowSimulationResponse {
  execution_time_ms: number;
  ar_collection_pct: number;
  dpo_days: number;
  capex_bdt: number;
  forecast_months: number;
  initial_cash_buffer_bdt: number;
  ending_cash_balance_bdt: number;
  minimum_cash_trough_bdt: number;
  working_capital_burn_bdt: number;
  liquidity_status: string;
  monthly_projections: MonthlyCashflowProjection[];
}

export function CashflowSimulator() {
  const [arCollectionPct, setArCollectionPct] = useState<number>(85);
  const [dpoDays, setDpoDays] = useState<number>(45);
  const [capexMillion, setCapexMillion] = useState<number>(5);
  const [simResult, setSimResult] = useState<CashflowSimulationResponse | null>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  const isModified = arCollectionPct !== 85 || dpoDays !== 45 || capexMillion !== 5;

  const handleResetToBaseline = () => {
    setArCollectionPct(85);
    setDpoDays(45);
    setCapexMillion(5);
  };

  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  // Trigger real-time <50ms cash flow simulation
  const runSimulation = async (ar: number, dpo: number, capexM: number) => {
    setIsSimulating(true);
    try {
      const capexBDT = capexM * 1000000;
      const resp = await fetch(
        `/api/v1/finance/simulate-cashflow?ar_collection_pct=${ar}&dpo_days=${dpo}&capex_bdt=${capexBDT}&forecast_months=6`
      );
      if (resp.ok) {
        const data: CashflowSimulationResponse = await resp.json();
        setSimResult(data);
      }
    } catch (err) {
      console.error('Failed to execute cash flow simulation:', err);
    } finally {
      setIsSimulating(false);
    }
  };

  useEffect(() => {
    runSimulation(arCollectionPct, dpoDays, capexMillion);
  }, [arCollectionPct, dpoDays, capexMillion]);

  // Update ECharts Cash Flow multi-series chart
  useEffect(() => {
    if (!chartRef.current || !simResult || simResult.monthly_projections.length === 0) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const months = simResult.monthly_projections.map((p) => p.month_label);
    const inflows = simResult.monthly_projections.map((p) => p.total_inflow_bdt / 1000000);
    const outflows = simResult.monthly_projections.map((p) => p.total_outflow_bdt / 1000000);
    const balances = simResult.monthly_projections.map((p) => p.closing_balance_bdt / 1000000);

    const option: echarts.EChartsOption = {
      backgroundColor: '#FFFFFF',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any) => {
          let str = `<div style="font-family: inherit; font-size: 11px; font-variant-numeric: tabular-nums;">
            <strong>${params[0].axisValue}</strong><br/>`;
          params.forEach((p: any) => {
            str += `${p.marker} ${p.seriesName}: ৳${p.value.toFixed(2)}M<br/>`;
          });
          str += `</div>`;
          return str;
        },
      },
      legend: {
        data: ['Total Cash Inflow', 'Total Cash Outflow', 'Cumulative Cash Balance'],
        top: 0,
        textStyle: { fontSize: 11, color: '#475569' },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '8%',
        top: '14%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: months,
        axisLabel: { fontSize: 11, color: '#334155' },
        axisLine: { lineStyle: { color: '#CBD5E1' } },
      },
      yAxis: [
        {
          type: 'value',
          name: 'Flows (৳M)',
          nameTextStyle: { color: '#64748B', fontSize: 10 },
          axisLabel: { formatter: '৳{value}M', fontSize: 10, color: '#64748B' },
          splitLine: { lineStyle: { color: '#E2E8F0', type: 'dashed' } },
        },
        {
          type: 'value',
          name: 'Balance (৳M)',
          nameTextStyle: { color: '#1E3A8A', fontSize: 10 },
          axisLabel: { formatter: '৳{value}M', fontSize: 10, color: '#1E3A8A' },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: 'Total Cash Inflow',
          type: 'bar',
          data: inflows,
          itemStyle: { color: '#059669', borderRadius: [2, 2, 0, 0] },
        },
        {
          name: 'Total Cash Outflow',
          type: 'bar',
          data: outflows,
          itemStyle: { color: '#D32F2F', borderRadius: [2, 2, 0, 0] },
        },
        {
          name: 'Cumulative Cash Balance',
          type: 'line',
          yAxisIndex: 1,
          data: balances,
          lineStyle: { width: 3, color: '#1E3A8A' },
          itemStyle: { color: '#1E3A8A' },
          symbol: 'circle',
          symbolSize: 6,
        },
      ],
    };

    chartInstance.current.setOption(option);

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [simResult]);

  const formatBDT = (val: number) => {
    return new Intl.NumberFormat('en-BD', {
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '6px',
        padding: '16px',
        marginTop: '24px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        <div>
          <h3
            style={{
              fontSize: '14px',
              fontWeight: 700,
              color: '#0F172A',
            }}
          >
            Real-Time Cash Flow Scenario Simulator
          </h3>
          <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
            Interactive treasury sensitivity model executing in &lt;50ms across working capital
            parameters.
          </p>
        </div>

        {simResult && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', color: '#64748B' }}>
              Execution Latency: <strong>{simResult.execution_time_ms.toFixed(1)}ms</strong>
            </span>
            <span
              id="liquidity-status-badge"
              style={{
                backgroundColor:
                  simResult.liquidity_status === 'HEALTHY'
                    ? '#D1FAE5'
                    : simResult.liquidity_status === 'CAUTION'
                      ? '#FEF3C7'
                      : '#FEE2E2',
                color:
                  simResult.liquidity_status === 'HEALTHY'
                    ? '#059669'
                    : simResult.liquidity_status === 'CAUTION'
                      ? '#D97706'
                      : '#DC2626',
                border: '1px solid #CBD5E1',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 700,
              }}
            >
              {simResult.liquidity_status} LIQUIDITY
            </span>

            <button
              id="btn-reset-simulator"
              type="button"
              onClick={handleResetToBaseline}
              disabled={!isModified}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11px',
                fontWeight: 600,
                color: isModified ? '#D32F2F' : '#94A3B8',
                backgroundColor: isModified ? '#FFEBEE' : '#F8FAFC',
                border: `1px solid ${isModified ? '#FFCDD2' : '#E2E8F0'}`,
                padding: '2px 8px',
                borderRadius: '4px',
                cursor: isModified ? 'pointer' : 'default',
                transition: 'all 0.15s ease',
              }}
              title="Reset simulation parameters to corporate baseline (85% AR, 45d DPO, ৳5M CapEx)"
            >
              <span>↺</span> Reset to Baseline
            </button>
          </div>
        )}
      </div>

      {/* Simulator Control Sliders */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '16px',
          backgroundColor: '#F8FAFC',
          padding: '16px',
          borderRadius: '6px',
          border: '1px solid #E2E8F0',
          marginBottom: '16px',
        }}
      >
        {/* Slider 1: AR Collection Efficiency */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              AR Collection Efficiency (%)
            </label>
            <span
              id="slider-val-ar"
              className="tabular-nums"
              style={{ fontSize: '12px', fontWeight: 700, color: '#D32F2F' }}
            >
              {arCollectionPct}%
            </span>
          </div>
          <input
            id="slider-ar-collection"
            type="range"
            min="50"
            max="100"
            step="1"
            value={arCollectionPct}
            onChange={(e) => setArCollectionPct(Number(e.target.value))}
            className="corporate-slider"
          />
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '10px',
              color: '#94A3B8',
              marginTop: '4px',
            }}
          >
            <span>50% (Distressed)</span>
            <span>85% (Target)</span>
            <span>100% (Full Realization)</span>
          </div>
        </div>

        {/* Slider 2: Days Payable Outstanding (DPO) */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              Days Payable Outstanding (DPO)
            </label>
            <span
              id="slider-val-dpo"
              className="tabular-nums"
              style={{ fontSize: '12px', fontWeight: 700, color: '#D32F2F' }}
            >
              {dpoDays} Days
            </span>
          </div>
          <input
            id="slider-dpo"
            type="range"
            min="15"
            max="120"
            step="5"
            value={dpoDays}
            onChange={(e) => setDpoDays(Number(e.target.value))}
            className="corporate-slider"
          />
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '10px',
              color: '#94A3B8',
              marginTop: '4px',
            }}
          >
            <span>15 Days</span>
            <span>45 Days (Baseline)</span>
            <span>120 Days</span>
          </div>
        </div>

        {/* Slider 3: Planned CapEx */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              Planned CapEx (৳ Millions)
            </label>
            <span
              id="slider-val-capex"
              className="tabular-nums"
              style={{ fontSize: '12px', fontWeight: 700, color: '#D32F2F' }}
            >
              ৳{capexMillion}M BDT
            </span>
          </div>
          <input
            id="slider-capex"
            type="range"
            min="0"
            max="30"
            step="1"
            value={capexMillion}
            onChange={(e) => setCapexMillion(Number(e.target.value))}
            className="corporate-slider"
          />
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '10px',
              color: '#94A3B8',
              marginTop: '4px',
            }}
          >
            <span>৳0M (Maintenance)</span>
            <span>৳5M (Current Plan)</span>
            <span>৳30M (Major Expansion)</span>
          </div>
        </div>
      </div>

      {/* KPI Projection Metrics */}
      {simResult && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '12px',
            marginBottom: '16px',
          }}
        >
          <div
            style={{
              padding: '12px',
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '4px',
            }}
          >
            <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 500 }}>
              Ending Cash Balance (M6)
            </div>
            <div
              id="simulated-net-cashflow"
              data-testid="kpi-ending-cash"
              className="tabular-nums"
              style={{
                fontSize: '18px',
                fontWeight: 700,
                color: simResult.ending_cash_balance_bdt >= 0 ? '#059669' : '#D32F2F',
                marginTop: '4px',
              }}
            >
              ৳{formatBDT(simResult.ending_cash_balance_bdt)}
            </div>
          </div>

          <div
            style={{
              padding: '12px',
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '4px',
            }}
          >
            <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 500 }}>
              Minimum Cash Trough
            </div>
            <div
              className="tabular-nums"
              style={{
                fontSize: '18px',
                fontWeight: 700,
                color: simResult.minimum_cash_trough_bdt >= 15000000 ? '#0F172A' : '#D97706',
                marginTop: '4px',
              }}
            >
              ৳{formatBDT(simResult.minimum_cash_trough_bdt)}
            </div>
          </div>

          <div
            style={{
              padding: '12px',
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '4px',
            }}
          >
            <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 500 }}>
              Working Capital Burn
            </div>
            <div
              className="tabular-nums"
              style={{
                fontSize: '18px',
                fontWeight: 700,
                color: simResult.working_capital_burn_bdt > 0 ? '#D32F2F' : '#059669',
                marginTop: '4px',
              }}
            >
              ৳{formatBDT(simResult.working_capital_burn_bdt)}
            </div>
          </div>

          <div
            style={{
              padding: '12px',
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '4px',
            }}
          >
            <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 500 }}>
              Forecast Horizon
            </div>
            <div
              className="tabular-nums"
              style={{
                fontSize: '18px',
                fontWeight: 700,
                color: '#1E3A8A',
                marginTop: '4px',
              }}
            >
              {simResult.forecast_months} Months
            </div>
          </div>
        </div>
      )}

      {/* Real-Time Cash Flow ECharts Container */}
      <div
        id="echarts-cashflow-container"
        ref={chartRef}
        style={{ width: '100%', height: '280px', minHeight: '280px' }}
      />
    </div>
  );
}
