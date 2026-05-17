#!/usr/bin/env python3
"""
Spending Tracker Dashboard — lightweight HTTP server + Chart.js visualizations.
Run: python3 dashboard.py [--port PORT]
"""
import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

TRACKER_DIR = Path(os.path.expanduser("~/.hermes/spending_tracker"))
sys.path.insert(0, str(TRACKER_DIR))

from tracker import get_dashboard_data, load_config, get_summary


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>💸 Spending Tracker</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f0f0f;
    --card: #1a1a1a;
    --border: #2a2a2a;
    --text: #e0e0e0;
    --muted: #888;
    --green: #4ade80;
    --yellow: #facc15;
    --red: #f87171;
    --blue: #60a5fa;
    --purple: #c084fc;
    --orange: #fb923c;
    --teal: #2dd4bf;
    --pink: #f472b6;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
  }
  h1 { font-size: 1.8rem; margin-bottom: 4px; }
  .subtitle { color: var(--muted); margin-bottom: 24px; font-size: 0.9rem; }
  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }
  .stat-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }
  .stat-card .label { color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-card .value { font-size: 1.6rem; font-weight: 700; margin-top: 4px; }
  .stat-card .sub { font-size: 0.8rem; color: var(--muted); margin-top: 2px; }
  .stat-card.warn { border-color: var(--yellow); }
  .stat-card.crit { border-color: var(--red); }
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
  }
  .panel {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
  }
  .panel h2 {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 16px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  canvas { max-height: 300px; }
  .tabs {
    display: flex;
    gap: 0;
    margin-bottom: 16px;
  }
  .tab {
    padding: 8px 20px;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s;
  }
  .tab:first-child { border-radius: 6px 0 0 6px; }
  .tab:last-child { border-radius: 0 6px 6px 0; }
  .tab.active { background: var(--blue); color: white; border-color: var(--blue); }
  .entries-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }
  .entries-table th {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    color: var(--muted);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .entries-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  .entries-table tr:hover td { background: rgba(255,255,255,0.03); }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .badge-cc { background: rgba(192,132,252,0.2); color: var(--purple); }
  .badge-upi { background: rgba(96,165,250,0.2); color: var(--blue); }
  .badge-cash { background: rgba(251,146,60,0.2); color: var(--orange); }
  .badge-other { background: rgba(136,136,136,0.2); color: var(--muted); }
  .amount { font-weight: 600; }
  .amount-cc { color: var(--purple); }
  .refresh { color: var(--muted); font-size: 0.75rem; margin-top: 12px; }
  @media (max-width: 768px) {
    .grid-2 { grid-template-columns: 1fr; }
    body { padding: 12px; }
  }
</style>
</head>
<body>
<h1>💸 Spending Tracker</h1>
<p class="subtitle" id="weekRange">Loading...</p>

<div class="stats" id="stats"></div>

<div class="tabs">
  <button class="tab active" onclick="switchTab('regular')">💵 Regular</button>
  <button class="tab" onclick="switchTab('credit')">💳 Credit Card</button>
</div>

<div class="grid-2">
  <div class="panel">
    <h2>📂 Category Breakdown</h2>
    <canvas id="categoryChart"></canvas>
  </div>
  <div class="panel">
    <h2>📈 Weekly Trend</h2>
    <canvas id="weeklyChart"></canvas>
  </div>
</div>

<div class="grid-2">
  <div class="panel">
    <h2>📅 Daily Spending (14 days)</h2>
    <canvas id="dailyChart"></canvas>
  </div>
  <div class="panel">
    <h2>💳 Payment Methods</h2>
    <canvas id="paymentChart"></canvas>
  </div>
</div>

<div class="panel" style="margin-bottom:24px;">
  <h2>📋 Recent Entries</h2>
  <table class="entries-table">
    <thead><tr><th>Date</th><th>Category</th><th>Amount</th><th>Payment</th><th>Note</th></tr></thead>
    <tbody id="entriesBody"></tbody>
  </table>
</div>

<p class="refresh" id="refreshTime"></p>

<script>
let currentTab = 'regular';
let chartInstances = {};

function destroyCharts() {
  Object.values(chartInstances).forEach(c => c.destroy());
  chartInstances = {};
}

const COLOR_PALETTE = [
  '#4ade80','#60a5fa','#facc15','#f87171','#c084fc','#fb923c','#2dd4bf','#f472b6',
  '#a78bfa','#34d399','#38bdf8','#fbbf24'
];

function makeChart(canvasId, config) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  chartInstances[canvasId] = new Chart(ctx, {
    ...config,
    options: {
      ...config.options,
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#888', font: { size: 11 } } } },
      scales: config.options?.scales || {}
    }
  });
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab:${tab === 'regular' ? 'first' : 'last'}-child`).classList.add('active');
  loadData();
}

async function loadData() {
  const resp = await fetch('/api/data');
  const data = await resp.json();
  render(data);
}

function render(d) {
  document.getElementById('weekRange').textContent =
    `${d.week_start} → ${d.week_end} (${d.week_id})`;

  // Stats
  const regTotal = currentTab === 'regular' ? d.weekly_regular_total : d.weekly_cc_total;
  const limit = currentTab === 'regular' ? d.weekly_budget : null;
  const pct = limit ? Math.round(regTotal / limit * 100) : 0;
  const remaining = limit ? limit - regTotal : 0;
  const critClass = pct >= 100 ? ' crit' : pct >= 80 ? ' warn' : '';

  const entries = currentTab === 'regular'
    ? d.entries.filter(e => !e.is_credit_card)
    : d.entries.filter(e => e.is_credit_card);

  document.getElementById('stats').innerHTML = `
    <div class="stat-card${critClass}">
      <div class="label">${currentTab === 'regular' ? 'Weekly Total' : 'Credit Card Total'}</div>
      <div class="value">₹${regTotal.toLocaleString('en-IN')}</div>
      ${limit ? `<div class="sub">of ₹${limit.toLocaleString('en-IN')} (${pct}%)</div>` : ''}
    </div>
    ${limit ? `<div class="stat-card">
      <div class="label">Remaining</div>
      <div class="value" style="color:${remaining >= 0 ? 'var(--green)' : 'var(--red)'}">₹${remaining.toLocaleString('en-IN')}</div>
    </div>` : ''}
    <div class="stat-card">
      <div class="label">Total Entries</div>
      <div class="value">${entries.length}</div>
    </div>
    <div class="stat-card">
      <div class="label">Avg Per Entry</div>
      <div class="value">₹${entries.length ? Math.round(entries.reduce((s,e) => s+e.amount,0) / entries.length).toLocaleString('en-IN') : 0}</div>
    </div>
  `;

  destroyCharts();

  // Category chart (doughnut)
  const catData = d.categories.filter(c => c.total > 0);
  makeChart('categoryChart', {
    type: 'doughnut',
    data: {
      labels: catData.map(c => c.name),
      datasets: [{
        data: catData.map(c => c.total),
        backgroundColor: COLOR_PALETTE,
        borderColor: '#1a1a1a',
        borderWidth: 2
      }]
    },
    options: {
      cutout: '60%',
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyleWidth: 8 } }
      }
    }
  });

  // Weekly trend
  const wkLabels = d.weekly_history.map(w => w.week);
  const wkReg = d.weekly_history.map(w => w.regular);
  const wkCC = d.weekly_history.map(w => w.credit_card);
  const wkLim = d.weekly_history.map(w => w.limit);

  makeChart('weeklyChart', {
    type: 'bar',
    data: {
      labels: wkLabels,
      datasets: [
        {
          label: 'Regular',
          data: wkReg,
          backgroundColor: '#60a5fa',
          borderRadius: 4,
        },
        {
          label: 'Credit Card',
          data: wkCC,
          backgroundColor: '#c084fc',
          borderRadius: 4,
        }
      ]
    },
    options: {
      scales: {
        x: { ticks: { color: '#888' }, grid: { display: false } },
        y: { ticks: { color: '#888', callback: v => '₹'+v }, grid: { color: '#1a1a1a' } }
      },
      plugins: { legend: { position: 'top', labels: { usePointStyle: true } } }
    }
  });

  // Daily chart
  const dayLabels = d.daily_spending.map(d => d.date.slice(5));
  makeChart('dailyChart', {
    type: 'line',
    data: {
      labels: dayLabels,
      datasets: [
        {
          label: 'Regular',
          data: d.daily_spending.map(d => d.regular),
          borderColor: '#60a5fa',
          backgroundColor: 'rgba(96,165,250,0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 5,
        },
        {
          label: 'Credit Card',
          data: d.daily_spending.map(d => d.credit_card),
          borderColor: '#c084fc',
          backgroundColor: 'rgba(192,132,252,0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 5,
        }
      ]
    },
    options: {
      scales: {
        x: { ticks: { color: '#888', maxTicksLimit: 7 }, grid: { display: false } },
        y: { ticks: { color: '#888', callback: v => '₹'+v }, grid: { color: '#1a1a1a' } }
      }
    }
  });

  // Payment methods chart
  const pmLabels = Object.keys(d.payment_methods);
  const pmData = Object.values(d.payment_methods);
  if (pmLabels.length > 0) {
    makeChart('paymentChart', {
      type: 'pie',
      data: {
        labels: pmLabels,
        datasets: [{
          data: pmData,
          backgroundColor: COLOR_PALETTE,
          borderColor: '#1a1a1a',
          borderWidth: 2,
        }]
      },
      options: {
        plugins: { legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true } } }
      }
    });
  }

  // Entries table
  const showEntries = entries.slice(0, 20);
  document.getElementById('entriesBody').innerHTML = showEntries.map(e => `
    <tr>
      <td>${e.date}</td>
      <td>${e.category.replace(/_/g, ' ')}</td>
      <td class="amount${e.is_credit_card ? ' amount-cc' : ''}">₹${e.amount.toLocaleString('en-IN')}</td>
      <td><span class="badge badge-${e.payment_method === 'upi' ? 'upi' : e.payment_method === 'cash' ? 'cash' : e.is_credit_card ? 'cc' : 'other'}">${e.payment_method || '—'}</span></td>
      <td style="color:var(--muted)">${e.note || '—'}</td>
    </tr>
  `).join('');

  document.getElementById('refreshTime').textContent =
    `Last updated: ${new Date().toLocaleString()}`;
}

// Auto-refresh every 30 seconds
setInterval(loadData, 30000);
loadData();
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode('utf-8'))
        elif self.path == '/api/data':
            try:
                data = get_dashboard_data()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/summary':
            try:
                summary = get_summary()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(summary.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # silence logs


def main():
    port = 8765
    if len(sys.argv) > 2 and sys.argv[1] == '--port':
        port = int(sys.argv[2])

    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"📊 Spending Tracker Dashboard → http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
