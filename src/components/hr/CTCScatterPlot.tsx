'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';

export interface CTCScatterPoint {
  employee_id: string;
  employee_code: string;
  full_name: string;
  designation: string;
  depot_id: string;
  depot_name: string;
  territory_name: string;
  base_salary_bdt: number;
  tada_bdt: number;
  incentives_bdt: number;
  overhead_bdt: number;
  fully_loaded_ctc_bdt: number;
  gross_sales_bdt: number;
  contribution_margin_bdt: number;
  roi_multiple: number;
  quadrant: string;
  coordinates: number[];
}

export interface QuadrantSummary {
  quadrant: string;
  label: string;
  count: number;
  percentage: number;
  avg_ctc_bdt: number;
  avg_margin_bdt: number;
  avg_roi_multiple: number;
}

interface CTCScatterPlotProps {
  points: CTCScatterPoint[];
  quadrants: QuadrantSummary[];
  medianCTC: number;
  medianMargin: number;
  isLoading?: boolean;
}

export function CTCScatterPlot({
  points,
  quadrants,
  medianCTC,
  medianMargin,
  isLoading = false,
}: CTCScatterPlotProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const [activeQuadrantFilter, setActiveQuadrantFilter] = useState<string>('ALL');

  const filteredPoints =
    activeQuadrantFilter === 'ALL'
      ? points
      : points.filter((p) => p.quadrant === activeQuadrantFilter);

  useEffect(() => {
    if (!chartRef.current || points.length === 0) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const quadrantColorMap: Record<string, string> = {
      STARS: '#059669', // Emerald Green (High Margin, Moderate Cost)
      HEAVY_HITTERS: '#2563EB', // Royal Blue (High Margin, High Cost)
      RAMP_UP: '#D97706', // Warm Amber (Developing, Low Cost)
      VALUE_DESTROYERS: '#DC2626', // Red (Low Margin, High Cost)
    };

    // Group points by quadrant for distinct series styling
    const seriesList = ['STARS', 'HEAVY_HITTERS', 'RAMP_UP', 'VALUE_DESTROYERS'].map((quadKey) => {
      const quadPoints = filteredPoints
        .filter((p) => p.quadrant === quadKey)
        .map((p) => ({
          value: [p.fully_loaded_ctc_bdt, p.contribution_margin_bdt],
          pointMeta: p,
        }));

      const quadLabel =
        quadKey === 'STARS'
          ? 'Stars'
          : quadKey === 'HEAVY_HITTERS'
            ? 'Heavy Hitters'
            : quadKey === 'RAMP_UP'
              ? 'Ramp-Up'
              : 'Value Destroyers';

      return {
        name: quadLabel,
        type: 'scatter' as const,
        symbolSize: 14,
        data: quadPoints,
        itemStyle: {
          color: quadrantColorMap[quadKey],
          borderColor: '#FFFFFF',
          borderWidth: 1.5,
        },
        emphasis: {
          focus: 'series' as const,
          itemStyle: {
            borderWidth: 3,
            borderColor: '#0F172A',
          },
        },
      };
    });

    const option: echarts.EChartsOption = {
      animation: true,
      grid: {
        top: 40,
        right: 40,
        bottom: 60,
        left: 80,
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: '#FFFFFF',
        borderColor: '#E2E8F0',
        borderWidth: 1,
        padding: 12,
        textStyle: {
          color: '#0F172A',
          fontSize: 12,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        },
        formatter: (params: any) => {
          const meta: CTCScatterPoint | undefined = params.data?.pointMeta;
          if (!meta) return '';

          return `
            <div style="font-family: inherit; font-variant-numeric: tabular-nums;">
              <div style="font-weight: 700; font-size: 13px; color: #0F172A;">${meta.full_name}</div>
              <div style="font-size: 11px; color: #64748B; margin-bottom: 6px;">
                ${meta.designation} • ${meta.territory_name} (${meta.depot_name})
              </div>
              <div style="border-top: 1px solid #E2E8F0; padding-top: 6px; font-size: 11px; display: grid; grid-template-columns: 140px auto; gap: 4px;">
                <span style="color: #64748B;">Base Salary:</span>
                <span style="font-weight: 600; text-align: right;">BDT ${meta.base_salary_bdt.toLocaleString()}</span>
                <span style="color: #64748B;">TA / DA:</span>
                <span style="font-weight: 600; text-align: right;">BDT ${meta.tada_bdt.toLocaleString()}</span>
                <span style="color: #64748B;">Incentives:</span>
                <span style="font-weight: 600; text-align: right;">BDT ${meta.incentives_bdt.toLocaleString()}</span>
                <span style="color: #64748B;">Overhead:</span>
                <span style="font-weight: 600; text-align: right;">BDT ${meta.overhead_bdt.toLocaleString()}</span>
                <span style="color: #0F172A; font-weight: 700;">Fully-Loaded CTC:</span>
                <span style="font-weight: 700; color: #0F172A; text-align: right;">BDT ${meta.fully_loaded_ctc_bdt.toLocaleString()}</span>
                <span style="color: #059669; font-weight: 700;">Contribution Margin:</span>
                <span style="font-weight: 700; color: #059669; text-align: right;">BDT ${meta.contribution_margin_bdt.toLocaleString()}</span>
                <span style="color: #2563EB; font-weight: 700;">ROI Multiple:</span>
                <span style="font-weight: 700; color: #2563EB; text-align: right;">${meta.roi_multiple.toFixed(2)}x CTC</span>
              </div>
            </div>
          `;
        },
      },
      legend: {
        bottom: 10,
        textStyle: {
          color: '#475569',
          fontSize: 11,
          fontWeight: 600,
        },
        itemGap: 16,
      },
      xAxis: {
        type: 'value',
        name: 'Fully-Loaded Monthly CTC (BDT)',
        nameLocation: 'middle',
        nameGap: 36,
        nameTextStyle: {
          color: '#475569',
          fontSize: 11,
          fontWeight: 600,
        },
        axisLabel: {
          color: '#64748B',
          fontSize: 11,
          formatter: (val: number) => `BDT ${(val / 1000).toFixed(0)}k`,
        },
        splitLine: {
          lineStyle: {
            color: '#F1F5F9',
          },
        },
      },
      yAxis: {
        type: 'value',
        name: 'Contribution Margin (BDT)',
        nameTextStyle: {
          color: '#475569',
          fontSize: 11,
          fontWeight: 600,
        },
        axisLabel: {
          color: '#64748B',
          fontSize: 11,
          formatter: (val: number) => `BDT ${(val / 100000).toFixed(1)}L`,
        },
        splitLine: {
          lineStyle: {
            color: '#F1F5F9',
          },
        },
      },
      series: [
        ...seriesList,
        // Median reference split lines creating the 4 visual quadrants
        {
          name: 'Partition Thresholds',
          type: 'line',
          data: [],
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: {
              color: '#94A3B8',
              type: 'dashed',
              width: 1.5,
            },
            data: [
              {
                xAxis: medianCTC,
                label: {
                  formatter: `Median CTC\nBDT ${(medianCTC / 1000).toFixed(0)}k`,
                  position: 'insideEndTop' as const,
                  color: '#64748B',
                  fontSize: 10,
                  fontWeight: 600,
                },
              },
              {
                yAxis: medianMargin,
                label: {
                  formatter: `Median Margin: BDT ${(medianMargin / 100000).toFixed(1)}L`,
                  position: 'end' as const,
                  color: '#64748B',
                  fontSize: 10,
                  fontWeight: 600,
                },
              },
            ],
          },
        },
      ],
    };

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [filteredPoints, points.length, medianCTC, medianMargin]);

  if (isLoading) {
    return (
      <div
        id="ctc-scatter-loading"
        style={{
          padding: '40px',
          textAlign: 'center',
          backgroundColor: '#FFFFFF',
          borderRadius: '4px',
          border: '1px solid #E2E8F0',
          color: '#64748B',
          fontSize: '13px',
        }}
      >
        Loading Fully-Loaded CTC vs. Contribution Margin 4-Quadrant Scatter...
      </div>
    );
  }

  const quadConfig: Record<string, { color: string; bg: string; border: string }> = {
    STARS: { color: '#065F46', bg: '#ECFDF5', border: '#A7F3D0' },
    HEAVY_HITTERS: { color: '#1E40AF', bg: '#EFF6FF', border: '#BFDBFE' },
    RAMP_UP: { color: '#92400E', bg: '#FFFBEB', border: '#FDE68A' },
    VALUE_DESTROYERS: { color: '#991B1B', bg: '#FEF2F2', border: '#FECACA' },
  };

  return (
    <div
      id="ctc-scatter-plot-section"
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '4px',
        padding: '20px',
      }}
    >
      {/* Header and Quadrant Pills */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          paddingBottom: '16px',
          borderBottom: '1px solid #E2E8F0',
          marginBottom: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                backgroundColor: '#D32F2F',
                color: '#FFFFFF',
                padding: '2px 8px',
                borderRadius: '2px',
                letterSpacing: '0.5px',
              }}
            >
              4-QUADRANT MATRIX
            </span>
            <span style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A' }}>
              Fully-Loaded CTC vs. Contribution Margin
            </span>
          </div>
          <p style={{ fontSize: '12px', color: '#64748B', margin: '4px 0 0 0' }}>
            Identifies compensation capital allocation efficiency (Base + TA/DA + Incentives +
            Overhead) against realized margins
          </p>
        </div>

        {/* Quadrant filter pills */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setActiveQuadrantFilter('ALL')}
            style={{
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: 600,
              borderRadius: '4px',
              border: '1px solid #CBD5E1',
              cursor: 'pointer',
              backgroundColor: activeQuadrantFilter === 'ALL' ? '#0F172A' : '#FFFFFF',
              color: activeQuadrantFilter === 'ALL' ? '#FFFFFF' : '#475569',
            }}
          >
            All Reps ({points.length})
          </button>

          {quadrants.map((q) => {
            const style = quadConfig[q.quadrant] || {
              color: '#475569',
              bg: '#F8FAFC',
              border: '#E2E8F0',
            };
            const isSelected = activeQuadrantFilter === q.quadrant;

            return (
              <button
                key={q.quadrant}
                onClick={() => setActiveQuadrantFilter(q.quadrant)}
                style={{
                  padding: '4px 10px',
                  fontSize: '11px',
                  fontWeight: 600,
                  borderRadius: '4px',
                  cursor: 'pointer',
                  border: isSelected ? '2px solid #0F172A' : `1px solid ${style.border}`,
                  backgroundColor: style.bg,
                  color: style.color,
                }}
              >
                {q.quadrant === 'STARS'
                  ? 'Stars'
                  : q.quadrant === 'HEAVY_HITTERS'
                    ? 'Heavy Hitters'
                    : q.quadrant === 'RAMP_UP'
                      ? 'Ramp-Up'
                      : 'Value Destroyers'}{' '}
                ({q.count})
              </button>
            );
          })}
        </div>
      </div>

      {/* 4 Quadrant Metric Summary Cards */}
      <div
        id="quadrant-summary-cards"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        {quadrants.map((q) => {
          const style = quadConfig[q.quadrant] || {
            color: '#475569',
            bg: '#F8FAFC',
            border: '#E2E8F0',
          };

          return (
            <div
              key={q.quadrant}
              style={{
                backgroundColor: style.bg,
                border: `1px solid ${style.border}`,
                borderRadius: '4px',
                padding: '10px 14px',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              <div
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                <span style={{ fontSize: '12px', fontWeight: 700, color: style.color }}>
                  {q.quadrant === 'STARS'
                    ? '⭐ Stars'
                    : q.quadrant === 'HEAVY_HITTERS'
                      ? '⚡ Heavy Hitters'
                      : q.quadrant === 'RAMP_UP'
                        ? '🌱 Ramp-Up'
                        : '⚠️ Value Destroyers'}
                </span>
                <span style={{ fontSize: '11px', fontWeight: 700, color: style.color }}>
                  {q.count} Reps ({q.percentage.toFixed(0)}%)
                </span>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginTop: '6px',
                  fontSize: '10px',
                  color: '#475569',
                }}
              >
                <span>Avg CTC: BDT {(q.avg_ctc_bdt / 1000).toFixed(0)}k</span>
                <span>Avg Margin: BDT {(q.avg_margin_bdt / 100000).toFixed(1)}L</span>
              </div>
              <div
                style={{ fontSize: '10px', fontWeight: 600, color: style.color, marginTop: '2px' }}
              >
                ROI Multiple: {q.avg_roi_multiple.toFixed(2)}x
              </div>
            </div>
          );
        })}
      </div>

      {/* ECharts 4-Quadrant Scatter Container */}
      <div
        id="echarts-scatter-container"
        ref={chartRef}
        style={{
          width: '100%',
          height: '460px',
        }}
      />
    </div>
  );
}
