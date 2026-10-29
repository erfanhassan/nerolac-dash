'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';

export interface KPIScoreBreakdown {
  sales_score: number;
  collections_score: number;
  coverage_score: number;
  conversions_score: number;
  reviews_score: number;
  whatsapp_discipline_score: number;
}

export interface EmployeeScorecard {
  employee_id: string;
  employee_code: string;
  full_name: string;
  designation: string;
  department: string;
  depot_id: string;
  depot_name: string;
  territory_name: string;
  kpi_breakdown: KPIScoreBreakdown;
  overall_score: number;
  performance_tier: string;
  radar_values: number[];
}

export interface RadarAxisIndicator {
  name: string;
  max: number;
}

interface RepRadarChartProps {
  scorecards: EmployeeScorecard[];
  indicators: RadarAxisIndicator[];
  teamBenchmark: number[];
  weights: Record<string, number>;
  isLoading?: boolean;
  selectedRepId?: string;
  onSelectRep?: (id: string) => void;
  activeQuadrantFilter?: string;
  onQuadrantChange?: (quadrant: string) => void;
  repQuadrantMap?: Record<string, string>;
  onDepotSelect?: (depotId: string) => void;
}

export function RepRadarChart({
  scorecards,
  indicators,
  teamBenchmark,
  weights,
  isLoading = false,
  selectedRepId: propSelectedRepId,
  onSelectRep,
  activeQuadrantFilter = 'ALL',
  onQuadrantChange,
  repQuadrantMap,
  onDepotSelect,
}: RepRadarChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const [internalRepId, setInternalRepId] = useState<string>(
    scorecards.length > 0 ? scorecards[0].employee_id : ''
  );

  const activeRepId = propSelectedRepId ?? internalRepId;

  // Sync activeRepId if scorecards list changes and rep is not found
  useEffect(() => {
    if (scorecards.length > 0 && !scorecards.some((s) => s.employee_id === activeRepId)) {
      const nextId = scorecards[0].employee_id;
      setInternalRepId(nextId);
      onSelectRep?.(nextId);
    }
  }, [scorecards, activeRepId, onSelectRep]);

  const handleRepChange = (newId: string) => {
    setInternalRepId(newId);
    onSelectRep?.(newId);
  };

  const selectedRep =
    scorecards.find((s) => s.employee_id === activeRepId) ||
    (scorecards.length > 0 ? scorecards[0] : null);

  useEffect(() => {
    if (!chartRef.current || !selectedRep || indicators.length === 0) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const radarIndicators = indicators.map((ind) => ({
      name: ind.name,
      max: ind.max,
      color: '#475569',
    }));

    const option: echarts.EChartsOption = {
      animation: true,
      tooltip: {
        trigger: 'item',
        backgroundColor: '#FFFFFF',
        borderColor: '#E2E8F0',
        borderWidth: 1,
        textStyle: {
          color: '#0F172A',
          fontSize: 12,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        },
      },
      legend: {
        bottom: 0,
        data: [selectedRep.full_name, 'Team Benchmark Average'],
        textStyle: {
          color: '#475569',
          fontSize: 11,
          fontWeight: 600,
        },
        itemGap: 16,
      },
      radar: {
        indicator: radarIndicators,
        shape: 'polygon',
        splitNumber: 4,
        axisName: {
          color: '#1E293B',
          fontSize: 11,
          fontWeight: 600,
        },
        splitLine: {
          lineStyle: {
            color: '#E2E8F0',
          },
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: ['#FFFFFF', '#F8FAFC'],
          },
        },
        axisLine: {
          lineStyle: {
            color: '#CBD5E1',
          },
        },
      },
      series: [
        {
          name: 'Productivity Radar',
          type: 'radar',
          data: [
            {
              value: selectedRep.radar_values,
              name: selectedRep.full_name,
              symbol: 'circle',
              symbolSize: 6,
              itemStyle: {
                color: '#D32F2F', // Official Nerolac Red
              },
              lineStyle: {
                color: '#D32F2F',
                width: 2,
              },
              areaStyle: {
                color: 'rgba(211, 47, 47, 0.20)', // Subtle translucent red fill
              },
            },
            {
              value: teamBenchmark,
              name: 'Team Benchmark Average',
              symbol: 'rect',
              symbolSize: 5,
              itemStyle: {
                color: '#2563EB', // Corporate Royal Blue
              },
              lineStyle: {
                color: '#2563EB',
                width: 1.5,
                type: 'dashed',
              },
              areaStyle: {
                color: 'rgba(37, 99, 235, 0.08)',
              },
            },
          ],
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
  }, [selectedRep, indicators, teamBenchmark]);

  if (isLoading) {
    return (
      <div
        id="rep-radar-loading"
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
        Loading Sales Officer Radar Diagnostics...
      </div>
    );
  }

  if (!selectedRep) {
    return null;
  }

  const tierBadgeStyle =
    selectedRep.performance_tier === 'TOP_PERFORMER'
      ? { bg: '#ECFDF5', border: '#A7F3D0', text: '#065F46', label: 'Top Performer (>=85)' }
      : selectedRep.performance_tier === 'SOLID_PERFORMER'
        ? { bg: '#EFF6FF', border: '#BFDBFE', text: '#1E40AF', label: 'Solid Performer (70-84)' }
        : selectedRep.performance_tier === 'NEEDS_IMPROVEMENT'
          ? {
              bg: '#FFFBEB',
              border: '#FDE68A',
              text: '#92400E',
              label: 'Needs Improvement (55-69)',
            }
          : {
              bg: '#FEF2F2',
              border: '#FECACA',
              text: '#991B1B',
              label: 'Critical Underperformer (<55)',
            };

  const quadrantDetails: Record<
    string,
    { label: string; icon: string; bg: string; color: string; border: string }
  > = {
    STARS: {
      label: 'Stars',
      icon: '⭐',
      bg: '#ECFDF5',
      color: '#065F46',
      border: '#A7F3D0',
    },
    HEAVY_HITTERS: {
      label: 'Heavy Hitters',
      icon: '⚡',
      bg: '#EFF6FF',
      color: '#1E40AF',
      border: '#BFDBFE',
    },
    RAMP_UP: {
      label: 'Ramp-Up',
      icon: '🌱',
      bg: '#FFFBEB',
      color: '#92400E',
      border: '#FDE68A',
    },
    VALUE_DESTROYERS: {
      label: 'Value Destroyers',
      icon: '⚠️',
      bg: '#FEF2F2',
      color: '#991B1B',
      border: '#FECACA',
    },
  };

  const currentRepQuadrant = repQuadrantMap?.[selectedRep.employee_id];

  return (
    <div
      id="rep-radar-chart-section"
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '4px',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        boxSizing: 'border-box',
      }}
    >
      {/* Section Header & Officer Dropdown */}
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
              PRODUCTIVITY RADAR
            </span>
            <span style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A' }}>
              6-Axis Sales Rep Performance Spectrum
            </span>
          </div>
          <p style={{ fontSize: '12px', color: '#64748B', margin: '4px 0 0 0' }}>
            Weighted benchmark index comparing individual field officer execution against territory
            medians
          </p>
        </div>

        {/* Rep Selector Dropdown & Active Sync Indicators */}
        <div
          style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label
              htmlFor="sales-rep-select"
              style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}
            >
              Sales Officer:
            </label>
            <select
              id="sales-rep-select"
              value={activeRepId}
              onChange={(e) => handleRepChange(e.target.value)}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                color: '#0F172A',
                backgroundColor: '#F8FAFC',
                border: '1px solid #CBD5E1',
                borderRadius: '4px',
                outline: 'none',
                cursor: 'pointer',
                minWidth: '220px',
              }}
            >
              {scorecards.map((rep) => {
                const qKey = repQuadrantMap?.[rep.employee_id];
                const isMatch = activeQuadrantFilter !== 'ALL' && qKey === activeQuadrantFilter;
                return (
                  <option key={rep.employee_id} value={rep.employee_id}>
                    {rep.full_name} ({rep.designation}) — {rep.overall_score.toFixed(1)}
                    {isMatch ? ' ★' : ''}
                  </option>
                );
              })}
            </select>
          </div>

          {activeQuadrantFilter !== 'ALL' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '10px', color: '#64748B' }}>Quadrant Filter:</span>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  backgroundColor: '#0F172A',
                  color: '#FFFFFF',
                  padding: '1px 6px',
                  borderRadius: '3px',
                }}
              >
                {activeQuadrantFilter}
              </span>
              <button
                type="button"
                onClick={() => onQuadrantChange?.('ALL')}
                style={{
                  fontSize: '10px',
                  color: '#D32F2F',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0,
                }}
              >
                Reset
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Layout: Radar Chart + Officer Profile Panel */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(320px, 1.3fr) minmax(280px, 1fr)',
          gap: '24px',
          alignItems: 'center',
          flex: 1,
        }}
      >
        {/* ECharts 6-Axis Radar Container */}
        <div
          id="echarts-radar-container"
          ref={chartRef}
          style={{
            width: '100%',
            height: '400px',
          }}
        />

        {/* Selected Officer Detailed Scorecard */}
        <div
          style={{
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '4px',
            padding: '16px',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {/* Officer identity banner */}
          <div
            style={{
              borderBottom: '1px solid #E2E8F0',
              paddingBottom: '12px',
              marginBottom: '12px',
            }}
          >
            <div
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}
            >
              <div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A' }}>
                  {selectedRep.full_name}
                </div>
                <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
                  {selectedRep.employee_code} • {selectedRep.designation}
                </div>
                <div style={{ fontSize: '11px', color: '#475569', marginTop: '1px' }}>
                  {selectedRep.territory_name}
                </div>
              </div>

              {/* Overall composite index score */}
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A' }}>
                  {selectedRep.overall_score.toFixed(1)}
                </div>
                <div style={{ fontSize: '10px', color: '#64748B', textTransform: 'uppercase' }}>
                  Composite Score
                </div>
              </div>
            </div>

            {/* Performance tier pill & synchronized cross-links */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '3px 8px',
                  borderRadius: '3px',
                  backgroundColor: tierBadgeStyle.bg,
                  border: `1px solid ${tierBadgeStyle.border}`,
                  color: tierBadgeStyle.text,
                }}
              >
                {tierBadgeStyle.label}
              </span>

              {currentRepQuadrant && quadrantDetails[currentRepQuadrant] && (
                <button
                  type="button"
                  onClick={() => onQuadrantChange?.(currentRepQuadrant)}
                  title="View this quadrant in 4-Quadrant Scatter Matrix"
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '3px',
                    backgroundColor: quadrantDetails[currentRepQuadrant].bg,
                    border: `1px solid ${quadrantDetails[currentRepQuadrant].border}`,
                    color: quadrantDetails[currentRepQuadrant].color,
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span>{quadrantDetails[currentRepQuadrant].icon}</span>
                  <span>{quadrantDetails[currentRepQuadrant].label}</span>
                  <span style={{ fontSize: '10px' }}>↗</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => onDepotSelect?.(selectedRep.depot_id)}
                title={`Filter all views to ${selectedRep.depot_name}`}
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '3px 8px',
                  borderRadius: '3px',
                  backgroundColor: '#EFF6FF',
                  border: '1px solid #BFDBFE',
                  color: '#1E40AF',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <span>📍</span>
                <span>{selectedRep.depot_name}</span>
              </button>
            </div>
          </div>

          {/* 6 Core KPI Dimensions Table */}
          <div style={{ fontSize: '11px' }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto auto',
                gap: '8px',
                fontWeight: 700,
                color: '#64748B',
                paddingBottom: '6px',
                borderBottom: '1px solid #E2E8F0',
              }}
            >
              <span>KPI DIMENSION</span>
              <span>SCORE</span>
              <span>WEIGHT</span>
            </div>

            {[
              {
                name: 'Sales Achievement %',
                score: selectedRep.kpi_breakdown.sales_score,
                weight: weights.sales || 0.3,
              },
              {
                name: 'Collections %',
                score: selectedRep.kpi_breakdown.collections_score,
                weight: weights.collections || 0.2,
              },
              {
                name: 'Dealer Beat Coverage %',
                score: selectedRep.kpi_breakdown.coverage_score,
                weight: weights.coverage || 0.15,
              },
              {
                name: 'New Product Conversions',
                score: selectedRep.kpi_breakdown.conversions_score,
                weight: weights.conversions || 0.15,
              },
              {
                name: 'Quarterly Reviews %',
                score: selectedRep.kpi_breakdown.reviews_score,
                weight: weights.reviews || 0.1,
              },
              {
                name: 'WhatsApp Discipline %',
                score: selectedRep.kpi_breakdown.whatsapp_discipline_score,
                weight: weights.whatsapp_discipline || 0.1,
              },
            ].map((kpi) => (
              <div
                key={kpi.name}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr auto auto',
                  gap: '8px',
                  alignItems: 'center',
                  padding: '6px 0',
                  borderBottom: '1px solid #F1F5F9',
                }}
              >
                <span style={{ color: '#334155', fontWeight: 500 }}>{kpi.name}</span>
                <span
                  style={{
                    fontWeight: 700,
                    color: kpi.score >= 85 ? '#047857' : kpi.score >= 70 ? '#1E40AF' : '#D32F2F',
                  }}
                >
                  {kpi.score.toFixed(1)}
                </span>
                <span style={{ color: '#94A3B8' }}>{(kpi.weight * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
