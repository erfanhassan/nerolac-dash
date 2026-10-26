'use client';

import React, { useState } from 'react';

export interface PnLTreeNode {
  id: string;
  label: string;
  level: number;
  category: string;
  volume_liters: number;
  revenue_bdt: number;
  cogs_bdt: number;
  gross_margin_bdt: number;
  gross_margin_pct: number;
  opex_bdt: number;
  ebitda_bdt: number;
  ebitda_pct: number;
  children?: PnLTreeNode[];
}

interface PnLTreeGridProps {
  data: PnLTreeNode[];
  isLoading?: boolean;
}

export function PnLTreeGrid({ data, isLoading = false }: PnLTreeGridProps) {
  // Track expanded nodes (all level 0 expanded by default)
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({
    div_architectural_coatings: true,
    div_industrial_coatings: true,
  });

  const toggleNode = (id: string) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const formatBDT = (val: number) => {
    return new Intl.NumberFormat('en-BD', {
      maximumFractionDigits: 0,
    }).format(val);
  };

  const formatLiters = (val: number) => {
    return new Intl.NumberFormat('en-BD', {
      maximumFractionDigits: 0,
    }).format(val);
  };

  const renderRow = (node: PnLTreeNode, depth: number = 0) => {
    const isExpanded = !!expandedNodes[node.id];
    const hasChildren = node.children && node.children.length > 0;
    const isDivision = node.level === 0;

    return (
      <React.Fragment key={node.id}>
        <tr
          id={`tree-row-${node.id}`}
          style={{
            backgroundColor: isDivision ? '#F8FAFC' : '#FFFFFF',
            fontWeight: isDivision ? 700 : 500,
            borderBottom: '1px solid #E2E8F0',
            cursor: hasChildren ? 'pointer' : 'default',
          }}
          onClick={() => hasChildren && toggleNode(node.id)}
        >
          {/* Label with Indent and Toggle Chevron */}
          <td
            style={{
              padding: '10px 12px',
              paddingLeft: `${16 + depth * 20}px`,
              color: isDivision ? '#0F172A' : '#334155',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {hasChildren ? (
                <span
                  style={{
                    display: 'inline-block',
                    width: '14px',
                    fontSize: '10px',
                    color: isDivision ? '#D32F2F' : '#64748B',
                    userSelect: 'none',
                  }}
                >
                  {isExpanded ? '▼' : '▶'}
                </span>
              ) : (
                <span style={{ display: 'inline-block', width: '14px' }} />
              )}
              <span>{node.label}</span>
              {isDivision && (
                <span
                  style={{
                    fontSize: '10px',
                    backgroundColor: '#E2E8F0',
                    color: '#475569',
                    padding: '1px 6px',
                    borderRadius: '3px',
                    fontWeight: 600,
                  }}
                >
                  DIVISION
                </span>
              )}
            </div>
          </td>

          {/* Volume (Liters) */}
          <td
            className="tabular-nums"
            style={{
              textAlign: 'right',
              padding: '10px 12px',
              color: '#334155',
            }}
          >
            {formatLiters(node.volume_liters)} L
          </td>

          {/* Net Revenue (BDT) */}
          <td
            className="tabular-nums"
            style={{
              textAlign: 'right',
              padding: '10px 12px',
              color: '#0F172A',
              fontWeight: isDivision ? 700 : 600,
            }}
          >
            ৳{formatBDT(node.revenue_bdt)}
          </td>

          {/* COGS (BDT) */}
          <td
            className="tabular-nums"
            style={{
              textAlign: 'right',
              padding: '10px 12px',
              color: '#D32F2F',
            }}
          >
            (৳{formatBDT(node.cogs_bdt)})
          </td>

          {/* Gross Margin (BDT) */}
          <td
            className="tabular-nums"
            style={{
              textAlign: 'right',
              padding: '10px 12px',
              color: node.gross_margin_bdt >= 0 ? '#059669' : '#D32F2F',
              fontWeight: 600,
            }}
          >
            ৳{formatBDT(node.gross_margin_bdt)}
          </td>

          {/* Gross Margin % */}
          <td
            className="tabular-nums"
            style={{
              textAlign: 'right',
              padding: '10px 12px',
              color: '#334155',
            }}
          >
            {node.gross_margin_pct.toFixed(1)}%
          </td>

          {/* OPEX (BDT) */}
          <td
            className="tabular-nums"
            style={{
              textAlign: 'right',
              padding: '10px 12px',
              color: '#64748B',
            }}
          >
            (৳{formatBDT(node.opex_bdt)})
          </td>

          {/* EBITDA (BDT) */}
          <td
            className="tabular-nums"
            style={{
              textAlign: 'right',
              padding: '10px 12px',
              color: node.ebitda_bdt >= 0 ? '#059669' : '#D32F2F',
              fontWeight: 700,
            }}
          >
            ৳{formatBDT(node.ebitda_bdt)}
          </td>

          {/* EBITDA % */}
          <td
            className="tabular-nums"
            style={{
              textAlign: 'right',
              padding: '10px 12px',
              color: '#0F172A',
              fontWeight: 600,
            }}
          >
            {node.ebitda_pct.toFixed(1)}%
          </td>
        </tr>

        {/* Child rows when node is expanded */}
        {hasChildren && isExpanded && node.children!.map((child) => renderRow(child, depth + 1))}
      </React.Fragment>
    );
  };

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '6px',
        overflow: 'hidden',
        marginTop: '16px',
      }}
    >
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #E2E8F0',
          backgroundColor: '#F8FAFC',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <h4
            style={{
              fontSize: '13px',
              fontWeight: 700,
              color: '#0F172A',
            }}
          >
            Segment P&L Breakdown (TanStack Tree Grid)
          </h4>
          <p style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
            Click any row to expand segment components (Volume, Revenue, COGS, EBITDA)
          </p>
        </div>
        <div style={{ fontSize: '11px', color: '#64748B' }}>
          Display: <strong>tabular-nums</strong>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table
          id="tanstack-tree-grid-table"
          className="corporate-table tabular-nums"
          style={{ width: '100%', minWidth: '850px' }}
        >
          <thead>
            <tr>
              <th style={{ width: '28%' }}>Hierarchy / Segment</th>
              <th style={{ textAlign: 'right', width: '10%' }}>Volume</th>
              <th style={{ textAlign: 'right', width: '12%' }}>Net Revenue</th>
              <th style={{ textAlign: 'right', width: '10%' }}>COGS</th>
              <th style={{ textAlign: 'right', width: '10%' }}>Gross Margin</th>
              <th style={{ textAlign: 'right', width: '6%' }}>GM %</th>
              <th style={{ textAlign: 'right', width: '9%' }}>OPEX</th>
              <th style={{ textAlign: 'right', width: '9%' }}>EBITDA</th>
              <th style={{ textAlign: 'right', width: '6%' }}>EBITDA %</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '32px', color: '#64748B' }}>
                  Loading Segment P&L data...
                </td>
              </tr>
            ) : data && data.length > 0 ? (
              data.map((node) => renderRow(node, 0))
            ) : (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '32px', color: '#64748B' }}>
                  No segment trial balance data found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
