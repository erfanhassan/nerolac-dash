'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface DashboardContextType {
  // Depot
  selectedDepot: string;
  setSelectedDepot: (depot: string) => void;

  // Fiscal Year & Month for Finance / Analytics
  selectedYear: number;
  setSelectedYear: (year: number) => void;
  selectedMonth: number;
  setSelectedMonth: (month: number) => void;

  // TopBar Fiscal Period tokens
  selectedFY: string;
  setSelectedFY: (fy: string) => void;
  selectedPeriod: string;
  setSelectedPeriod: (period: string) => void;

  // SSO Role
  selectedRole: string;
  setSelectedRole: (role: string) => void;
}

const fyToYearMap: Record<string, number> = {
  FY2026_27: 2026,
  FY2025_26: 2025,
  FY2024_25: 2024,
};

const yearToFyMap: Record<number, string> = {
  2026: 'FY2026_27',
  2025: 'FY2025_26',
  2024: 'FY2024_25',
};

const periodToMonthMap: Record<string, number> = {
  P01: 4,
  P02: 5,
  P03: 6,
  P04: 7,
  P05: 8,
  P06: 9,
  P07: 10,
  P08: 11,
  P09: 12,
  P10: 1,
  P11: 2,
  P12: 3,
  Q1: 3,
  Q2: 6,
  Q3: 9,
  Q4: 12,
  FULL_YEAR: 3,
};

const monthToPeriodMap: Record<number, string> = {
  1: 'P10',
  2: 'P11',
  3: 'P12',
  4: 'P01',
  5: 'P02',
  6: 'P03',
  7: 'P04',
  8: 'P05',
  9: 'P06',
  10: 'P07',
  11: 'P08',
  12: 'P09',
};

export const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [selectedDepot, setSelectedDepotState] = useState<string>('ALL');
  const [selectedYear, setSelectedYearState] = useState<number>(2024);
  const [selectedMonth, setSelectedMonthState] = useState<number>(3);
  const [selectedFY, setSelectedFYState] = useState<string>('FY2024_25');
  const [selectedPeriod, setSelectedPeriodState] = useState<string>('P12');
  const [selectedRole, setSelectedRole] = useState<string>('FINANCE_DIRECTOR');

  const setSelectedDepot = (depot: string) => {
    setSelectedDepotState(depot);
  };

  const setSelectedYear = (year: number) => {
    setSelectedYearState(year);
    const mappedFY = yearToFyMap[year];
    if (mappedFY) {
      setSelectedFYState(mappedFY);
    }
  };

  const setSelectedFY = (fy: string) => {
    setSelectedFYState(fy);
    const mappedYear = fyToYearMap[fy];
    if (mappedYear !== undefined) {
      setSelectedYearState(mappedYear);
    }
  };

  const setSelectedMonth = (month: number) => {
    setSelectedMonthState(month);
    const mappedPeriod = monthToPeriodMap[month];
    if (mappedPeriod) {
      setSelectedPeriodState(mappedPeriod);
    }
  };

  const setSelectedPeriod = (period: string) => {
    setSelectedPeriodState(period);
    const mappedMonth = periodToMonthMap[period];
    if (mappedMonth !== undefined) {
      setSelectedMonthState(mappedMonth);
    }
  };

  return (
    <DashboardContext.Provider
      value={{
        selectedDepot,
        setSelectedDepot,
        selectedYear,
        setSelectedYear,
        selectedMonth,
        setSelectedMonth,
        selectedFY,
        setSelectedFY,
        selectedPeriod,
        setSelectedPeriod,
        selectedRole,
        setSelectedRole,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard(): DashboardContextType {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
}
