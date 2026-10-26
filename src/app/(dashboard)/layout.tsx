import React from 'react';
import Link from 'next/link';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        backgroundColor: '#FFFFFF',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
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

          <div
            style={{
              padding: '8px 12px',
              color: '#64748B',
              fontSize: '13px',
              marginBottom: '4px',
              cursor: 'not-allowed',
            }}
          >
            Sales & Field Operations
          </div>
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
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Top Navbar */}
        <header
          style={{
            height: '56px',
            backgroundColor: '#FFFFFF',
            borderBottom: '1px solid #E2E8F0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span
              style={{
                fontSize: '16px',
                fontWeight: 600,
                color: '#0F172A',
              }}
            >
              Finance Control Center (Module 1)
            </span>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: '#D32F2F',
                backgroundColor: '#FFEBEE',
                border: '1px solid #FFCDD2',
                padding: '2px 8px',
                borderRadius: '4px',
              }}
            >
              GL 10000–10017
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span style={{ fontSize: '12px', color: '#64748B' }}>
              Base Currency: <strong>BDT (৳)</strong>
            </span>
            <div
              style={{
                width: '1px',
                height: '16px',
                backgroundColor: '#E2E8F0',
              }}
            />
            <span
              style={{
                fontSize: '12px',
                fontWeight: 600,
                color: '#334155',
                backgroundColor: '#F1F5F9',
                padding: '4px 8px',
                borderRadius: '4px',
              }}
            >
              FINANCE_DIRECTOR
            </span>
          </div>
        </header>

        {/* Dashboard View Body */}
        <main
          style={{
            flex: 1,
            backgroundColor: '#FFFFFF',
            padding: '24px',
            overflowY: 'auto',
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
