'use client';

import React, { useState } from 'react';

export interface VacantTerritory {
  territory_id: string;
  territory_code: string;
  territory_name: string;
  depot_id: string;
  depot_name: string;
  district: string;
  territory_target_bdt: number;
  active_dealers: number;
  visit_frequency: number;
  sales_revenue_capacity: number;
  workload_capacity: number;
  combined_capacity: number;
  recommended_headcount: number;
  current_headcount: number;
  gap_headcount: number;
  estimated_monthly_cost_bdt: number;
  projected_monthly_revenue_bdt: number;
  projected_contribution_margin_bdt: number;
  roi_payback_months: number;
  priority: string;
  justification_summary: string;
}

interface VacantTerritoryCardsProps {
  territories: VacantTerritory[];
  isLoading?: boolean;
  onDepotSelect?: (depotId: string) => void;
  selectedDepot?: string;
  selectedOfficerInfo?: {
    name: string;
    depotId: string;
    depotName: string;
    territoryName: string;
  } | null;
}

export function VacantTerritoryCards({
  territories,
  isLoading = false,
  onDepotSelect,
  selectedDepot,
  selectedOfficerInfo,
}: VacantTerritoryCardsProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');

  if (isLoading) {
    return (
      <div
        id="vacant-territories-loading"
        style={{
          padding: '40px 20px',
          textAlign: 'center',
          backgroundColor: '#FFFFFF',
          borderRadius: '4px',
          border: '1px solid #E2E8F0',
          color: '#64748B',
          fontSize: '13px',
        }}
      >
        Loading 39 Vacant Territory Justification Models...
      </div>
    );
  }

  // Map common Bangladesh place name spelling aliases (modern vs. corporate ERP transliterations)
  const normalizeLocation = (str: string): string => {
    return str
      .toLowerCase()
      .replace(/chattogram/g, 'chittagong')
      .replace(/bogura/g, 'bogra')
      .replace(/barishal/g, 'barisal')
      .replace(/cumilla/g, 'comilla')
      .replace(/jashore/g, 'jessore')
      .replace(/cox's bazar|coxs bazar/g, 'coxsbazar')
      .trim();
  };

  const normalizedQuery = normalizeLocation(searchQuery);

  const filteredTerritories = territories.filter((t) => {
    const haystack = normalizeLocation(
      `${t.territory_name} ${t.district} ${t.depot_name} ${t.territory_code}`
    );
    const matchesSearch =
      normalizedQuery === '' ||
      haystack.includes(normalizedQuery) ||
      t.territory_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.district.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.depot_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.territory_code.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPriority =
      priorityFilter === 'ALL' || t.priority.toUpperCase() === priorityFilter.toUpperCase();
    return matchesSearch && matchesPriority;
  });

  return (
    <div id="vacant-territories-section">
      {/* Officer Territory Focus Banner */}
      {selectedOfficerInfo && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderLeft: '4px solid #2563EB',
            borderRadius: '4px',
            padding: '10px 16px',
            marginBottom: '16px',
            fontSize: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '15px' }}>🎯</span>
            <div>
              <span style={{ fontWeight: 600, color: '#475569' }}>Selected Officer Context: </span>
              <strong style={{ color: '#0F172A' }}>{selectedOfficerInfo.name}</strong>
              <span style={{ color: '#64748B' }}>
                {' '}
                is assigned to <strong>{selectedOfficerInfo.depotName}</strong> (
                {selectedOfficerInfo.territoryName})
              </span>
            </div>
          </div>

          {selectedDepot !== selectedOfficerInfo.depotId ? (
            <button
              type="button"
              onClick={() => onDepotSelect?.(selectedOfficerInfo.depotId)}
              style={{
                padding: '4px 10px',
                fontSize: '11px',
                fontWeight: 600,
                backgroundColor: '#EFF6FF',
                color: '#1E40AF',
                border: '1px solid #BFDBFE',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Filter 39 Sectors to {selectedOfficerInfo.depotName} ↗
            </button>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '11px', color: '#059669', fontWeight: 600 }}>
                ✓ Filtered to {selectedOfficerInfo.depotName}
              </span>
              <button
                type="button"
                onClick={() => onDepotSelect?.('ALL')}
                style={{
                  padding: '3px 8px',
                  fontSize: '11px',
                  fontWeight: 600,
                  backgroundColor: '#FFFFFF',
                  color: '#64748B',
                  border: '1px solid #CBD5E1',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                View All Hubs
              </button>
            </div>
          )}
        </div>
      )}

      {/* Header and Controls */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
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
            39 VACANT TERRITORIES
          </span>
          <span style={{ fontSize: '12px', color: '#64748B' }}>
            Showing {filteredTerritories.length} of {territories.length} expansion sectors
          </span>
        </div>

        {/* Filter Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Priority filter pills */}
          <div
            style={{
              display: 'inline-flex',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              overflow: 'hidden',
              backgroundColor: '#FFFFFF',
            }}
          >
            {['ALL', 'HIGH', 'MEDIUM', 'STRATEGIC'].map((p) => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                style={{
                  padding: '4px 10px',
                  fontSize: '11px',
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: priorityFilter === p ? '#0F172A' : '#FFFFFF',
                  color: priorityFilter === p ? '#FFFFFF' : '#475569',
                  transition: 'background-color 0.15s ease',
                }}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Search box with clear button */}
          <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
            <input
              id="territory-search-input"
              type="text"
              placeholder="Search district, territory, depot..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: '6px 28px 6px 12px',
                fontSize: '12px',
                border: '1px solid #CBD5E1',
                borderRadius: '4px',
                width: '240px',
                color: '#0F172A',
                backgroundColor: '#FFFFFF',
                outline: 'none',
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                title="Clear search"
                style={{
                  position: 'absolute',
                  right: '6px',
                  background: 'none',
                  border: 'none',
                  color: '#94A3B8',
                  cursor: 'pointer',
                  fontSize: '13px',
                  lineHeight: 1,
                  padding: '2px 4px',
                }}
              >
                ✕
              </button>
            )}
          </div>

          {(searchQuery !== '' || priorityFilter !== 'ALL') && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setPriorityFilter('ALL');
              }}
              style={{
                fontSize: '11px',
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
          )}
        </div>
      </div>

      {/* Grid of 39 Justification Cards */}
      <div
        id="vacant-territory-cards-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
          gap: '16px',
        }}
      >
        {filteredTerritories.map((item) => {
          const priorityColor =
            item.priority === 'HIGH'
              ? '#D32F2F'
              : item.priority === 'STRATEGIC'
                ? '#4F46E5'
                : '#D97706';

          return (
            <div
              key={item.territory_id}
              className="territory-card"
              data-territory-id={item.territory_id}
              style={{
                backgroundColor: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '4px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
              }}
            >
              {/* Top Banner */}
              <div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    marginBottom: '8px',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: '#0F172A',
                        lineHeight: 1.2,
                      }}
                    >
                      {item.territory_name}
                    </div>
                    <div
                      style={{
                        fontSize: '11px',
                        color: '#64748B',
                        marginTop: '3px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        flexWrap: 'wrap',
                      }}
                    >
                      <span>{item.district} District •</span>
                      <button
                        type="button"
                        onClick={() => onDepotSelect?.(item.depot_id)}
                        title={`Filter all dashboard views to ${item.depot_name}`}
                        style={{
                          background: '#F1F5F9',
                          border: '1px solid #CBD5E1',
                          borderRadius: '3px',
                          padding: '1px 6px',
                          fontSize: '10px',
                          fontWeight: 600,
                          color: '#2563EB',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '2px',
                        }}
                      >
                        <span>📍</span>
                        <span>{item.depot_name}</span>
                      </button>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '2px',
                        border: `1px solid ${priorityColor}33`,
                        color: priorityColor,
                        backgroundColor: `${priorityColor}11`,
                      }}
                    >
                      {item.priority}
                    </span>
                  </div>
                </div>

                {/* ROI Payback Chip (Prominently Rendered) */}
                <div style={{ marginBottom: '12px' }}>
                  <div
                    className="roi-payback-chip"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 10px',
                      borderRadius: '4px',
                      backgroundColor: '#ECFDF5',
                      border: '1px solid #A7F3D0',
                      color: '#065F46',
                      fontSize: '11px',
                      fontWeight: 700,
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    <span style={{ color: '#059669', fontSize: '13px' }}>⚡</span>
                    <span>{item.roi_payback_months.toFixed(1)} mo payback</span>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 500,
                        color: '#047857',
                        marginLeft: '4px',
                      }}
                    >
                      (BDT {(item.projected_contribution_margin_bdt / 100000).toFixed(1)}L
                      margin/mo)
                    </span>
                  </div>
                </div>

                {/* 2-Factor Capacity Metric Grid */}
                <div
                  style={{
                    backgroundColor: '#F8FAFC',
                    border: '1px solid #E2E8F0',
                    borderRadius: '4px',
                    padding: '10px',
                    marginBottom: '12px',
                  }}
                >
                  <div
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      color: '#64748B',
                      letterSpacing: '0.5px',
                      marginBottom: '8px',
                    }}
                  >
                    2-FACTOR CAPACITY FORMULA
                  </div>

                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '8px',
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '10px', color: '#64748B' }}>Sales Capacity</div>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>
                        {item.sales_revenue_capacity.toFixed(2)}
                      </div>
                      <div style={{ fontSize: '9px', color: '#94A3B8' }}>Target / 15 Lacs</div>
                    </div>

                    <div>
                      <div style={{ fontSize: '10px', color: '#64748B' }}>Workload Capacity</div>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>
                        {item.workload_capacity.toFixed(2)}
                      </div>
                      <div style={{ fontSize: '9px', color: '#94A3B8' }}>
                        {item.active_dealers} dlrs × {item.visit_frequency} / 24d
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      marginTop: '8px',
                      paddingTop: '6px',
                      borderTop: '1px dashed #CBD5E1',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      fontSize: '11px',
                    }}
                  >
                    <span style={{ color: '#475569', fontWeight: 600 }}>
                      Recommended Headcount:
                    </span>
                    <span
                      style={{
                        fontWeight: 700,
                        color: '#D32F2F',
                        backgroundColor: '#FEF2F2',
                        padding: '1px 6px',
                        borderRadius: '2px',
                        border: '1px solid #FECACA',
                      }}
                    >
                      +{item.recommended_headcount} Officer(s)
                    </span>
                  </div>
                </div>

                {/* Financial Summary */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '11px',
                    color: '#475569',
                    marginBottom: '10px',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  <div>
                    <span style={{ color: '#94A3B8' }}>Target: </span>
                    <span style={{ fontWeight: 600 }}>
                      BDT {(item.territory_target_bdt / 100000).toFixed(1)}L
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#94A3B8' }}>Cost: </span>
                    <span style={{ fontWeight: 600 }}>
                      BDT {(item.estimated_monthly_cost_bdt / 1000).toFixed(0)}k/mo
                    </span>
                  </div>
                </div>

                {/* Justification Narrative */}
                <div
                  style={{
                    fontSize: '11px',
                    color: '#64748B',
                    lineHeight: 1.4,
                    borderTop: '1px solid #F1F5F9',
                    paddingTop: '8px',
                  }}
                >
                  {item.justification_summary}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {filteredTerritories.length === 0 && (
        <div
          style={{
            padding: '30px',
            textAlign: 'center',
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            color: '#64748B',
            fontSize: '13px',
          }}
        >
          No vacant territories match &ldquo;{searchQuery}&rdquo;.
        </div>
      )}
    </div>
  );
}
