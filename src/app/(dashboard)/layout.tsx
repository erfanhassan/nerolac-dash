import React from 'react';
import Link from 'next/link';
import { TopBar } from '@/components/layout/TopBar';
import { DashboardProvider } from '@/context/DashboardContext';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardProvider>
      <div
        style={{
          display: 'flex',
          minHeight: '100vh',
          backgroundColor: '#FFFFFF',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          maxWidth: '100vw',
          overflowX: 'hidden',
        }}
      >
        {/* Corporate Left Sidebar */}
        <aside
          style={{
            width: '240px',
            backgroundColor: '#F8FAFC',
            borderRight: '1px solid #E2E8F0',
            display: 'flex',
            flexDirection: 'column',
            flexShrink: 0,
          }}
        >
          {/* Brand Banner */}
          <div
            style={{
              padding: '20px 16px',
              borderBottom: '1px solid #E2E8F0',
              backgroundColor: '#FFFFFF',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                id="nerolac-brand-logo-mark"
                style={{
                  width: '12px',
                  height: '24px',
                  backgroundColor: '#D32F2F',
                  borderRadius: '2px',
                }}
              />
              <div>
                <div
                  style={{
                    fontSize: '15px',
                    fontWeight: 700,
                    letterSpacing: '0.5px',
                    color: '#D32F2F',
                  }}
                >
                  KANSAI NEROLAC
                </div>
                <div
                  style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    color: '#64748B',
                    letterSpacing: '1px',
                  }}
                >
                  BANGLADESH OPERATIONS
                </div>
              </div>
            </div>
          </div>

          {/* Navigation Items */}
          <nav style={{ padding: '16px 8px', flex: 1 }}>
            <div
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: '#94A3B8',
                padding: '0 8px 8px 8px',
                letterSpacing: '0.5px',
              }}
            >
              CORE MODULES
            </div>

            <Link
              href="/finance"
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '8px 12px',
                borderRadius: '4px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderLeft: '3px solid #D32F2F',
                color: '#0F172A',
                fontWeight: 600,
                fontSize: '13px',
                textDecoration: 'none',
                marginBottom: '4px',
              }}
            >
              Finance Control Center
            </Link>

            <Link
              href="/hr"
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '8px 12px',
                borderRadius: '4px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderLeft: '3px solid #D32F2F',
                color: '#0F172A',
                fontWeight: 600,
                fontSize: '13px',
                textDecoration: 'none',
                marginBottom: '4px',
              }}
            >
              HR Workforce Intelligence
            </Link>

            <Link
              id="nav-supply-chain"
              href="/supply-chain"
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '8px 12px',
                borderRadius: '4px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderLeft: '3px solid #D32F2F',
                color: '#0F172A',
                fontWeight: 600,
                fontSize: '13px',
                textDecoration: 'none',
                marginBottom: '4px',
              }}
            >
              Supply Chain (SCM & MRP)
            </Link>

            <Link
              id="nav-whatsapp"
              href="/whatsapp"
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '8px 12px',
                borderRadius: '4px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderLeft: '3px solid #D32F2F',
                color: '#0F172A',
                fontWeight: 600,
                fontSize: '13px',
                textDecoration: 'none',
                marginBottom: '4px',
              }}
            >
              WhatsApp Recon (Module 4)
            </Link>
          </nav>

          {/* Footer info */}
          <div
            style={{
              padding: '12px 16px',
              borderTop: '1px solid #E2E8F0',
              fontSize: '11px',
              color: '#64748B',
              backgroundColor: '#FFFFFF',
            }}
          >
            <div>Production ERP: SAP S/4HANA</div>
            <div style={{ color: '#059669', fontWeight: 600, marginTop: '2px' }}>
              ● Bangladesh Sovereign Node
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minWidth: 0,
            width: 'calc(100% - 240px)',
          }}
        >
          {/* Global Top Bar */}
          <TopBar />

          {/* Dashboard View Body */}
          <main
            style={{
              flex: 1,
              backgroundColor: '#FFFFFF',
              padding: '24px',
              overflowY: 'auto',
              minWidth: 0,
            }}
          >
            {children}
          </main>
        </div>
      </div>
    </DashboardProvider>
  );
}
