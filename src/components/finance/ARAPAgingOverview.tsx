'use client';

import React from 'react';

export interface AgingBucketSummary {
  bucket_label: string;
  bucket_code: string;
  ar_amount_bdt: number;
  ap_amount_bdt: number;
  net_exposure_bdt: number;
  risk_level: string;
}

export interface AgingEntityRecord {
  aging_id: number;
  entry_type: string;
  entity_code: string;
  entity_name: string;
  depot_id: string;
  current_amount_bdt: number;
  days_1_30_bdt: number;
  days_31_60_bdt: number;
  days_61_90_bdt: number;
  days_90_plus_bdt: number;
  total_outstanding_bdt: number;
  as_of_date: string;
}

interface ARAPAgingOverviewProps {
  totalAR: number;
  totalAP: number;
  netWorkingCapital: number;
  dso: number;
  dpo: number;
  buckets: AgingBucketSummary[];
  entities: AgingEntityRecord[];
  isLoading?: boolean;
}

export function ARAPAgingOverview({
  totalAR,
  totalAP,
  netWorkingCapital,
  dso,
  dpo,
  buckets,
  entities,
  isLoading = false,
}: ARAPAgingOverviewProps) {
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
            AR / AP Working Capital &amp; Aging Schedule
          </h3>
          <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
            Sorted dealer receivables and vendor obligations across 0–30, 31–60, 61–90, and 90+ day
            intervals.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '16px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11px', color: '#64748B' }}>DSO (Sales)</div>
            <div
              className="tabular-nums"
              style={{ fontSize: '15px', fontWeight: 700, color: '#1E3A8A' }}
            >
              {dso.toFixed(1)} Days
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11px', color: '#64748B' }}>DPO (Payables)</div>
            <div
              className="tabular-nums"
              style={{ fontSize: '15px', fontWeight: 700, color: '#475569' }}
            >
              {dpo.toFixed(1)} Days
            </div>
          </div>
        </div>
      </div>

      {/* Aging Bucket Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        {buckets.map((b) => {
          const riskColor =
            b.risk_level === 'CRITICAL'
              ? '#DC2626'
              : b.risk_level === 'HIGH'
                ? '#D97706'
                : b.risk_level === 'MODERATE'
                  ? '#2563EB'
                  : '#059669';

          return (
            <div
              key={b.bucket_code}
              id={`aging-bucket-${b.bucket_code}`}
              style={{
                backgroundColor: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '4px',
                padding: '12px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px',
                }}
              >
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A' }}>
                  {b.bucket_label}
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    color: riskColor,
                    backgroundColor: '#FFFFFF',
                    border: '1px solid #CBD5E1',
                    padding: '1px 5px',
                    borderRadius: '3px',
                  }}
                >
                  {b.risk_level}
                </span>
              </div>

              <div style={{ fontSize: '11px', color: '#64748B', marginBottom: '2px' }}>
                Receivables (AR):{' '}
                <strong className="tabular-nums" style={{ color: '#0F172A' }}>
                  ৳{formatBDT(b.ar_amount_bdt)}
                </strong>
              </div>
              <div style={{ fontSize: '11px', color: '#64748B', marginBottom: '4px' }}>
                Payables (AP):{' '}
                <strong className="tabular-nums" style={{ color: '#D32F2F' }}>
                  (৳{formatBDT(b.ap_amount_bdt)})
                </strong>
              </div>

              <div
                style={{
                  borderTop: '1px solid #E2E8F0',
                  paddingTop: '6px',
                  fontSize: '11px',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span style={{ color: '#475569' }}>Net Gap:</span>
                <span
                  className="tabular-nums"
                  style={{
                    fontWeight: 700,
                    color: b.net_exposure_bdt >= 0 ? '#059669' : '#DC2626',
                  }}
                >
                  ৳{formatBDT(b.net_exposure_bdt)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Entity Details Table */}
      <div style={{ overflowX: 'auto', border: '1px solid #E2E8F0', borderRadius: '4px' }}>
        <table
          id="ar-ap-entities-table"
          className="corporate-table tabular-nums"
          style={{ width: '100%', minWidth: '850px' }}
        >
          <thead>
            <tr>
              <th style={{ width: '12%' }}>Type</th>
              <th style={{ width: '25%' }}>Dealer / Supplier</th>
              <th style={{ width: '8%' }}>Depot</th>
              <th style={{ textAlign: 'right', width: '12%' }}>0–30 Days</th>
              <th style={{ textAlign: 'right', width: '12%' }}>31–60 Days</th>
              <th style={{ textAlign: 'right', width: '12%' }}>61–90 Days</th>
              <th style={{ textAlign: 'right', width: '12%' }}>90+ Days</th>
              <th style={{ textAlign: 'right', width: '15%' }}>Total Outstanding</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '24px', color: '#64748B' }}>
                  Loading aging ledger...
                </td>
              </tr>
            ) : entities && entities.length > 0 ? (
              entities.map((e) => (
                <tr key={e.aging_id} id={`entity-row-${e.aging_id}`}>
                  <td>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        backgroundColor: e.entry_type === 'RECEIVABLE' ? '#EFF6FF' : '#FEF2F2',
                        color: e.entry_type === 'RECEIVABLE' ? '#2563EB' : '#DC2626',
                        border: '1px solid #CBD5E1',
                        padding: '1px 6px',
                        borderRadius: '3px',
                      }}
                    >
                      {e.entry_type}
                    </span>
                  </td>
                  <td style={{ fontWeight: 500, color: '#0F172A' }}>{e.entity_name}</td>
                  <td style={{ color: '#64748B', fontSize: '12px' }}>{e.depot_id}</td>
                  <td className="tabular-nums" style={{ textAlign: 'right' }}>
                    ৳{formatBDT(e.current_amount_bdt + e.days_1_30_bdt)}
                  </td>
                  <td className="tabular-nums" style={{ textAlign: 'right' }}>
                    ৳{formatBDT(e.days_31_60_bdt)}
                  </td>
                  <td className="tabular-nums" style={{ textAlign: 'right' }}>
                    ৳{formatBDT(e.days_61_90_bdt)}
                  </td>
                  <td
                    className="tabular-nums"
                    style={{
                      textAlign: 'right',
                      color: e.days_90_plus_bdt > 0 ? '#DC2626' : '#334155',
                      fontWeight: e.days_90_plus_bdt > 0 ? 700 : 400,
                    }}
                  >
                    ৳{formatBDT(e.days_90_plus_bdt)}
                  </td>
                  <td
                    className="tabular-nums"
                    style={{
                      textAlign: 'right',
                      fontWeight: 700,
                      color: e.entry_type === 'RECEIVABLE' ? '#0F172A' : '#D32F2F',
                    }}
                  >
                    ৳{formatBDT(e.total_outstanding_bdt)}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '24px', color: '#64748B' }}>
                  No active aging records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
