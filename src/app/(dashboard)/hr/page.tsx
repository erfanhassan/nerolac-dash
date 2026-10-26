'use client';

import React, { useState, useEffect } from 'react';
import { VacantTerritoryCards, VacantTerritory } from '@/components/hr/VacantTerritoryCards';
import {
  RepRadarChart,
  EmployeeScorecard,
  RadarAxisIndicator,
} from '@/components/hr/RepRadarChart';
import { CTCScatterPlot, CTCScatterPoint, QuadrantSummary } from '@/components/hr/CTCScatterPlot';

interface ManpowerResponse {
  total_vacant_territories: number;
  total_recommended_headcount: number;
  total_monthly_target_bdt: number;
  total_projected_margin_bdt: number;
  average_payback_months: number;
  benchmark_sales_capacity_lac_bdt: number;
  benchmark_working_days: number;
  territories: VacantTerritory[];
}

interface KPIResponse {
  assessment_period: string;
  weights: Record<string, number>;
  indicators: RadarAxisIndicator[];
  team_benchmark_radar_values: number[];
  total_reps_evaluated: number;
  top_performers_count: number;
  solid_performers_count: number;
  needs_improvement_count: number;
  critical_count: number;
  scorecards: EmployeeScorecard[];
}

interface ScatterResponse {
  period: string;
  total_reps: number;
  median_ctc_bdt: number;
  median_contribution_margin_bdt: number;
  quadrants: QuadrantSummary[];
  points: CTCScatterPoint[];
}

export default function HRWorkforceIntelligencePage() {
  const [selectedPeriod, setSelectedPeriod] = useState<string>('2024-M03');
  const [selectedDepot, setSelectedDepot] = useState<string>('ALL');

  const [capacityData, setCapacityData] = useState<ManpowerResponse | null>(null);
  const [kpiData, setKpiData] = useState<KPIResponse | null>(null);
  const [scatterData, setScatterData] = useState<ScatterResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchHRData = async () => {
    setIsLoading(true);
    try {
      const depotQuery = selectedDepot !== 'ALL' ? `&depot_id=${selectedDepot}` : '';
      const depotQueryFirst = selectedDepot !== 'ALL' ? `?depot_id=${selectedDepot}` : '';

      // 1. Fetch 39 Vacant Territories & 2-Factor Capacity
      const capPromise = fetch(`/api/v1/hr/manpower-capacity${depotQueryFirst}`).then((r) =>
        r.ok ? r.json() : null
      );

      // 2. Fetch 0–100 Weighted KPI Scorecard & Radar specs
      const kpiPromise = fetch(
        `/api/v1/hr/kpi-scorecard?assessment_period=${selectedPeriod}${depotQuery}`
      ).then((r) => (r.ok ? r.json() : null));

      // 3. Fetch Fully-Loaded CTC vs Contribution Margin 4-Quadrant Scatter
      const scatterPromise = fetch(
        `/api/v1/hr/ctc-scatter-plot?period=${selectedPeriod}${depotQuery}`
      ).then((r) => (r.ok ? r.json() : null));

      const [capRes, kpiRes, scatterRes] = await Promise.all([
        capPromise,
        kpiPromise,
        scatterPromise,
      ]);

      setCapacityData(capRes);
      setKpiData(kpiRes);
      setScatterData(scatterRes);
    } catch (err) {
      // In corporate mode, cleanly handle error states
      console.error('Failed to load HR Workforce data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHRData();
  }, [selectedPeriod, selectedDepot]);

  // Derived KPI metrics
  const totalVacantCount = capacityData?.total_vacant_territories ?? 39;
  const totalRecommendedOfficers = capacityData?.total_recommended_headcount ?? 0;
  const totalMonthlyPotentialBDT = capacityData?.total_monthly_target_bdt ?? 0;
  const avgPaybackMonths = capacityData?.average_payback_months ?? 0;
  const totalRepsEvaluated = kpiData?.total_reps_evaluated ?? 0;
  const topPerformers = kpiData?.top_performers_count ?? 0;

  return (
    <div
      id="hr-workforce-container"
      style={{
        padding: '24px 32px',
        backgroundColor: '#FFFFFF',
        minHeight: '100%',
        color: '#0F172A',
      }}
    >
      {/* Page Title & Control Bar */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          paddingBottom: '20px',
          borderBottom: '1px solid #E2E8F0',
          marginBottom: '24px',
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
              MODULE 2
            </span>
            <h1
              style={{
                fontSize: '22px',
                fontWeight: 700,
                color: '#0F172A',
                letterSpacing: '-0.3px',
                margin: 0,
              }}
            >
              HR Workforce Intelligence
            </h1>
          </div>
          <p
            style={{
              fontSize: '13px',
              color: '#64748B',
              marginTop: '4px',
              marginBottom: 0,
            }}
          >
            2-Factor Capacity Models • 39 Vacant Territory Justifications • 6-Axis Rep Radar •
            4-Quadrant CTC vs Margin Matrix
          </p>
        </div>

        {/* Global Filter Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Assessment Period */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label
              htmlFor="period-select"
              style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}
            >
              Period:
            </label>
            <select
              id="period-select"
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
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
              }}
            >
              <option value="2024-M03">2024 - March (M03)</option>
              <option value="2024-M02">2024 - February (M02)</option>
              <option value="2024-M01">2024 - January (M01)</option>
            </select>
          </div>

          {/* Regional Supply Hub Depot */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label
              htmlFor="depot-select"
              style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}
            >
              Depot:
            </label>
            <select
              id="depot-select"
              value={selectedDepot}
              onChange={(e) => setSelectedDepot(e.target.value)}
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
              }}
            >
              <option value="ALL">All Hubs (Bangladesh Operations)</option>
              <option value="DEPOT_01">DEPOT_01: Dhaka Central</option>
              <option value="DEPOT_02">DEPOT_02: Chittagong Commercial</option>
              <option value="DEPOT_03">DEPOT_03: Sylhet Surma</option>
              <option value="DEPOT_04">DEPOT_04: Bogura North</option>
              <option value="DEPOT_05">DEPOT_05: Khulna Coastal</option>
              <option value="DEPOT_06">DEPOT_06: Barisal Delta</option>
              <option value="DEPOT_07">DEPOT_07: Rangpur Frontier</option>
              <option value="DEPOT_08">DEPOT_08: Mymensingh Valley</option>
            </select>
          </div>

          <button
            id="refresh-button"
            onClick={fetchHRData}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              backgroundColor: '#FFFFFF',
              color: '#D32F2F',
              border: '1px solid #D32F2F',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Executive KPI Summary Cards */}
      <div
        id="hr-kpi-summary-cards"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        {/* Card 1: Vacant Territories Deficit */}
        <div
          style={{
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #D32F2F',
            borderRadius: '4px',
            padding: '16px',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
            VACANT TERRITORIES (CAPACITY DEFICIT)
          </div>
          <div
            style={{
              fontSize: '24px',
              fontWeight: 800,
              color: '#0F172A',
              marginTop: '4px',
            }}
          >
            {totalVacantCount} Territories
          </div>
          <div style={{ fontSize: '11px', color: '#D32F2F', marginTop: '4px', fontWeight: 600 }}>
            +{totalRecommendedOfficers} Recommended Field Officers
          </div>
        </div>

        {/* Card 2: Unlocked Revenue Potential */}
        <div
          style={{
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #059669',
            borderRadius: '4px',
            padding: '16px',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
            UNLOCKED MONTHLY SALES POTENTIAL
          </div>
          <div
            style={{
              fontSize: '24px',
              fontWeight: 800,
              color: '#0F172A',
              marginTop: '4px',
            }}
          >
            BDT {(totalMonthlyPotentialBDT / 10000000).toFixed(2)} Cr
          </div>
          <div style={{ fontSize: '11px', color: '#059669', marginTop: '4px', fontWeight: 600 }}>
            Avg Payback: {avgPaybackMonths.toFixed(1)} Months
          </div>
        </div>

        {/* Card 3: Active Sales Officers Evaluated */}
        <div
          style={{
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #2563EB',
            borderRadius: '4px',
            padding: '16px',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
            ACTIVE SALES OFFICERS EVALUATED
          </div>
          <div
            style={{
              fontSize: '24px',
              fontWeight: 800,
              color: '#0F172A',
              marginTop: '4px',
            }}
          >
            {totalRepsEvaluated} Field Reps
          </div>
          <div style={{ fontSize: '11px', color: '#2563EB', marginTop: '4px', fontWeight: 600 }}>
            {topPerformers} Top Performers (&ge;85 Score)
          </div>
        </div>

        {/* Card 4: 2-Factor Benchmark Constants */}
        <div
          style={{
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #475569',
            borderRadius: '4px',
            padding: '16px',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
            2-FACTOR BENCHMARK STANDARDS
          </div>
          <div
            style={{
              fontSize: '20px',
              fontWeight: 800,
              color: '#0F172A',
              marginTop: '4px',
            }}
          >
            15L Target • 24 Days
          </div>
          <div style={{ fontSize: '11px', color: '#64748B', marginTop: '4px' }}>
            Sales Quotient &amp; Beat Workload Ratio
          </div>
        </div>
      </div>

      {/* Section 1: Productivity Radar & CTC Scatter Plot (Grid Layout) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))',
          gap: '24px',
          marginBottom: '32px',
        }}
      >
        {/* ECharts 6-Axis Radar Chart */}
        <RepRadarChart
          scorecards={kpiData?.scorecards || []}
          indicators={kpiData?.indicators || []}
          teamBenchmark={kpiData?.team_benchmark_radar_values || []}
          weights={kpiData?.weights || {}}
          isLoading={isLoading}
        />

        {/* ECharts 4-Quadrant Scatter Plot */}
        <CTCScatterPlot
          points={scatterData?.points || []}
          quadrants={scatterData?.quadrants || []}
          medianCTC={scatterData?.median_ctc_bdt || 90000}
          medianMargin={scatterData?.median_contribution_margin_bdt || 600000}
          isLoading={isLoading}
        />
      </div>

      {/* Section 2: 39 Vacant Territory Justification Cards with ROI Payback Chips */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '4px',
          padding: '24px',
        }}
      >
        <div style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                backgroundColor: '#0F172A',
                color: '#FFFFFF',
                padding: '2px 8px',
                borderRadius: '2px',
              }}
            >
              EXPANSION PIPELINE
            </span>
            <h2
              style={{
                fontSize: '18px',
                fontWeight: 700,
                color: '#0F172A',
                margin: 0,
              }}
            >
              39 Vacant Territory Justification Engine
            </h2>
          </div>
          <p style={{ fontSize: '12px', color: '#64748B', margin: '4px 0 0 0' }}>
            2-Factor Capacity calculations combining Sales Revenue Target (Territory Target / 15
            Lacs BDT) and Workload Beat Coverage (Active Dealers x Visit Frequency / 24 Days) with
            ROI Payback Chips
          </p>
        </div>

        <VacantTerritoryCards territories={capacityData?.territories || []} isLoading={isLoading} />
      </div>
    </div>
  );
}
