/* global __ENV, __VU, __ITER */
import http from 'k6/http';
import { check, sleep } from 'k6';

// k6 Stress Testing Options: 1,000 Concurrent User Sessions
export const options = {
  scenarios: {
    filter_clicking_stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '3s', target: 200 }, // Warmup to 200 concurrent users
        { duration: '7s', target: 1000 }, // Scale to 1,000 concurrent users
        { duration: '5s', target: 1000 }, // Sustained peak load at 1,000 users
        { duration: '3s', target: 0 }, // Graceful ramp down
      ],
    },
  },
  thresholds: {
    // SLA Requirement: P95 response times must remain < 100ms
    http_req_duration: ['p(95)<100'],
    http_req_failed: ['rate<0.01'], // < 1% error rate
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:8000';

const DEPOTS = ['DHK', 'CTG', 'SYL', 'BGR', 'RAJ', 'KLN', 'MYM', 'COM', 'ALL'];
const CATEGORIES = ['TIO2', 'RESIN', 'SOLVENT', 'EXTENDER', 'ALL'];

export default function () {
  const vuId = __VU;
  const iterId = __ITER;

  // Each concurrent user has a distinct corporate session ID to model 1,000 distinct users
  const headers = {
    'X-User-ID': `user_session_${vuId}`,
    'X-User-Role': 'DEPOT_MANAGER',
    'X-Depot-Id': DEPOTS[vuId % DEPOTS.length],
    'Content-Type': 'application/json',
  };

  const selectedDepot = DEPOTS[(vuId + iterId) % DEPOTS.length];
  const selectedCat = CATEGORIES[(vuId + iterId) % CATEGORIES.length];

  // Rotate between realistic dashboard filter clicks across all 4 modules
  const filterAction = iterId % 6;

  let url;
  if (filterAction === 0) {
    // Module 1: Segment P&L Filter Switch
    url = `${BASE_URL}/api/v1/finance/segment-pnl?fiscal_year=2024&fiscal_month=3&depot_id=${selectedDepot}`;
  } else if (filterAction === 1) {
    // Module 1: Supplier Variance Flagged Spread Filter
    url = `${BASE_URL}/api/v1/finance/supplier-variance?flagged_only=true`;
  } else if (filterAction === 2) {
    // Module 1: Cashflow Simulation Slider Interaction
    const arPct = 70 + ((vuId + iterId) % 25);
    const dpo = 30 + ((vuId + iterId) % 60);
    url = `${BASE_URL}/api/v1/finance/simulate-cashflow?ar_collection_pct=${arPct}&dpo_days=${dpo}&capex_slider_bdt=500000`;
  } else if (filterAction === 3) {
    // Module 2: HR Workforce 2-Factor Capacity Filter
    url = `${BASE_URL}/api/v1/hr/manpower-capacity?depot_id=${selectedDepot}`;
  } else if (filterAction === 4) {
    // Module 3: Supply Chain Demand Forecast / MRP Reorder Filter
    url = `${BASE_URL}/api/v1/supply-chain/mrp-proposals?category=${selectedCat}`;
  } else {
    // Module 4: WhatsApp Field Recon Messages Filter
    url = `${BASE_URL}/api/v1/whatsapp/messages?status=PARSED`;
  }

  const res = http.get(url, { headers, tags: { name: 'filter_click' } });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'sub-100ms latency': (r) => r.timings.duration < 100,
  });

  // Paced user think time between filter clicks (realistic user interaction: 1s)
  sleep(1.0);
}
