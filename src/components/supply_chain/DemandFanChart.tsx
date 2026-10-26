'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';

export interface TimeSeriesDataPoint {
  period: string;
  period_label: string;
  actual_liters: number | null;
  is_firm_order: boolean;
  forecast_liters: number | null;
  lower_80: number | null;
  upper_80: number | null;
  lower_95: number | null;
  upper_95: number | null;
}

export interface DemandForecastResponse {
  depot_id: string;
  depot_name: string;
  sku_id: string;
  sku_name: string;
  unit_of_measure: string;
  model_name: string;
  training_period_months: number;
  mape_score_pct: number;
  month_0_firm_liters: number;
  month_1_forecast_liters: number;
  month_2_forecast_liters: number;
  series: TimeSeriesDataPoint[];
}

interface DemandFanChartProps {
  forecastData: DemandForecastResponse | null;
  isLoading?: boolean;
}

export function DemandFanChart({ forecastData, isLoading = false }: DemandFanChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const [show80Band, setShow80Band] = useState<boolean>(true);
  const [show95Band, setShow95Band] = useState<boolean>(true);

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const chart = chartInstance.current;

    if (isLoading) {
      chart.showLoading({
        text: 'Computing LightGBM + Prophet 24-Month Forecast...',
        color: '#D32F2F',
        textColor: '#64748B',
        maskColor: 'rgba(255, 255, 255, 0.7)',
        fontSize: 13,
      });
      return;
    }

    chart.hideLoading();

    if (!forecastData || forecastData.series.length === 0) {
      chart.clear();
      return;
    }

    const periods = forecastData.series.map((s) => s.period_label);

    // Historical actuals series (solid line)
    const actualData = forecastData.series.map((s) => s.actual_liters);

    // ML Forecast series (starts at Month 0 firm order so the dashed line connects smoothly)
    const forecastLineData = forecastData.series.map((s) => s.forecast_liters);

    // Confidence bands using stacked series
    // 95% Confidence Interval band (outer)
    const base95Data = forecastData.series.map((s) => {
      if (s.lower_95 !== null && show95Band) return s.lower_95;
      return null;
    });

    const diff95Data = forecastData.series.map((s) => {
      if (s.upper_95 !== null && s.lower_95 !== null && show95Band) {
        return Math.max(0, s.upper_95 - s.lower_95);
      }
      return null;
    });

    // 80% Confidence Interval band (inner)
    const base80Data = forecastData.series.map((s) => {
      if (s.lower_80 !== null && show80Band) return s.lower_80;
      return null;
    });

    const diff80Data = forecastData.series.map((s) => {
      if (s.upper_80 !== null && s.lower_80 !== null && show80Band) {
        return Math.max(0, s.upper_80 - s.lower_80);
      }
      return null;
    });

    // Month 0 Firm Order mark point
    const month0Index = forecastData.series.findIndex((s) => s.is_firm_order);

    const option: echarts.EChartsOption = {
      backgroundColor: '#FFFFFF',
      animationDuration: 600,
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          lineStyle: { color: '#94A3B8', width: 1, type: 'dashed' },
          crossStyle: { color: '#94A3B8' },
        },
        backgroundColor: '#FFFFFF',
        borderColor: '#E2E8F0',
        borderWidth: 1,
        padding: [12, 16],
        textStyle: { color: '#0F172A', fontSize: 12 },
        extraCssText: 'box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); border-radius: 6px;',
        formatter: (params: any) => {
          if (!Array.isArray(params) || params.length === 0) return '';
          const dataIndex = params[0].dataIndex;
          const point = forecastData.series[dataIndex];
          if (!point) return '';

          const formatLiters = (val: number | null) =>
            val !== null
              ? `${new Intl.NumberFormat('en-BD', { maximumFractionDigits: 0 }).format(val)} L`
              : '—';

          let statusTag = '';
          if (point.is_firm_order) {
            statusTag =
              '<span style="background: #FEF2F2; color: #D32F2F; border: 1px solid #FECACA; padding: 2px 6px; border-radius: 3px; font-weight: 700; font-size: 10px;">FIRM SAP ORDER</span>';
          } else if (point.forecast_liters !== null && point.actual_liters === null) {
            statusTag =
              '<span style="background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; padding: 2px 6px; border-radius: 3px; font-weight: 700; font-size: 10px;">ML PREDICTION</span>';
          } else {
            statusTag =
              '<span style="background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0; padding: 2px 6px; border-radius: 3px; font-weight: 600; font-size: 10px;">HISTORICAL ACTUAL</span>';
          }

          let html = `
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; min-width: 210px;">
              <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #F1F5F9; padding-bottom: 6px; margin-bottom: 8px;">
                <span style="font-weight: 700; color: #0F172A; font-size: 13px;">${point.period_label}</span>
                ${statusTag}
              </div>
          `;

          if (point.actual_liters !== null) {
            html += `
              <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-variant-numeric: tabular-nums;">
                <span style="color: #64748B;">${point.is_firm_order ? 'Firm SAP Order:' : 'Realized Actuals:'}</span>
                <span style="font-weight: 700; color: #1E3A8A;">${formatLiters(point.actual_liters)}</span>
              </div>
            `;
          }

          if (point.forecast_liters !== null) {
            html += `
              <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-variant-numeric: tabular-nums;">
                <span style="color: #64748B;">Ensemble ML Forecast:</span>
                <span style="font-weight: 700; color: #D32F2F;">${formatLiters(point.forecast_liters)}</span>
              </div>
            `;
          }

          if (point.lower_80 !== null && point.upper_80 !== null && !point.is_firm_order) {
            html += `
              <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-variant-numeric: tabular-nums; font-size: 11px;">
                <span style="color: #64748B;">80% Confidence Band:</span>
                <span style="color: #475569; font-weight: 600;">${formatLiters(point.lower_80)} - ${formatLiters(point.upper_80)}</span>
              </div>
            `;
          }

          if (point.lower_95 !== null && point.upper_95 !== null && !point.is_firm_order) {
            html += `
              <div style="display: flex; justify-content: space-between; font-variant-numeric: tabular-nums; font-size: 11px;">
                <span style="color: #64748B;">95% Confidence Band:</span>
                <span style="color: #64748B; font-weight: 500;">${formatLiters(point.lower_95)} - ${formatLiters(point.upper_95)}</span>
              </div>
            `;
          }

          html += '</div>';
          return html;
        },
      },
      legend: {
        show: true,
        bottom: 0,
        itemGap: 20,
        textStyle: { color: '#475569', fontSize: 12, fontWeight: 500 },
        data: [
          { name: 'Historical Actuals (Liters)', icon: 'circle' },
          { name: 'ML Forecast (Ensemble)', icon: 'line' },
          { name: '80% Confidence Interval', icon: 'rect' },
          { name: '95% Confidence Interval', icon: 'rect' },
        ],
      },
      grid: {
        left: '50px',
        right: '40px',
        top: '30px',
        bottom: '50px',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: periods,
        axisLine: { lineStyle: { color: '#CBD5E1' } },
        axisTick: { alignWithLabel: true },
        axisLabel: {
          color: '#64748B',
          fontSize: 11,
          interval: 2,
          rotate: 0,
        },
        splitLine: {
          show: true,
          lineStyle: { color: '#F1F5F9', type: 'solid' },
        },
      },
      yAxis: {
        type: 'value',
        name: 'Volume (Liters)',
        nameTextStyle: { color: '#64748B', fontSize: 11, padding: [0, 0, 0, 10] },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: '#64748B',
          fontSize: 11,
          formatter: (value: number) => {
            if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M L`;
            if (value >= 1_000) return `${(value / 1_000).toFixed(0)}k L`;
            return `${value} L`;
          },
        },
        splitLine: {
          show: true,
          lineStyle: { color: '#F1F5F9', type: 'solid' },
        },
      },
      series: [
        // 1. 95% CI Base (Invisible)
        {
          name: '95% Confidence Base',
          type: 'line',
          stack: 'ci_95',
          data: base95Data,
          symbol: 'none',
          lineStyle: { opacity: 0 },
          itemStyle: { color: 'transparent' },
          silent: true,
        },
        // 2. 95% CI Band (Shaded area)
        {
          name: '95% Confidence Interval',
          type: 'line',
          stack: 'ci_95',
          data: diff95Data,
          symbol: 'none',
          lineStyle: { opacity: 0 },
          areaStyle: {
            color: 'rgba(211, 47, 47, 0.10)',
          },
          itemStyle: { color: 'rgba(211, 47, 47, 0.20)' },
          silent: false,
        },
        // 3. 80% CI Base (Invisible)
        {
          name: '80% Confidence Base',
          type: 'line',
          stack: 'ci_80',
          data: base80Data,
          symbol: 'none',
          lineStyle: { opacity: 0 },
          itemStyle: { color: 'transparent' },
          silent: true,
        },
        // 4. 80% CI Band (Darker shaded area)
        {
          name: '80% Confidence Interval',
          type: 'line',
          stack: 'ci_80',
          data: diff80Data,
          symbol: 'none',
          lineStyle: { opacity: 0 },
          areaStyle: {
            color: 'rgba(211, 47, 47, 0.22)',
          },
          itemStyle: { color: 'rgba(211, 47, 47, 0.35)' },
          silent: false,
        },
        // 5. Historical Actuals (Solid Navy Line)
        {
          name: 'Historical Actuals (Liters)',
          type: 'line',
          data: actualData,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: { color: '#1E3A8A' },
          lineStyle: { width: 2.5, color: '#1E3A8A' },
          markPoint:
            month0Index >= 0
              ? {
                  symbol: 'pin',
                  symbolSize: 42,
                  itemStyle: { color: '#D32F2F' },
                  data: [
                    {
                      name: 'Month 0 Firm Order',
                      coord: [month0Index, forecastData.series[month0Index].actual_liters || 0],
                      value: 'M0',
                    },
                  ],
                }
              : undefined,
        },
        // 6. ML Forecast (Dashed Nerolac Red Line)
        {
          name: 'ML Forecast (Ensemble)',
          type: 'line',
          data: forecastLineData,
          symbol: 'diamond',
          symbolSize: 8,
          itemStyle: { color: '#D32F2F' },
          lineStyle: {
            width: 2.5,
            color: '#D32F2F',
            type: 'dashed',
          },
        },
      ],
    };

    chart.setOption(option, true);

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [forecastData, show80Band, show95Band, isLoading]);

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        borderRadius: '6px',
        border: '1px solid #E2E8F0',
        padding: '20px',
      }}
    >
      {/* Header telemetry and controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          borderBottom: '1px solid #F1F5F9',
          paddingBottom: '16px',
          marginBottom: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: '#D32F2F',
                display: 'inline-block',
              }}
            />
            <h2
              style={{
                fontSize: '16px',
                fontWeight: 700,
                color: '#0F172A',
                margin: 0,
              }}
            >
              Demand Fan Chart: 24-Month History & +1/+2 Forecast
            </h2>
          </div>
          <div
            style={{
              fontSize: '12px',
              color: '#64748B',
              marginTop: '4px',
            }}
          >
            LightGBM (55%) + Prophet (45%) with MB52 zero-stockout imputation across 8 depots
          </div>
        </div>

        {/* Model Telemetry Chips & Band Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {forecastData && (
            <>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: '#1E3A8A',
                  backgroundColor: '#EFF6FF',
                  border: '1px solid #DBEAFE',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                MAPE: {forecastData.mape_score_pct.toFixed(1)}%
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: '#059669',
                  backgroundColor: '#ECFDF5',
                  border: '1px solid #A7F3D0',
                  padding: '3px 8px',
                  borderRadius: '4px',
                }}
              >
                ● Stockout Masked
              </span>
            </>
          )}

          <button
            type="button"
            onClick={() => setShow80Band(!show80Band)}
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '4px 10px',
              borderRadius: '4px',
              border: '1px solid #CBD5E1',
              backgroundColor: show80Band ? '#FEE2E2' : '#FFFFFF',
              color: show80Band ? '#991B1B' : '#64748B',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            {show80Band ? '✓ 80% Band (Active)' : '+ 80% Band'}
          </button>

          <button
            type="button"
            onClick={() => setShow95Band(!show95Band)}
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '4px 10px',
              borderRadius: '4px',
              border: '1px solid #CBD5E1',
              backgroundColor: show95Band ? '#FEE2E2' : '#FFFFFF',
              color: show95Band ? '#991B1B' : '#64748B',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            {show95Band ? '✓ 95% Band (Active)' : '+ 95% Band'}
          </button>
        </div>
      </div>

      {/* Fan Chart Canvas Container */}
      <div
        id="echarts-fanchart-container"
        ref={chartRef}
        style={{
          width: '100%',
          height: '420px',
        }}
      />
    </div>
  );
}
