'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  ReconciliationDashboard,
  DailyReconciliationResponse,
} from '@/components/whatsapp/ReconciliationDashboard';
import {
  MessageStreamCards,
  WhatsAppMessageFeedResponse,
} from '@/components/whatsapp/MessageStreamCards';

export default function WhatsAppDashboardPage() {
  const [activeTab, setActiveTab] = useState<'ALL' | 'RECON' | 'FEED'>('ALL');
  const [reconData, setReconData] = useState<DailyReconciliationResponse | null>(null);
  const [feedData, setFeedData] = useState<WhatsAppMessageFeedResponse | null>(null);
  const [isLoadingRecon, setIsLoadingRecon] = useState(true);
  const [isLoadingFeed, setIsLoadingFeed] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch 7:00 PM reconciliation data
  const fetchReconciliation = useCallback(async () => {
    setIsLoadingRecon(true);
    setErrorMessage(null);
    try {
      const res = await fetch('/api/v1/whatsapp/reconciliation');
      if (!res.ok) {
        throw new Error(`Failed to load 7:00 PM SAP Recon (HTTP ${res.status})`);
      }
      const data: DailyReconciliationResponse = await res.json();
      setReconData(data);
    } catch (err: any) {
      console.error('Error fetching reconciliation data:', err);
      setErrorMessage(err.message || 'Error loading reconciliation data');
    } finally {
      setIsLoadingRecon(false);
    }
  }, []);

  // Fetch real-time message stream
  const fetchMessageFeed = useCallback(async () => {
    setIsLoadingFeed(true);
    try {
      const res = await fetch('/api/v1/whatsapp/messages');
      if (!res.ok) {
        throw new Error(`Failed to load message stream (HTTP ${res.status})`);
      }
      const data: WhatsAppMessageFeedResponse = await res.json();
      setFeedData(data);
    } catch (err: any) {
      console.error('Error fetching message feed:', err);
    } finally {
      setIsLoadingFeed(false);
    }
  }, []);

  // Trigger manual 7:00 PM reconciliation recalculation
  const handleTriggerRecon = async () => {
    try {
      const res = await fetch('/api/v1/whatsapp/reconciliation/run', {
        method: 'POST',
      });
      if (!res.ok) {
        throw new Error(`Failed to trigger reconciliation (HTTP ${res.status})`);
      }
      const updatedData: DailyReconciliationResponse = await res.json();
      setReconData(updatedData);
      await fetchMessageFeed();
    } catch (err: any) {
      console.error('Error triggering recon:', err);
      alert(`Error triggering reconciliation: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchReconciliation();
    fetchMessageFeed();
  }, [fetchReconciliation, fetchMessageFeed]);

  return (
    <div
      style={{
        maxWidth: '1440px',
        margin: '0 auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
      }}
    >
      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '4px',
                height: '24px',
                backgroundColor: '#D32F2F',
                borderRadius: '2px',
              }}
            />
            <h1
              style={{
                fontSize: '22px',
                fontWeight: 700,
                color: '#0F172A',
                letterSpacing: '-0.3px',
                margin: 0,
              }}
            >
              WhatsApp Field Operations &amp; 7:00 PM SAP Recon
            </h1>
          </div>
          <p
            style={{
              fontSize: '13px',
              color: '#64748B',
              margin: '4px 0 0 12px',
            }}
          >
            Meta Cloud Webhook Listener, Asynchronous Banglish Entity Parser (pgvector + RapidFuzz),
            and Evening SAP Invoicing Audit
          </p>
        </div>

        {/* View Switcher / Tab Buttons */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#F1F5F9',
            padding: '3px',
            borderRadius: '6px',
            gap: '2px',
          }}
        >
          <button
            id="tab-btn-all"
            onClick={() => setActiveTab('ALL')}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: activeTab === 'ALL' ? 700 : 500,
              color: activeTab === 'ALL' ? '#0F172A' : '#64748B',
              backgroundColor: activeTab === 'ALL' ? '#FFFFFF' : 'transparent',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              boxShadow: activeTab === 'ALL' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
            }}
          >
            Unified Dashboard
          </button>

          <button
            id="tab-btn-recon"
            onClick={() => setActiveTab('RECON')}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: activeTab === 'RECON' ? 700 : 500,
              color: activeTab === 'RECON' ? '#0F172A' : '#64748B',
              backgroundColor: activeTab === 'RECON' ? '#FFFFFF' : 'transparent',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              boxShadow: activeTab === 'RECON' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
            }}
          >
            7:00 PM SAP Recon
          </button>

          <button
            id="tab-btn-feed"
            onClick={() => setActiveTab('FEED')}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: activeTab === 'FEED' ? 700 : 500,
              color: activeTab === 'FEED' ? '#0F172A' : '#64748B',
              backgroundColor: activeTab === 'FEED' ? '#FFFFFF' : 'transparent',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              boxShadow: activeTab === 'FEED' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
            }}
          >
            Live Ingestion Stream ({feedData?.total_messages_today ?? 0})
          </button>
        </div>
      </div>

      {/* Error notification if any */}
      {errorMessage && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: '#FEF2F2',
            border: '1px solid #FECACA',
            borderRadius: '6px',
            color: '#991B1B',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>⚠️ {errorMessage}</span>
          <button
            onClick={() => {
              fetchReconciliation();
              fetchMessageFeed();
            }}
            style={{
              backgroundColor: '#DC2626',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Main Content Area */}
      {(activeTab === 'ALL' || activeTab === 'RECON') && (
        <ReconciliationDashboard
          data={reconData}
          isLoading={isLoadingRecon}
          onTriggerRecon={handleTriggerRecon}
        />
      )}

      {(activeTab === 'ALL' || activeTab === 'FEED') && (
        <MessageStreamCards
          data={feedData}
          isLoading={isLoadingFeed}
          onRefresh={fetchMessageFeed}
        />
      )}
    </div>
  );
}
