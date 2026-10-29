'use client';

import React, { useState, useMemo } from 'react';

export interface MRPProposalItem {
  indent_id: string;
  material_code: string;
  material_name: string;
  category: string;
  current_stock_kg: number;
  safety_stock_kg: number;
  lead_time_days: number;
  gross_requirement_kg: number;
  net_shortfall_kg: number;
  recommended_reorder_kg: number;
  unit_cost_bdt: number;
  estimated_po_cost_bdt: number;
  supplier_name: string;
  country_of_origin: string;
  alert_level: string;
  action_notes: string;
}

export interface MRPProposalsResponse {
  evaluation_date: string;
  total_materials_monitored: number;
  critical_alerts_count: number;
  total_recommended_po_bdt: number;
  proposals: MRPProposalItem[];
}

interface MRPActionTableProps {
  data: MRPProposalsResponse | null;
  isLoading?: boolean;
  selectedAlertFilter?: string;
  onAlertFilterChange?: (filter: string) => void;
}

type SortField =
  | 'indent_id'
  | 'material_code'
  | 'category'
  | 'current_stock_kg'
  | 'safety_stock_kg'
  | 'recommended_reorder_kg'
  | 'estimated_po_cost_bdt'
  | 'lead_time_days'
  | 'alert_level';

export function MRPActionTable({
  data,
  isLoading = false,
  selectedAlertFilter,
  onAlertFilterChange,
}: MRPActionTableProps) {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [localSelectedAlert, setLocalSelectedAlert] = useState<string>('ALL');
  const [sortField, setSortField] = useState<SortField>('alert_level');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const currentAlert = selectedAlertFilter !== undefined ? selectedAlertFilter : localSelectedAlert;

  const handleAlertSelect = (alertVal: string) => {
    setLocalSelectedAlert(alertVal);
    onAlertFilterChange?.(alertVal);
  };

  const categories = useMemo(() => {
    if (!data || !data.proposals) return ['ALL'];
    const unique = Array.from(new Set(data.proposals.map((p) => p.category)));
    return ['ALL', ...unique.sort()];
  }, [data]);

  const filteredAndSortedProposals = useMemo(() => {
    if (!data || !data.proposals) return [];

    let result = [...data.proposals];

    // Search filter
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      result = result.filter(
        (p) =>
          p.material_code.toLowerCase().includes(q) ||
          p.material_name.toLowerCase().includes(q) ||
          p.supplier_name.toLowerCase().includes(q) ||
          p.indent_id.toLowerCase().includes(q)
      );
    }

    // Category filter
    if (selectedCategory !== 'ALL') {
      result = result.filter((p) => p.category === selectedCategory);
    }

    // Alert filter
    if (currentAlert !== 'ALL') {
      result = result.filter((p) => p.alert_level === currentAlert);
    }

    // Sort
    result.sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      // Custom priority for alert level
      if (sortField === 'alert_level') {
        const priority: Record<string, number> = {
          CRITICAL_STOCKOUT_RISK: 4,
          REORDER_REQUIRED: 3,
          ADEQUATE_STOCK: 2,
          OVERSTOCKED: 1,
        };
        const pA = priority[a.alert_level] || 0;
        const pB = priority[b.alert_level] || 0;
        return sortDirection === 'asc' ? pA - pB : pB - pA;
      }

      if (typeof valA === 'string' && typeof valB === 'string') {
        return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }

      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortDirection === 'asc' ? valA - valB : valB - valA;
      }

      return 0;
    });

    return result;
  }, [data, searchTerm, selectedCategory, currentAlert, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Inline CSV Export Handler
  const exportToCSV = () => {
    if (!filteredAndSortedProposals.length) return;

    const headers = [
      'Indent ID',
      'Material Code',
      'Material Name',
      'Category',
      'Current Stock (KG)',
      'Safety Stock (KG)',
      '2-Month Gross Req (KG)',
      'Net Shortfall (KG)',
      'Recommended Reorder (KG)',
      'Unit Cost (BDT/KG)',
      'Estimated PO Cost (BDT)',
      'Lead Time (Days)',
      'Contracted Supplier',
      'Country of Origin',
      'Alert Level',
      'Action Notes',
    ];

    const rows = filteredAndSortedProposals.map((p) => [
      `"${p.indent_id}"`,
      `"${p.material_code}"`,
      `"${p.material_name.replace(/"/g, '""')}"`,
      `"${p.category}"`,
      p.current_stock_kg,
      p.safety_stock_kg,
      p.gross_requirement_kg,
      p.net_shortfall_kg,
      p.recommended_reorder_kg,
      p.unit_cost_bdt,
      p.estimated_po_cost_bdt,
      p.lead_time_days,
      `"${p.supplier_name.replace(/"/g, '""')}"`,
      `"${p.country_of_origin}"`,
      `"${p.alert_level}"`,
      `"${p.action_notes.replace(/"/g, '""')}"`,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    const dateStr = data?.evaluation_date || new Date().toISOString().slice(0, 10);
    link.setAttribute('download', `Nerolac_MRP_Reorder_Indents_${dateStr}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatNumber = (num: number, maximumFractionDigits = 0) =>
    new Intl.NumberFormat('en-BD', { maximumFractionDigits }).format(num);

  const formatCurrency = (amount: number) =>
    `৳${new Intl.NumberFormat('en-BD', {
      maximumFractionDigits: 0,
    }).format(amount)}`;

  const renderAlertBadge = (level: string) => {
    switch (level) {
      case 'CRITICAL_STOCKOUT_RISK':
        return (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#FEF2F2',
              color: '#991B1B',
              border: '1px solid #FECACA',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: '#DC2626',
              }}
            />
            CRITICAL SHORTFALL
          </span>
        );
      case 'REORDER_REQUIRED':
        return (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#FFFBEB',
              color: '#92400E',
              border: '1px solid #FDE68A',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: '#D97706',
              }}
            />
            REORDER REQUIRED
          </span>
        );
      case 'OVERSTOCKED':
        return (
          <span
            style={{
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600,
              backgroundColor: '#F1F5F9',
              color: '#475569',
              border: '1px solid #CBD5E1',
            }}
          >
            OVERSTOCKED
          </span>
        );
      case 'ADEQUATE_STOCK':
      default:
        return (
          <span
            style={{
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600,
              backgroundColor: '#ECFDF5',
              color: '#065F46',
              border: '1px solid #A7F3D0',
            }}
          >
            ADEQUATE STOCK
          </span>
        );
    }
  };

  return (
    <div
      id="mrp-action-table-container"
      style={{
        backgroundColor: '#FFFFFF',
        borderRadius: '6px',
        border: '1px solid #E2E8F0',
        padding: '20px',
        marginTop: '20px',
      }}
    >
      {/* Top Header & Summary */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
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
                borderRadius: '2px',
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
              Material Requirements Planning (MRP) Action Table
            </h2>
          </div>
          <div style={{ fontSize: '12px', color: '#64748B', marginTop: '4px' }}>
            Automated BOM explosion from 2-month forecast • Safety buffer calculations & supplier
            lead-times
          </div>
        </div>

        {/* Action Buttons: Export CSV */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            id="mrp-export-csv-btn"
            type="button"
            onClick={exportToCSV}
            disabled={!filteredAndSortedProposals.length}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#FFFFFF',
              color: '#D32F2F',
              border: '1px solid #D32F2F',
              padding: '6px 14px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 700,
              cursor: filteredAndSortedProposals.length ? 'pointer' : 'not-allowed',
              opacity: filteredAndSortedProposals.length ? 1 : 0.6,
              transition: 'background-color 0.15s ease',
            }}
          >
            <span>↓</span>
            <span>Export Reorder Indents (CSV)</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        {/* Search Input with Clear Button */}
        <div style={{ minWidth: '260px', flex: '1 1 260px', position: 'relative' }}>
          <input
            id="mrp-search-input"
            type="text"
            placeholder="Search material code, name, or vendor..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '7px 28px 7px 12px',
              fontSize: '13px',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              outline: 'none',
              backgroundColor: '#F8FAFC',
              color: '#0F172A',
              boxSizing: 'border-box',
            }}
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              title="Clear search"
              style={{
                position: 'absolute',
                right: '8px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                color: '#94A3B8',
                cursor: 'pointer',
                fontSize: '13px',
                lineHeight: 1,
                padding: '2px',
              }}
            >
              ✕
            </button>
          )}
        </div>

        {/* Category Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>Category:</span>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setSelectedCategory(cat)}
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '3px 8px',
                borderRadius: '4px',
                border: '1px solid',
                borderColor: selectedCategory === cat ? '#D32F2F' : '#E2E8F0',
                backgroundColor: selectedCategory === cat ? '#FEF2F2' : '#FFFFFF',
                color: selectedCategory === cat ? '#D32F2F' : '#475569',
                cursor: 'pointer',
              }}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Alert Status Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>Status:</span>
          {[
            { id: 'ALL', label: 'All' },
            { id: 'CRITICAL_STOCKOUT_RISK', label: 'Critical Shortfall' },
            { id: 'REORDER_REQUIRED', label: 'Reorder' },
            { id: 'ADEQUATE_STOCK', label: 'Adequate' },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => handleAlertSelect(item.id)}
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '3px 8px',
                borderRadius: '4px',
                border: '1px solid',
                borderColor: currentAlert === item.id ? '#0F172A' : '#E2E8F0',
                backgroundColor: currentAlert === item.id ? '#0F172A' : '#FFFFFF',
                color: currentAlert === item.id ? '#FFFFFF' : '#475569',
                cursor: 'pointer',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Reset Filter Action */}
        {(searchTerm !== '' || selectedCategory !== 'ALL' || currentAlert !== 'ALL') && (
          <button
            type="button"
            onClick={() => {
              setSearchTerm('');
              setSelectedCategory('ALL');
              handleAlertSelect('ALL');
            }}
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: '#D32F2F',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              textDecoration: 'underline',
              padding: '0 4px',
            }}
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* High-Density Action Table */}
      <div
        style={{
          overflowX: 'auto',
          border: '1px solid #E2E8F0',
          borderRadius: '4px',
        }}
      >
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '12px',
            textAlign: 'left',
          }}
        >
          <thead>
            <tr
              style={{
                backgroundColor: '#F8FAFC',
                borderBottom: '1px solid #CBD5E1',
                color: '#475569',
                fontWeight: 600,
                whiteSpace: 'nowrap',
              }}
            >
              <th
                onClick={() => handleSort('indent_id')}
                style={{ padding: '10px 12px', cursor: 'pointer' }}
              >
                Indent ID {sortField === 'indent_id' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th
                onClick={() => handleSort('material_code')}
                style={{ padding: '10px 12px', cursor: 'pointer' }}
              >
                Material Master{' '}
                {sortField === 'material_code' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th
                onClick={() => handleSort('category')}
                style={{ padding: '10px 12px', cursor: 'pointer' }}
              >
                Category {sortField === 'category' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th
                onClick={() => handleSort('current_stock_kg')}
                style={{ padding: '10px 12px', textAlign: 'right', cursor: 'pointer' }}
              >
                Current Stock (KG){' '}
                {sortField === 'current_stock_kg' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th
                onClick={() => handleSort('safety_stock_kg')}
                style={{ padding: '10px 12px', textAlign: 'right', cursor: 'pointer' }}
              >
                Safety Stock (KG){' '}
                {sortField === 'safety_stock_kg' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th
                onClick={() => handleSort('recommended_reorder_kg')}
                style={{ padding: '10px 12px', textAlign: 'right', cursor: 'pointer' }}
              >
                Reorder Indent (KG){' '}
                {sortField === 'recommended_reorder_kg'
                  ? sortDirection === 'asc'
                    ? '↑'
                    : '↓'
                  : ''}
              </th>
              <th
                onClick={() => handleSort('estimated_po_cost_bdt')}
                style={{ padding: '10px 12px', textAlign: 'right', cursor: 'pointer' }}
              >
                PO Value (BDT){' '}
                {sortField === 'estimated_po_cost_bdt' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th
                onClick={() => handleSort('lead_time_days')}
                style={{ padding: '10px 12px', textAlign: 'center', cursor: 'pointer' }}
              >
                Lead Time{' '}
                {sortField === 'lead_time_days' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th style={{ padding: '10px 12px' }}>Supplier / Origin</th>
              <th
                onClick={() => handleSort('alert_level')}
                style={{ padding: '10px 12px', cursor: 'pointer' }}
              >
                Status {sortField === 'alert_level' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th style={{ padding: '10px 12px' }}>Action Guidance</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={11} style={{ textAlign: 'center', padding: '32px', color: '#64748B' }}>
                  Loading MRP explosion calculations...
                </td>
              </tr>
            ) : filteredAndSortedProposals.length === 0 ? (
              <tr>
                <td colSpan={11} style={{ textAlign: 'center', padding: '32px', color: '#64748B' }}>
                  No material proposals match the selected filters.
                </td>
              </tr>
            ) : (
              filteredAndSortedProposals.map((item, idx) => (
                <tr
                  key={item.material_code}
                  style={{
                    backgroundColor: idx % 2 === 0 ? '#FFFFFF' : '#FAFAFA',
                    borderBottom: '1px solid #F1F5F9',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {/* Indent ID */}
                  <td style={{ padding: '8px 12px', fontWeight: 600, color: '#1E3A8A' }}>
                    {item.indent_id}
                  </td>

                  {/* Material Master */}
                  <td style={{ padding: '8px 12px' }}>
                    <div style={{ fontWeight: 600, color: '#0F172A' }}>{item.material_code}</div>
                    <div
                      style={{
                        fontSize: '11px',
                        color: '#64748B',
                        maxWidth: '200px',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {item.material_name}
                    </div>
                  </td>

                  {/* Category */}
                  <td style={{ padding: '8px 12px' }}>
                    <span
                      style={{
                        padding: '2px 6px',
                        backgroundColor: '#F1F5F9',
                        borderRadius: '3px',
                        fontSize: '10px',
                        fontWeight: 600,
                        color: '#475569',
                      }}
                    >
                      {item.category}
                    </span>
                  </td>

                  {/* Current Stock */}
                  <td
                    style={{
                      padding: '8px 12px',
                      textAlign: 'right',
                      fontWeight: 500,
                      color: '#0F172A',
                    }}
                  >
                    {formatNumber(item.current_stock_kg)} kg
                  </td>

                  {/* Safety Stock */}
                  <td style={{ padding: '8px 12px', textAlign: 'right', color: '#64748B' }}>
                    {formatNumber(item.safety_stock_kg)} kg
                  </td>

                  {/* Recommended Reorder */}
                  <td
                    style={{
                      padding: '8px 12px',
                      textAlign: 'right',
                      fontWeight: 700,
                      color: item.recommended_reorder_kg > 0 ? '#D32F2F' : '#059669',
                    }}
                  >
                    {item.recommended_reorder_kg > 0
                      ? `${formatNumber(item.recommended_reorder_kg)} kg`
                      : '0 kg'}
                  </td>

                  {/* PO Value BDT */}
                  <td
                    style={{
                      padding: '8px 12px',
                      textAlign: 'right',
                      fontWeight: 700,
                      color: '#0F172A',
                    }}
                  >
                    {formatCurrency(item.estimated_po_cost_bdt)}
                  </td>

                  {/* Lead Time */}
                  <td style={{ padding: '8px 12px', textAlign: 'center', color: '#64748B' }}>
                    {item.lead_time_days}d
                  </td>

                  {/* Supplier */}
                  <td style={{ padding: '8px 12px' }}>
                    <div style={{ fontWeight: 500, color: '#0F172A' }}>{item.supplier_name}</div>
                    <div style={{ fontSize: '10px', color: '#64748B' }}>
                      {item.country_of_origin}
                    </div>
                  </td>

                  {/* Status Badge */}
                  <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                    {renderAlertBadge(item.alert_level)}
                  </td>

                  {/* Action Guidance */}
                  <td
                    style={{
                      padding: '8px 12px',
                      fontSize: '11px',
                      color: '#475569',
                      maxWidth: '240px',
                    }}
                  >
                    {item.action_notes}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer Info */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '12px',
          fontSize: '11px',
          color: '#64748B',
        }}
      >
        <div>
          Showing <strong>{filteredAndSortedProposals.length}</strong> of{' '}
          <strong>{data?.total_materials_monitored || 0}</strong> raw material items
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <span>
            Critical Alerts:{' '}
            <strong style={{ color: '#DC2626' }}>{data?.critical_alerts_count || 0}</strong>
          </span>
          <span>
            Total Reorder Value:{' '}
            <strong style={{ color: '#0F172A' }}>
              {formatCurrency(data?.total_recommended_po_bdt || 0)}
            </strong>
          </span>
        </div>
      </div>
    </div>
  );
}
