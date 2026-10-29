'use client';

import React, { useState, useContext } from 'react';
import { DashboardContext } from '@/context/DashboardContext';

export interface TopBarProps {
  currentModuleTitle?: string;
  onDepotChange?: (depot: string) => void;
  onFiscalPeriodChange?: (period: string) => void;
  onFiscalYearChange?: (fy: string) => void;
}

export const DEPOT_OPTIONS = [
  { id: 'ALL', name: 'All Depots (National)', code: 'ALL' },
  { id: 'DEPOT_01', name: 'Dhaka', code: 'DEPOT_01', fullName: 'Dhaka Central Hub' },
  { id: 'DEPOT_02', name: 'Chittagong', code: 'DEPOT_02', fullName: 'Chittagong Port Depot' },
  { id: 'DEPOT_04', name: 'Sylhet', code: 'DEPOT_04', fullName: 'Sylhet Regional Depot' },
  { id: 'DEPOT_03', name: 'Bogra', code: 'DEPOT_03', fullName: 'Bogura Distribution Center' },
  { id: 'DEPOT_06', name: 'Rajshahi', code: 'DEPOT_06', fullName: 'Rajshahi Depot' },
  { id: 'DEPOT_05', name: 'Khulna', code: 'DEPOT_05', fullName: 'Khulna Coastal Hub' },
  { id: 'DEPOT_07', name: 'Mymensingh', code: 'DEPOT_07', fullName: 'Mymensingh Regional Hub' },
  { id: 'DEPOT_08', name: 'Comilla', code: 'DEPOT_08', fullName: 'Comilla Regional Hub' },
];

export const FISCAL_YEARS = [
  { id: 'FY2026_27', label: 'FY 2026–27 (Current)' },
  { id: 'FY2025_26', label: 'FY 2025–26' },
  { id: 'FY2024_25', label: 'FY 2024–25' },
];

export const FISCAL_PERIODS = [
  { id: 'FULL_YEAR', label: 'Full Year (Apr–Mar)' },
  { id: 'Q1', label: 'Q1 (Apr–Jun)' },
  { id: 'Q2', label: 'Q2 (Jul–Sep)' },
  { id: 'Q3', label: 'Q3 (Oct–Dec)' },
  { id: 'Q4', label: 'Q4 (Jan–Mar)' },
  { id: 'P01', label: 'P01 - April' },
  { id: 'P02', label: 'P02 - May' },
  { id: 'P03', label: 'P03 - June' },
  { id: 'P04', label: 'P04 - July' },
  { id: 'P05', label: 'P05 - August' },
  { id: 'P06', label: 'P06 - September' },
  { id: 'P07', label: 'P07 - October (Current)' },
  { id: 'P08', label: 'P08 - November' },
  { id: 'P09', label: 'P09 - December' },
  { id: 'P10', label: 'P10 - January' },
  { id: 'P11', label: 'P11 - February' },
  { id: 'P12', label: 'P12 - March' },
];

export const SSO_ROLES = [
  {
    id: 'FINANCE_DIRECTOR',
    label: 'FINANCE_DIRECTOR',
    user: 'Erfan Hassan',
    email: 'erfan@nerolac.bd',
  },
  {
    id: 'MANAGING_DIRECTOR',
    label: 'MANAGING_DIRECTOR',
    user: 'Shabir Ahmed',
    email: 'director@nerolac.bd',
  },
  {
    id: 'SUPPLY_CHAIN_HEAD',
    label: 'SUPPLY_CHAIN_HEAD',
    user: 'Tariqul Islam',
    email: 'scm@nerolac.bd',
  },
  {
    id: 'NATIONAL_SALES_MGR',
    label: 'NATIONAL_SALES_MGR',
    user: 'Zahirul Haque',
    email: 'sales@nerolac.bd',
  },
  {
    id: 'COMPLIANCE_AUDITOR',
    label: 'COMPLIANCE_AUDITOR',
    user: 'Nazia Rahman',
    email: 'audit@nerolac.bd',
  },
];

export function TopBar({
  currentModuleTitle = 'Enterprise Operations Control Center',
  onDepotChange,
  onFiscalPeriodChange,
  onFiscalYearChange,
}: TopBarProps) {
  const dashboard = useContext(DashboardContext);

  const [localDepot, setLocalDepot] = useState('ALL');
  const [localFY, setLocalFY] = useState('FY2026_27');
  const [localPeriod, setLocalPeriod] = useState('P07');
  const [localRole, setLocalRole] = useState('FINANCE_DIRECTOR');

  const selectedDepot = dashboard ? dashboard.selectedDepot : localDepot;
  const selectedFY = dashboard ? dashboard.selectedFY : localFY;
  const selectedPeriod = dashboard ? dashboard.selectedPeriod : localPeriod;
  const selectedRole = dashboard ? dashboard.selectedRole : localRole;

  const handleDepotSelect = (depotId: string) => {
    if (dashboard) {
      dashboard.setSelectedDepot(depotId);
    } else {
      setLocalDepot(depotId);
    }
    if (onDepotChange) onDepotChange(depotId);
  };

  const handleFiscalYearSelect = (fyId: string) => {
    if (dashboard) {
      dashboard.setSelectedFY(fyId);
    } else {
      setLocalFY(fyId);
    }
    if (onFiscalYearChange) onFiscalYearChange(fyId);
  };

  const handleFiscalPeriodSelect = (periodId: string) => {
    if (dashboard) {
      dashboard.setSelectedPeriod(periodId);
    } else {
      setLocalPeriod(periodId);
    }
    if (onFiscalPeriodChange) onFiscalPeriodChange(periodId);
  };

  const handleRoleSelect = (roleId: string) => {
    if (dashboard) {
      dashboard.setSelectedRole(roleId);
    } else {
      setLocalRole(roleId);
    }
  };

  const currentRoleObj = SSO_ROLES.find((r) => r.id === selectedRole) || SSO_ROLES[0];
  const activeDepotObj = DEPOT_OPTIONS.find((d) => d.id === selectedDepot) || DEPOT_OPTIONS[0];

  return (
    <header
      id="global-topbar"
      style={{
        minHeight: '60px',
        backgroundColor: '#FFFFFF',
        borderBottom: '1px solid #E2E8F0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 16px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        width: '100%',
        maxWidth: '100%',
        boxSizing: 'border-box',
      }}
    >
      {/* Left: Operational Context & Base Currency */}
      <div
        style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0, minWidth: 0 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#059669',
              boxShadow: '0 0 0 2px rgba(5, 150, 105, 0.2)',
              flexShrink: 0,
            }}
          />
          <span
            id="topbar-context-title"
            style={{
              fontSize: '13px',
              fontWeight: 700,
              color: '#0F172A',
              letterSpacing: '-0.2px',
              whiteSpace: 'nowrap',
            }}
          >
            {currentModuleTitle}
          </span>
        </div>

        <div style={{ width: '1px', height: '16px', backgroundColor: '#E2E8F0', flexShrink: 0 }} />

        {/* Currency & Sovereign Node indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              color: '#334155',
              backgroundColor: '#F8FAFC',
              border: '1px solid #E2E8F0',
              padding: '2px 6px',
              borderRadius: '4px',
              fontVariantNumeric: 'tabular-nums',
              whiteSpace: 'nowrap',
            }}
          >
            BDT (৳)
          </span>

          <span
            style={{
              fontSize: '11px',
              color: '#64748B',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              whiteSpace: 'nowrap',
            }}
          >
            <span style={{ color: '#059669', fontSize: '10px' }}>●</span> SAP S/4HANA
          </span>
        </div>
      </div>

      {/* Center-Right Controls: Depot Switcher, Fiscal Picker, SSO Role Badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          justifyContent: 'flex-end',
          flexShrink: 1,
          minWidth: 0,
        }}
      >
        {/* 1. 1-Click Global Depot Switcher */}
        <div
          id="global-depot-switcher-container"
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '6px',
            padding: '2px 4px',
            gap: '4px',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontSize: '10px',
              fontWeight: 700,
              color: '#64748B',
              padding: '0 4px',
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
              whiteSpace: 'nowrap',
            }}
          >
            Depot:
          </div>

          <select
            id="global-depot-switcher"
            value={selectedDepot}
            onChange={(e) => handleDepotSelect(e.target.value)}
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              padding: '3px 6px',
              fontSize: '11px',
              fontWeight: 600,
              color: '#0F172A',
              cursor: 'pointer',
              outline: 'none',
              maxWidth: '160px',
            }}
          >
            {DEPOT_OPTIONS.map((depot) => (
              <option key={depot.id} value={depot.id}>
                {depot.id === 'ALL' ? depot.name : `${depot.name} (${depot.code})`}
              </option>
            ))}
          </select>

          {/* Quick Active Depot Badge */}
          <span
            id="active-depot-badge"
            style={{
              fontSize: '10px',
              fontWeight: 700,
              color: '#D32F2F',
              backgroundColor: '#FFEBEE',
              border: '1px solid #FFCDD2',
              borderRadius: '4px',
              padding: '2px 6px',
              fontVariantNumeric: 'tabular-nums',
              whiteSpace: 'nowrap',
            }}
          >
            {activeDepotObj.name}
          </span>
        </div>

        {/* 2. April–March Fiscal Period Picker */}
        <div
          id="fiscal-period-picker"
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '6px',
            padding: '2px 4px',
            gap: '4px',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontSize: '10px',
              fontWeight: 700,
              color: '#64748B',
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
              whiteSpace: 'nowrap',
              padding: '0 2px',
            }}
          >
            Fiscal (Apr–Mar):
          </div>

          {/* Fiscal Year Select */}
          <select
            id="fiscal-year-select"
            value={selectedFY}
            onChange={(e) => handleFiscalYearSelect(e.target.value)}
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              padding: '3px 6px',
              fontSize: '11px',
              fontWeight: 600,
              color: '#0F172A',
              cursor: 'pointer',
              outline: 'none',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {FISCAL_YEARS.map((fy) => (
              <option key={fy.id} value={fy.id}>
                {fy.label}
              </option>
            ))}
          </select>

          {/* Fiscal Period / Month Select */}
          <select
            id="fiscal-period-select"
            value={selectedPeriod}
            onChange={(e) => handleFiscalPeriodSelect(e.target.value)}
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #CBD5E1',
              borderRadius: '4px',
              padding: '3px 6px',
              fontSize: '11px',
              fontWeight: 600,
              color: '#0284C7',
              cursor: 'pointer',
              outline: 'none',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {FISCAL_PERIODS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        {/* 3. User SSO Role Badge */}
        <div
          id="user-sso-role-badge"
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderRadius: '6px',
            padding: '2px 6px',
            gap: '6px',
            flexShrink: 0,
          }}
        >
          {/* Avatar initial */}
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              backgroundColor: '#0F172A',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.5px',
              flexShrink: 0,
            }}
          >
            {currentRoleObj.user
              .split(' ')
              .map((n) => n[0])
              .join('')}
          </div>

          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#0F172A',
                lineHeight: '1.2',
                whiteSpace: 'nowrap',
              }}
            >
              {currentRoleObj.user}
            </div>
            <div
              style={{ fontSize: '9px', color: '#64748B', lineHeight: '1.2', whiteSpace: 'nowrap' }}
            >
              Azure AD SSO (Sovereign)
            </div>
          </div>

          {/* Interactive Role Switcher Pill */}
          <select
            id="sso-role-select"
            value={selectedRole}
            onChange={(e) => handleRoleSelect(e.target.value)}
            style={{
              fontSize: '10px',
              fontWeight: 700,
              color: '#0F172A',
              backgroundColor: '#F1F5F9',
              border: '1px solid #E2E8F0',
              borderRadius: '4px',
              padding: '2px 4px',
              cursor: 'pointer',
              outline: 'none',
              maxWidth: '120px',
            }}
          >
            {SSO_ROLES.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}
