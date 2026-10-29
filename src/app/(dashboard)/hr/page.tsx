'use client';

import React, { useState, useEffect, useContext } from 'react';
import { DashboardContext } from '@/context/DashboardContext';
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
  const dashboard = useContext(DashboardContext);
  const [localPeriod, setLocalPeriod] = useState<string>('2024-M03');
  const [localDepot, setLocalDepot] = useState<string>('ALL');

  const selectedDepot = dashboard ? dashboard.selectedDepot : localDepot;
  const setSelectedDepot = dashboard ? dashboard.setSelectedDepot : setLocalDepot;
  const [selectedPeriod, setSelectedPeriod] = useState<string>('2024-M03');

  // Synchronized rep & quadrant states
  const [selectedRepId, setSelectedRepId] = useState<string>('');
  const [activeQuadrantFilter, setActiveQuadrantFilter] = useState<string>('ALL');

  // Synchronize period with global dashboard fiscal period if in FY 2024
  useEffect(() => {
    if (dashboard && dashboard.selectedYear === 2024) {
      if (dashboard.selectedMonth === 1) setSelectedPeriod('2024-M01');
      else if (dashboard.selectedMonth === 2) setSelectedPeriod('2024-M02');
      else if (dashboard.selectedMonth === 3) setSelectedPeriod('2024-M03');
    }
  }, [dashboard?.selectedYear, dashboard?.selectedMonth]);

  const handlePeriodChange = (val: string) => {
    setSelectedPeriod(val);
    if (dashboard) {
      if (val === '2024-M01') dashboard.setSelectedMonth(1);
      else if (val === '2024-M02') dashboard.setSelectedMonth(2);
      else if (val === '2024-M03') dashboard.setSelectedMonth(3);
    }
  };

  const [capacityData, setCapacityData] = useState<ManpowerResponse | null>(null);
  const [kpiData, setKpiData] = useState<KPIResponse | null>(null);
  const [scatterData, setScatterData] = useState<ScatterResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Map employee_id -> quadrant from scatter data
  const repQuadrantMap = React.useMemo(() => {
    const map: Record<string, string> = {};
    if (scatterData?.points) {
      for (const p of scatterData.points) {
        map[p.employee_id] = p.quadrant;
      }
    }
    return map;
  }, [scatterData]);

  // Sync selected rep when scorecards load or change
  useEffect(() => {
    if (kpiData?.scorecards && kpiData.scorecards.length > 0) {
      if (!kpiData.scorecards.some((s) => s.employee_id === selectedRepId)) {
        setSelectedRepId(kpiData.scorecards[0].employee_id);
      }
    }
  }, [kpiData, selectedRepId]);

  const handleQuadrantChange = (quadrant: string) => {
    setActiveQuadrantFilter(quadrant);
    if (quadrant !== 'ALL' && scatterData?.points) {
      const repInQuad = scatterData.points.find((p) => p.quadrant === quadrant);
      if (repInQuad) {
        setSelectedRepId(repInQuad.employee_id);
      }
    }
  };

  const handleResetAll = () => {
    setSelectedDepot('ALL');
    handlePeriodChange('2024-M03');
    setActiveQuadrantFilter('ALL');
    if (kpiData?.scorecards && kpiData.scorecards.length > 0) {
      setSelectedRepId(kpiData.scorecards[0].employee_id);
    }
  };

  // Derive selected officer information for cross-component context
  const selectedScorecard = kpiData?.scorecards.find((s) => s.employee_id === selectedRepId);
  const selectedOfficerInfo = selectedScorecard
    ? {
        name: selectedScorecard.full_name,
        depotId: selectedScorecard.depot_id,
        depotName: selectedScorecard.depot_name,
        territoryName: selectedScorecard.territory_name,
      }
    : null;

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
              onChange={(e) => handlePeriodChange(e.target.value)}
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
            id="reset-all-filters-btn"
            onClick={handleResetAll}
            title="Reset period, regional hub, quadrant, and rep filters to system defaults"
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              backgroundColor: '#F8FAFC',
              color: '#475569',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Reset All Filters
          </button>

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
        {/* Card 1: Vacant Territories Deficit (Clickable to jump to pipeline) */}
        <div
          onClick={() => {
            document
              .getElementById('vacant-territories-section')
              ?.scrollIntoView({ behavior: 'smooth' });
          }}
          role="button"
          tabIndex={0}
          title="Click to jump to 39 Vacant Territory Justification Engine"
          style={{
            cursor: 'pointer',
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #D32F2F',
            borderRadius: '4px',
            padding: '16px',
            fontVariantNumeric: 'tabular-nums',
            transition: 'box-shadow 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
              VACANT TERRITORIES (CAPACITY DEFICIT)
            </span>
            <span style={{ fontSize: '12px', color: '#94A3B8' }}>↓</span>
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

        {/* Card 2: Unlocked Revenue Potential (Clickable to jump to pipeline) */}
        <div
          onClick={() => {
            document
              .getElementById('vacant-territories-section')
              ?.scrollIntoView({ behavior: 'smooth' });
          }}
          role="button"
          tabIndex={0}
          title="Click to view ROI Payback Chips for expansion pipeline"
          style={{
            cursor: 'pointer',
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #059669',
            borderRadius: '4px',
            padding: '16px',
            fontVariantNumeric: 'tabular-nums',
            transition: 'box-shadow 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
              UNLOCKED MONTHLY SALES POTENTIAL
            </span>
            <span style={{ fontSize: '12px', color: '#94A3B8' }}>↓</span>
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

        {/* Card 3: Active Sales Officers Evaluated (Clickable to toggle Top Performers) */}
        <div
          onClick={() => {
            handleQuadrantChange(activeQuadrantFilter === 'STARS' ? 'ALL' : 'STARS');
            document
              .getElementById('rep-radar-chart-section')
              ?.scrollIntoView({ behavior: 'smooth' });
          }}
          role="button"
          tabIndex={0}
          title="Click to toggle Top Performers (Stars) filter across Radar and Scatter Matrix"
          style={{
            cursor: 'pointer',
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #2563EB',
            borderRadius: '4px',
            padding: '16px',
            fontVariantNumeric: 'tabular-nums',
            transition: 'box-shadow 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
              ACTIVE SALES OFFICERS EVALUATED
            </span>
            <span style={{ fontSize: '11px', color: '#2563EB', fontWeight: 700 }}>
              {activeQuadrantFilter === 'STARS' ? 'Showing Stars ★' : 'Filter Stars ↗'}
            </span>
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
          title="2-Factor Capacity: Sales Revenue Quotient (Territory Target / 15 Lacs BDT) + Beat Workload Quotient (Active Dealers x Visit Frequency / 24 Days)"
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
          alignItems: 'stretch',
        }}
      >
        {/* ECharts 6-Axis Radar Chart */}
        <RepRadarChart
          scorecards={kpiData?.scorecards || []}
          indicators={kpiData?.indicators || []}
          teamBenchmark={kpiData?.team_benchmark_radar_values || []}
          weights={kpiData?.weights || {}}
          isLoading={isLoading}
          selectedRepId={selectedRepId}
          onSelectRep={setSelectedRepId}
          activeQuadrantFilter={activeQuadrantFilter}
          onQuadrantChange={handleQuadrantChange}
          repQuadrantMap={repQuadrantMap}
          onDepotSelect={setSelectedDepot}
        />

        {/* ECharts 4-Quadrant Scatter Plot */}
        <CTCScatterPlot
          points={scatterData?.points || []}
          quadrants={scatterData?.quadrants || []}
          medianCTC={scatterData?.median_ctc_bdt || 90000}
          medianMargin={scatterData?.median_contribution_margin_bdt || 600000}
          isLoading={isLoading}
          selectedRepId={selectedRepId}
          onSelectRep={setSelectedRepId}
          activeQuadrantFilter={activeQuadrantFilter}
          onQuadrantChange={handleQuadrantChange}
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

        <VacantTerritoryCards
          territories={capacityData?.territories || []}
          isLoading={isLoading}
          onDepotSelect={setSelectedDepot}
          selectedDepot={selectedDepot}
          selectedOfficerInfo={selectedOfficerInfo}
        />
      </div>
    </div>
  );
}
