'use client';

import React, { useState } from 'react';

export interface SupplierPurchaseRecord {
  procurement_id: number;
  material_code: string;
  material_name: string;
  supplier_name: string;
  depot_id: string;
  purchase_date: string;
  quantity: number;
  unit_cost_bdt: number;
  benchmark_unit_cost_bdt: number;
  min_unit_cost_bdt: number;
  max_unit_cost_bdt: number;
  variance_pct: number;
  is_flagged: boolean;
  severity_color: string;
}

interface SupplierVarianceTableProps {
  records: SupplierPurchaseRecord[];
  flaggedCount: number;
  totalEvaluated: number;
  isLoading?: boolean;
}

export function SupplierVarianceTable({
  records,
  flaggedCount,
  totalEvaluated,
  isLoading = false,
}: SupplierVarianceTableProps) {
  const [filterMaterial, setFilterMaterial] = useState<string>('ALL');

  const filteredRecords =
    filterMaterial === 'ALL' ? records : records.filter((r) => r.material_code === filterMaterial);

  const uniqueMaterials = Array.from(new Set(records.map((r) => r.material_code)));

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '6px',
        overflow: 'hidden',
        marginTop: '24px',
      }}
    >
      {/* Table Header & Controls */}
      <div
        style={{
          padding: '16px',
          borderBottom: '1px solid #E2E8F0',
          backgroundColor: '#F8FAFC',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h3
              style={{
                fontSize: '14px',
                fontWeight: 700,
                color: '#0F172A',
              }}
            >
              Raw Material Supplier Price Spread Analysis
            </h3>
            {flaggedCount > 0 && (
              <span
                id="flagged-count-badge"
                style={{
                  backgroundColor: '#FEF3C7',
                  color: '#D97706',
                  border: '1px solid #FDE68A',
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '12px',
                }}
              >
                {flaggedCount} Spreads &gt; 5% Flagged
              </span>
            )}
          </div>
          <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
            Identifies vendor price spreads for resins, pigments (TiO₂), solvents, and packaging.
          </p>
        </div>

        {/* Filter by Material Code */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '12px', color: '#475569', fontWeight: 500 }}>
            Material Filter:
          </label>
          <select
            value={filterMaterial}
            onChange={(e) => setFilterMaterial(e.target.value)}
            style={{
              fontSize: '12px',
              padding: '4px 8px',
              borderRadius: '4px',
              border: '1px solid #CBD5E1',
              backgroundColor: '#FFFFFF',
              color: '#0F172A',
              outline: 'none',
            }}
          >
            <option value="ALL">All Raw Materials ({uniqueMaterials.length})</option>
            {uniqueMaterials.map((mat) => (
              <option key={mat} value={mat}>
                {mat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table View */}
      <div style={{ overflowX: 'auto' }}>
        <table
          id="supplier-variance-table"
          className="corporate-table tabular-nums"
          style={{ width: '100%', minWidth: '950px' }}
        >
          <thead>
            <tr>
              <th style={{ width: '12%' }}>Material Code</th>
              <th style={{ width: '22%' }}>Material Name</th>
              <th style={{ width: '20%' }}>Supplier / Vendor</th>
              <th style={{ width: '8%' }}>Depot</th>
              <th style={{ textAlign: 'right', width: '10%' }}>Quantity</th>
              <th style={{ textAlign: 'right', width: '10%' }}>Unit Cost (BDT)</th>
              <th style={{ textAlign: 'right', width: '10%' }}>Benchmark (BDT)</th>
              <th style={{ textAlign: 'center', width: '12%' }}>Price Spread</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: '#64748B' }}>
                  Loading procurement register...
                </td>
              </tr>
            ) : filteredRecords.length > 0 ? (
              filteredRecords.map((r) => {
                const isFlagged = r.is_flagged || r.variance_pct > 5.0;

                return (
                  <tr
                    key={r.procurement_id}
                    id={`procurement-row-${r.procurement_id}`}
                    style={{
                      backgroundColor: isFlagged ? '#FFFBEB' : '#FFFFFF',
                      borderBottom: '1px solid #E2E8F0',
                    }}
                  >
                    {/* Material Code */}
                    <td style={{ fontWeight: 600, color: '#0F172A' }}>{r.material_code}</td>

                    {/* Material Name */}
                    <td style={{ color: '#334155' }}>{r.material_name}</td>

                    {/* Supplier Name */}
                    <td style={{ color: '#0F172A', fontWeight: 500 }}>{r.supplier_name}</td>

                    {/* Depot */}
                    <td style={{ color: '#64748B', fontSize: '12px' }}>{r.depot_id}</td>

                    {/* Quantity */}
                    <td className="tabular-nums" style={{ textAlign: 'right', color: '#334155' }}>
                      {new Intl.NumberFormat('en-BD').format(r.quantity)}
                    </td>

                    {/* Unit Cost BDT */}
                    <td
                      className="tabular-nums"
                      style={{
                        textAlign: 'right',
                        fontWeight: 600,
                        color: isFlagged ? '#D97706' : '#0F172A',
                      }}
                    >
                      ৳{r.unit_cost_bdt.toFixed(2)}
                    </td>

                    {/* Benchmark BDT */}
                    <td className="tabular-nums" style={{ textAlign: 'right', color: '#64748B' }}>
                      ৳{r.benchmark_unit_cost_bdt.toFixed(2)}
                    </td>

                    {/* Variance Spread & Warm Amber Badge */}
                    <td style={{ textAlign: 'center' }}>
                      {isFlagged ? (
                        <span
                          className="badge-variance-amber"
                          style={{
                            backgroundColor: '#FEF3C7',
                            color: '#D97706',
                            border: '1px solid #FDE68A',
                            borderRadius: '4px',
                            padding: '3px 8px',
                            fontWeight: 700,
                            fontSize: '11px',
                          }}
                        >
                          +{r.variance_pct.toFixed(1)}% SPREAD
                        </span>
                      ) : (
                        <span
                          className="badge-variance-normal"
                          style={{
                            backgroundColor: '#F1F5F9',
                            color: '#475569',
                            border: '1px solid #E2E8F0',
                            borderRadius: '4px',
                            padding: '3px 8px',
                            fontSize: '11px',
                            fontWeight: 500,
                          }}
                        >
                          +{r.variance_pct.toFixed(1)}% (Normal)
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: '#64748B' }}>
                  No procurement records matching selected filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
