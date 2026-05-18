#!/usr/bin/env python3
"""
AgentHermes — Personal Assistant Dashboard
TradeLore-inspired design · Orange brand · Sidebar navigation
Run: python3 dashboard.py [--port PORT]
"""
import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timedelta

AGENT_DIR = Path(os.path.expanduser("~/.hermes/spending_tracker"))
sys.path.insert(0, str(AGENT_DIR))

from tracker import get_dashboard_data, load_config, get_summary

TASKS_PATH = AGENT_DIR / "tasks.json"
SCHEDULE_PATH = AGENT_DIR / "schedule.json"


# ═══════════════════════════════════════════
#  DATA HELPERS
# ═══════════════════════════════════════════

def load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"tasks": []} if "tasks" in str(path) else {"schedule": []}

def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def get_overview():
    """Combined data for main dashboard overview."""
    # Spending snapshot
    config = load_config()
    spending = get_dashboard_data()

    # Today's tasks
    tasks_data = load_json(TASKS_PATH)
    today = get_today_str()
    today_tasks = [t for t in tasks_data["tasks"] if t.get("date") == today]
    upcoming_tasks = [t for t in tasks_data["tasks"] if t.get("date", "") > today][:5]
    overdue_tasks = [t for t in tasks_data["tasks"]
                     if t.get("date", "") < today and not t.get("done")]

    # Today's schedule
    sched_data = load_json(SCHEDULE_PATH)
    today_schedule = [s for s in sched_data["schedule"] if s.get("date") == today]
    today_schedule.sort(key=lambda s: s.get("time", "23:59"))

    # Upcoming schedule
    upcoming_schedule = [s for s in sched_data["schedule"]
                         if s.get("date", "") >= today]
    upcoming_schedule.sort(key=lambda s: s.get("date", "") + s.get("time", "23:59"))
    upcoming_schedule = upcoming_schedule[:5]

    return {
        "spending": spending,
        "today_tasks": today_tasks,
        "upcoming_tasks": upcoming_tasks,
        "overdue_tasks": overdue_tasks,
        "today_schedule": today_schedule,
        "upcoming_schedule": upcoming_schedule,
        "total_tasks": len(tasks_data["tasks"]),
        "total_schedule": len(sched_data["schedule"]),
    }


# ═══════════════════════════════════════════
#  HTML + CSS + JS (TradeLore-inspired)
# ═══════════════════════════════════════════

AGENTHERMES_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgentHermes — Personal Assistant</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #ffffff;
    --surface: #fafafa;
    --page: #f8f8f8;
    --border: #e5e5e5;
    --text: #1a1a1a;
    --text-secondary: #737373;
    --brand: #f97316;
    --brand-light: #fff7ed;
    --brand-hover: #ea580c;
    --green: #16a34a;
    --green-bg: #f0fdf4;
    --red: #dc2626;
    --red-bg: #fef2f2;
    --blue: #2563eb;
    --blue-bg: #eff6ff;
    --purple: #7c3aed;
    --purple-bg: #f5f3ff;
    --radius: 10px;
    --radius-sm: 6px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
    --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    --sidebar-w: 220px;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: var(--font);
    background: var(--page);
    color: var(--text);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    display: flex;
    min-height: 100vh;
  }

  /* ── Sidebar ── */
  .sidebar {
    width: var(--sidebar-w);
    background: var(--bg);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    position: fixed;
    top: 0; left: 0; bottom: 0;
    z-index: 100;
    padding: 0;
  }
  .sidebar-logo {
    padding: 20px 20px 16px;
    font-size: 20px;
    font-weight: 700;
    color: var(--brand);
    letter-spacing: -0.5px;
    border-bottom: 1px solid var(--border);
  }
  .sidebar-logo .sub {
    display: block;
    font-size: 11px;
    font-weight: 400;
    color: var(--text-secondary);
    margin-top: 2px;
    letter-spacing: 0;
  }
  .sidebar-nav {
    flex: 1;
    padding: 12px 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .sidebar-nav .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: var(--radius-sm);
    font-size: 14px;
    font-weight: 500;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s;
    text-decoration: none;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
  }
  .sidebar-nav .nav-item:hover {
    background: var(--brand-light);
    color: var(--text);
  }
  .sidebar-nav .nav-item.active {
    background: var(--brand-light);
    color: var(--brand);
    font-weight: 600;
  }
  .sidebar-nav .nav-item .icon { font-size: 18px; width: 24px; text-align: center; }
  .sidebar-nav .nav-item .badge-count {
    margin-left: auto;
    background: var(--brand);
    color: white;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 10px;
    min-width: 20px;
    text-align: center;
  }
  .sidebar-footer {
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .sidebar-footer .status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--green);
  }

  /* ── Main Content ── */
  .main-wrap {
    margin-left: var(--sidebar-w);
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }
  .header {
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 50;
  }
  .header h1 { font-size: 18px; font-weight: 600; }
  .header .date-display {
    margin-left: auto;
    font-size: 13px;
    color: var(--text-secondary);
    font-weight: 500;
  }
  .main {
    flex: 1;
    padding: 24px 28px;
    max-width: 1200px;
  }
  .view { display: none; }
  .view.active { display: block; }

  /* ── Stat Pills ── */
  .stat-pills {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }
  .stat-pill {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 18px;
    box-shadow: var(--shadow);
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .stat-pill .label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .stat-pill .value {
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.5px;
  }
  .stat-pill .value.green { color: var(--green); }
  .stat-pill .value.red { color: var(--red); }
  .stat-pill .value.brand { color: var(--brand); }
  .stat-pill .sub {
    font-size: 11px;
    color: var(--text-secondary);
  }

  /* ── Sections / Panels ── */
  .section {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: var(--shadow);
  }
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }
  .section-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
  }
  .section-subtitle {
    font-size: 12px;
    color: var(--text-secondary);
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .grid-3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }

  /* ── Charts ── */
  .chart-wrap { position: relative; height: 240px; }
  .chart-wrap canvas { width: 100% !important; height: 100% !important; }

  /* ── Task List ── */
  .task-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    margin-bottom: 6px;
    background: var(--bg);
    transition: border-color 0.15s;
  }
  .task-item:hover { border-color: var(--brand); }
  .task-item.done { opacity: 0.6; }
  .task-item.done .task-title { text-decoration: line-through; }
  .task-check {
    width: 20px; height: 20px;
    border: 2px solid var(--border);
    border-radius: 50%;
    cursor: pointer;
    flex-shrink: 0;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .task-check:hover { border-color: var(--brand); }
  .task-check.checked {
    background: var(--brand);
    border-color: var(--brand);
    color: white;
    font-size: 12px;
  }
  .task-body { flex: 1; min-width: 0; }
  .task-title { font-size: 14px; font-weight: 500; }
  .task-meta {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 2px;
  }
  .task-date {
    font-size: 12px;
    color: var(--text-secondary);
    white-space: nowrap;
  }
  .task-date.overdue { color: var(--red); font-weight: 600; }
  .task-actions { display: flex; gap: 4px; }
  .task-actions button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 14px;
    color: var(--text-secondary);
    transition: all 0.1s;
  }
  .task-actions button:hover { background: var(--red-bg); color: var(--red); }

  /* ── Schedule Items ── */
  .schedule-item {
    display: flex;
    gap: 14px;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
    align-items: flex-start;
  }
  .schedule-item:last-child { border-bottom: none; }
  .schedule-time {
    font-size: 13px;
    font-weight: 700;
    color: var(--brand);
    min-width: 55px;
    white-space: nowrap;
  }
  .schedule-body { flex: 1; }
  .schedule-body .s-title { font-size: 14px; font-weight: 500; }
  .schedule-body .s-desc {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 2px;
  }
  .schedule-badge {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 12px;
    font-weight: 600;
    white-space: nowrap;
  }
  .schedule-badge.work { background: var(--blue-bg); color: var(--blue); }
  .schedule-badge.personal { background: var(--purple-bg); color: var(--purple); }
  .schedule-badge.health { background: var(--green-bg); color: var(--green); }
  .schedule-badge.other { background: var(--surface); color: var(--text-secondary); }

  /* ── Spending (kept from original, restyled) ── */
  .tabs { display: flex; gap: 0; margin-bottom: 16px; }
  .tab {
    padding: 8px 20px;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.15s;
  }
  .tab:first-child { border-radius: var(--radius-sm) 0 0 var(--radius-sm); }
  .tab:last-child { border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
  .tab.active { background: var(--brand); color: white; border-color: var(--brand); }
  .entries-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  .entries-table th {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid var(--border);
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .entries-table td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
  }
  .entries-table tr:hover td { background: var(--brand-light); }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge-cc { background: rgba(124,58,237,0.1); color: var(--purple); }
  .badge-upi { background: var(--blue-bg); color: var(--blue); }
  .badge-cash { background: var(--brand-light); color: var(--brand); }
  .badge-other { background: var(--surface); color: var(--text-secondary); }
  .amount { font-weight: 600; }
  .amount-cc { color: var(--purple); }

  /* ── Add Form ── */
  .add-form {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
    flex-wrap: wrap;
    align-items: flex-end;
  }
  .add-form input, .add-form select {
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
  }
  .add-form input:focus, .add-form select:focus {
    outline: none;
    border-color: var(--brand);
    box-shadow: 0 0 0 3px rgba(249,115,22,0.1);
  }
  .add-form input::placeholder { color: #a3a3a3; }
  .btn {
    padding: 8px 18px;
    border: none;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }
  .btn-brand { background: var(--brand); color: white; }
  .btn-brand:hover { background: var(--brand-hover); }
  .btn-outline {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
  }
  .btn-outline:hover { border-color: var(--brand); }
  .btn-sm { padding: 5px 12px; font-size: 11px; }
  .btn-danger { background: var(--red); color: white; }
  .btn-danger:hover { opacity: 0.9; }

  /* ── Empty State ── */
  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-secondary);
  }
  .empty-state .empty-icon { font-size: 40px; opacity: 0.3; margin-bottom: 10px; }
  .empty-state .empty-title { font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
  .empty-state .empty-sub { font-size: 13px; }

  /* ── Toast ── */
  #toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
    pointer-events: none;
  }
  .toast-msg {
    padding: 12px 20px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 500;
    box-shadow: var(--shadow-md);
    pointer-events: auto;
    max-width: 320px;
    animation: slideIn 0.2s ease;
  }
  .toast-msg.success { background: var(--green); color: white; }
  .toast-msg.error { background: var(--red); color: white; }
  .toast-msg.info { background: var(--text); color: white; }
  @keyframes slideIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    .sidebar { width: 60px; }
    .sidebar-logo { font-size: 0; padding: 16px 10px; }
    .sidebar-logo .sub { display: none; }
    .sidebar-nav .nav-item span:not(.icon) { display: none; }
    .sidebar-nav .nav-item .badge-count { display: none; }
    .main-wrap { margin-left: 60px; }
    .grid-2, .grid-3 { grid-template-columns: 1fr; }
    .stat-pills { grid-template-columns: 1fr 1fr; }
    .add-form { flex-direction: column; }
    .main { padding: 16px; }
    .header { padding: 12px 16px; }
  }
</style>
</head>
<body>

<!-- ═══════════ SIDEBAR ═══════════ -->
<aside class="sidebar">
  <div class="sidebar-logo">
    AgentHermes
    <span class="sub">Personal Assistant</span>
  </div>
  <nav class="sidebar-nav">
    <button class="nav-item active" data-view="dashboard" onclick="switchView('dashboard')">
      <span class="icon">🏠</span> <span>Dashboard</span>
    </button>
    <button class="nav-item" data-view="tasks" onclick="switchView('tasks')">
      <span class="icon">✅</span> <span>Tasks</span>
      <span class="badge-count" id="task-count">0</span>
    </button>
    <button class="nav-item" data-view="schedule" onclick="switchView('schedule')">
      <span class="icon">📅</span> <span>Schedule</span>
    </button>
    <button class="nav-item" data-view="spending" onclick="switchView('spending')">
      <span class="icon">💰</span> <span>Spending</span>
    </button>
  </nav>
  <div class="sidebar-footer">
    <span class="status-dot"></span>
    Hermes v1.0
  </div>
</aside>

<!-- ═══════════ MAIN ═══════════ -->
<div class="main-wrap">
  <header class="header">
    <h1 id="view-title">Dashboard</h1>
    <span class="date-display" id="date-display"></span>
  </header>

  <div class="main">

    <!-- ═══ DASHBOARD VIEW ═══ -->
    <div class="view active" id="view-dashboard">
      <div class="stat-pills" id="dash-stats"></div>

      <div class="grid-2">
        <div class="section">
          <div class="section-header">
            <div>
              <div class="section-title">📋 Today's Tasks</div>
              <div class="section-subtitle" id="dash-task-sub"></div>
            </div>
            <button class="btn btn-outline btn-sm" onclick="switchView('tasks')">View All →</button>
          </div>
          <div id="dash-tasks"></div>
        </div>

        <div class="section">
          <div class="section-header">
            <div>
              <div class="section-title">📅 Today's Schedule</div>
              <div class="section-subtitle" id="dash-schedule-sub"></div>
            </div>
            <button class="btn btn-outline btn-sm" onclick="switchView('schedule')">Full Schedule →</button>
          </div>
          <div id="dash-schedule"></div>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <div>
            <div class="section-title">💰 Spending Snapshot</div>
            <div class="section-subtitle">This week at a glance</div>
          </div>
          <button class="btn btn-outline btn-sm" onclick="switchView('spending')">Full Tracker →</button>
        </div>
        <div class="stat-pills" id="dash-spending-stats"></div>
      </div>
    </div>

    <!-- ═══ TASKS VIEW ═══ -->
    <div class="view" id="view-tasks">
      <div class="section">
        <div class="section-header">
          <div>
            <div class="section-title">Add Task</div>
            <div class="section-subtitle">Quick-add a task or reminder</div>
          </div>
        </div>
        <div class="add-form">
          <input type="text" id="task-input" placeholder="What needs to be done?" style="flex:2;min-width:200px;">
          <input type="date" id="task-date" style="flex:1;min-width:140px;">
          <input type="text" id="task-time" placeholder="Time (e.g. 15:00)" style="flex:0.8;min-width:100px;">
          <input type="text" id="task-cat" placeholder="Category" style="flex:0.8;min-width:100px;">
          <button class="btn btn-brand" onclick="addTask()">+ Add Task</button>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <div><div class="section-title">All Tasks</div></div>
          <div style="display:flex;gap:8px;">
            <button class="btn btn-outline btn-sm" onclick="filterTasks('all')" id="filter-all">All</button>
            <button class="btn btn-outline btn-sm" onclick="filterTasks('active')" id="filter-active">Active</button>
            <button class="btn btn-outline btn-sm" onclick="filterTasks('done')" id="filter-done">Done</button>
          </div>
        </div>
        <div id="task-list"></div>
      </div>
    </div>

    <!-- ═══ SCHEDULE VIEW ═══ -->
    <div class="view" id="view-schedule">
      <div class="section">
        <div class="section-header">
          <div>
            <div class="section-title">Add Schedule Entry</div>
            <div class="section-subtitle">Classes, meetings, recurring events</div>
          </div>
        </div>
        <div class="add-form">
          <input type="text" id="sched-title" placeholder="Event title" style="flex:2;min-width:180px;">
          <input type="date" id="sched-date" style="flex:1;min-width:130px;">
          <input type="time" id="sched-time" style="flex:0.8;min-width:100px;">
          <select id="sched-cat" style="flex:0.8;min-width:100px;">
            <option value="work">Work</option>
            <option value="personal">Personal</option>
            <option value="health">Health</option>
            <option value="other">Other</option>
          </select>
          <button class="btn btn-brand" onclick="addSchedule()">+ Add</button>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <div>
            <div class="section-title">Upcoming Schedule</div>
            <div class="section-subtitle" id="sched-range"></div>
          </div>
        </div>
        <div id="schedule-list"></div>
      </div>
    </div>

    <!-- ═══ SPENDING VIEW ═══ -->
    <div class="view" id="view-spending">
      <div class="tabs">
        <button class="tab active" onclick="switchSpendingTab('regular')">💵 Regular</button>
        <button class="tab" onclick="switchSpendingTab('credit')">💳 Credit Card</button>
      </div>

      <div class="stat-pills" id="spending-stats"></div>

      <div class="grid-2">
        <div class="section">
          <div class="section-header">
            <div><div class="section-title">📂 Category Breakdown</div></div>
          </div>
          <div class="chart-wrap"><canvas id="categoryChart"></canvas></div>
        </div>
        <div class="section">
          <div class="section-header">
            <div><div class="section-title">📈 Weekly Trend</div></div>
          </div>
          <div class="chart-wrap"><canvas id="weeklyChart"></canvas></div>
        </div>
      </div>

      <div class="grid-2">
        <div class="section">
          <div class="section-header">
            <div><div class="section-title">📅 Daily (14 days)</div></div>
          </div>
          <div class="chart-wrap"><canvas id="dailyChart"></canvas></div>
        </div>
        <div class="section">
          <div class="section-header">
            <div><div class="section-title">💳 Payment Methods</div></div>
          </div>
          <div class="chart-wrap"><canvas id="paymentChart"></canvas></div>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <div><div class="section-title">📋 Recent Entries</div></div>
        </div>
        <table class="entries-table">
          <thead><tr><th>Date</th><th>Category</th><th>Amount</th><th>Payment</th><th>Note</th></tr></thead>
          <tbody id="entriesBody"></tbody>
        </table>
      </div>
    </div>

  </div>
</div>

<div id="toast"></div>

<!-- ═══════════ JAVASCRIPT ═══════════ -->
<script>
// ── State ──
let currentView = 'dashboard';
let currentSpendingTab = 'regular';
let taskFilter = 'active';
let chartInstances = {};
const COLOR_PALETTE = [
  '#f97316','#16a34a','#2563eb','#7c3aed','#dc2626','#ca8a04',
  '#0891b2','#db2777','#4f46e5','#65a30d','#ea580c','#0284c7'
];

// ── View switching ──
function switchView(view) {
  currentView = view;
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + view).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector(`[data-view="${view}"]`).classList.add('active');

  const titles = {dashboard:'Dashboard', tasks:'Tasks', schedule:'Schedule', spending:'Spending'};
  document.getElementById('view-title').textContent = titles[view] || view;

  if (view === 'dashboard') loadDashboard();
  if (view === 'tasks') loadTasks();
  if (view === 'schedule') loadSchedule();
  if (view === 'spending') loadSpendingData();
}

// ── Toast ──
function toast(msg, type='info') {
  const el = document.createElement('div');
  el.className = 'toast-msg ' + type;
  el.textContent = msg;
  document.getElementById('toast').appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ── Date display ──
function updateDateDisplay() {
  const now = new Date();
  document.getElementById('date-display').textContent =
    now.toLocaleDateString('en-IN', {weekday:'long', day:'numeric', month:'long', year:'numeric'});
}

// ═══════════ DASHBOARD ═══════════
async function loadDashboard() {
  const resp = await fetch('/api/overview');
  const d = await resp.json();

  // Stats
  document.getElementById('dash-stats').innerHTML = `
    <div class="stat-pill">
      <div class="label">Tasks Today</div>
      <div class="value brand">${d.today_tasks.length}</div>
      <div class="sub">${d.overdue_tasks.length} overdue</div>
    </div>
    <div class="stat-pill">
      <div class="label">Schedule Today</div>
      <div class="value">${d.today_schedule.length}</div>
      <div class="sub">events</div>
    </div>
    <div class="stat-pill">
      <div class="label">Weekly Spend</div>
      <div class="value">₹${d.spending.weekly_regular_total.toLocaleString('en-IN')}</div>
      <div class="sub">of ₹${d.spending.weekly_budget.toLocaleString('en-IN')}</div>
    </div>
    <div class="stat-pill">
      <div class="label">Total Tasks</div>
      <div class="value">${d.total_tasks}</div>
      <div class="sub">all time</div>
    </div>
  `;

  // Tasks
  document.getElementById('dash-task-sub').textContent =
    `${d.today_tasks.filter(t=>t.done).length}/${d.today_tasks.length} done`;
  document.getElementById('dash-tasks').innerHTML = d.today_tasks.length === 0
    ? '<div class="empty-state"><div class="empty-icon">✅</div><div class="empty-title">No tasks today</div><div class="empty-sub">Add one in the Tasks tab</div></div>'
    : d.today_tasks.map(t => `
      <div class="task-item ${t.done?'done':''}">
        <div class="task-check ${t.done?'checked':''}">${t.done?'✓':''}</div>
        <div class="task-body">
          <div class="task-title">${escapeHtml(t.title)}</div>
          <div class="task-meta">${t.category || ''} ${t.time || ''}</div>
        </div>
      </div>
    `).join('');

  // Overdue
  if (d.overdue_tasks.length > 0) {
    document.getElementById('dash-tasks').innerHTML +=
      '<div style="margin-top:12px;font-size:11px;font-weight:600;color:var(--red);text-transform:uppercase;">⚠ Overdue</div>' +
      d.overdue_tasks.slice(0,3).map(t => `
        <div class="task-item" style="border-color:var(--red-bg);">
          <div class="task-body">
            <div class="task-title">${escapeHtml(t.title)}</div>
            <div class="task-meta" style="color:var(--red);">Due ${t.date}</div>
          </div>
        </div>
      `).join('');
  }

  // Schedule
  document.getElementById('dash-schedule-sub').textContent =
    `${d.today_schedule.length} events today`;
  document.getElementById('dash-schedule').innerHTML = d.today_schedule.length === 0
    ? '<div class="empty-state"><div class="empty-icon">📅</div><div class="empty-title">Nothing scheduled</div><div class="empty-sub">Add events in the Schedule tab</div></div>'
    : d.today_schedule.map(s => `
      <div class="schedule-item">
        <div class="schedule-time">${s.time || 'All day'}</div>
        <div class="schedule-body">
          <div class="s-title">${escapeHtml(s.title)}</div>
          ${s.description ? `<div class="s-desc">${escapeHtml(s.description)}</div>` : ''}
        </div>
        <span class="schedule-badge ${s.category || 'other'}">${s.category || 'other'}</span>
      </div>
    `).join('');

  // Spending snapshot
  const s = d.spending;
  const pct = s.weekly_budget ? Math.round(s.weekly_regular_total/s.weekly_budget*100) : 0;
  document.getElementById('dash-spending-stats').innerHTML = `
    <div class="stat-pill">
      <div class="label">Spent This Week</div>
      <div class="value ${pct >= 80 ? 'red' : pct >= 50 ? 'brand' : ''}">₹${s.weekly_regular_total.toLocaleString('en-IN')}</div>
      <div class="sub">${pct}% of budget</div>
    </div>
    <div class="stat-pill">
      <div class="label">Credit Card</div>
      <div class="value">₹${s.weekly_cc_total.toLocaleString('en-IN')}</div>
      <div class="sub">this week</div>
    </div>
    <div class="stat-pill">
      <div class="label">Total Entries</div>
      <div class="value">${s.total_entries}</div>
      <div class="sub">all time</div>
    </div>
  `;
}

// ═══════════ TASKS ═══════════
async function loadTasks() {
  const resp = await fetch('/api/tasks');
  const data = await resp.json();
  let tasks = data.tasks || [];
  if (taskFilter === 'active') tasks = tasks.filter(t => !t.done);
  else if (taskFilter === 'done') tasks = tasks.filter(t => t.done);
  tasks.sort((a,b) => (a.date||'').localeCompare(b.date||'') || (a.time||'').localeCompare(b.time||''));

  document.getElementById('task-count').textContent = data.tasks.filter(t => !t.done).length;

  const todayStr = new Date().toISOString().split('T')[0];
  document.getElementById('task-list').innerHTML = tasks.length === 0
    ? '<div class="empty-state"><div class="empty-icon">✅</div><div class="empty-title">No tasks</div><div class="empty-sub">Add your first task above</div></div>'
    : tasks.map(t => `
      <div class="task-item ${t.done?'done':''}">
        <div class="task-check ${t.done?'checked':''}" onclick="toggleTask(${t.id})">${t.done?'✓':''}</div>
        <div class="task-body">
          <div class="task-title">${escapeHtml(t.title)}</div>
          <div class="task-meta">${t.category||''} ${t.time||''} ${t.note||''}</div>
        </div>
        <div class="task-date ${t.date < todayStr && !t.done ? 'overdue' : ''}">${t.date||''}</div>
        <div class="task-actions">
          <button onclick="deleteTask(${t.id})" title="Delete">🗑</button>
        </div>
      </div>
    `).join('');
}

function filterTasks(f) {
  taskFilter = f;
  ['all','active','done'].forEach(x => {
    const btn = document.getElementById('filter-'+x);
    if (btn) btn.style.background = x===f ? 'var(--brand)' : '';
    if (btn) btn.style.color = x===f ? 'white' : '';
  });
  loadTasks();
}

async function addTask() {
  const title = document.getElementById('task-input').value.trim();
  const date = document.getElementById('task-date').value;
  const time = document.getElementById('task-time').value;
  const category = document.getElementById('task-cat').value.trim();

  if (!title) { toast('Please enter a task title', 'error'); return; }

  await fetch('/api/tasks', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({title, date: date || new Date().toISOString().split('T')[0], time, category})
  });
  document.getElementById('task-input').value = '';
  document.getElementById('task-time').value = '';
  document.getElementById('task-cat').value = '';
  toast('Task added', 'success');
  loadTasks();
}

async function toggleTask(id) {
  await fetch('/api/tasks/' + id, {method: 'PUT'});
  loadTasks();
  if (currentView === 'dashboard') loadDashboard();
}

async function deleteTask(id) {
  await fetch('/api/tasks/' + id, {method: 'DELETE'});
  toast('Task deleted', 'info');
  loadTasks();
  if (currentView === 'dashboard') loadDashboard();
}

// ═══════════ SCHEDULE ═══════════
async function loadSchedule() {
  const resp = await fetch('/api/schedule');
  const data = await resp.json();
  let items = data.schedule || [];
  items.sort((a,b) => (a.date||'').localeCompare(b.date||'') || (a.time||'').localeCompare(b.time||''));

  const today = new Date().toISOString().split('T')[0];
  document.getElementById('sched-range').textContent =
    `${items.length} total entries`;

  document.getElementById('schedule-list').innerHTML = items.length === 0
    ? '<div class="empty-state"><div class="empty-icon">📅</div><div class="empty-title">Nothing scheduled</div><div class="empty-sub">Add your first entry above</div></div>'
    : items.map(s => `
      <div class="schedule-item">
        <div class="schedule-time">${s.date === today ? '<b>Today</b><br>' : ''}${s.time||'All day'}</div>
        <div class="schedule-body">
          <div class="s-title">${escapeHtml(s.title)}</div>
          <div class="s-desc">${s.date||''} ${s.description||''}</div>
        </div>
        <span class="schedule-badge ${s.category||'other'}">${s.category||'other'}</span>
        <button onclick="deleteSchedule(${s.id})" style="background:none;border:none;cursor:pointer;color:var(--text-secondary);font-size:14px;">🗑</button>
      </div>
    `).join('');
}

async function addSchedule() {
  const title = document.getElementById('sched-title').value.trim();
  const date = document.getElementById('sched-date').value;
  const time = document.getElementById('sched-time').value;
  const category = document.getElementById('sched-cat').value;

  if (!title) { toast('Please enter a title', 'error'); return; }

  await fetch('/api/schedule', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({title, date: date || new Date().toISOString().split('T')[0], time, category})
  });
  document.getElementById('sched-title').value = '';
  document.getElementById('sched-time').value = '';
  toast('Schedule added', 'success');
  loadSchedule();
  if (currentView === 'dashboard') loadDashboard();
}

async function deleteSchedule(id) {
  await fetch('/api/schedule/' + id, {method: 'DELETE'});
  toast('Event removed', 'info');
  loadSchedule();
}

// ═══════════ SPENDING ═══════════
function switchSpendingTab(tab) {
  currentSpendingTab = tab;
  document.querySelectorAll('#view-spending .tab').forEach((t,i) => {
    t.classList.toggle('active', (i===0 && tab==='regular') || (i===1 && tab==='credit'));
  });
  loadSpendingData();
}

let spendingChartInstances = {};
function destroySpendingCharts() {
  Object.values(spendingChartInstances).forEach(c => c.destroy());
  spendingChartInstances = {};
}

function makeChart(canvasId, config) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  spendingChartInstances[canvasId] = new Chart(ctx, {
    ...config,
    options: {
      ...config.options,
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#737373', font: { size: 11 }, usePointStyle: true, padding: 14 } } },
      scales: config.options?.scales || {}
    }
  });
}

async function loadSpendingData() {
  const resp = await fetch('/api/data');
  const d = await resp.json();

  const regTotal = currentSpendingTab === 'regular' ? d.weekly_regular_total : d.weekly_cc_total;
  const limit = currentSpendingTab === 'regular' ? d.weekly_budget : null;
  const pct = limit ? Math.round(regTotal / limit * 100) : 0;
  const remaining = limit ? limit - regTotal : 0;
  const critClass = pct >= 100 ? 'red' : pct >= 80 ? 'brand' : '';

  const entries = currentSpendingTab === 'regular'
    ? d.entries.filter(e => !e.is_credit_card)
    : d.entries.filter(e => e.is_credit_card);

  document.getElementById('spending-stats').innerHTML = `
    <div class="stat-pill">
      <div class="label">${currentSpendingTab === 'regular' ? 'Weekly Total' : 'Credit Card Total'}</div>
      <div class="value ${critClass}">₹${regTotal.toLocaleString('en-IN')}</div>
      ${limit ? `<div class="sub">of ₹${limit.toLocaleString('en-IN')} (${pct}%)</div>` : ''}
    </div>
    ${limit ? `<div class="stat-pill">
      <div class="label">Remaining</div>
      <div class="value ${remaining >= 0 ? 'green' : 'red'}">₹${remaining.toLocaleString('en-IN')}</div>
    </div>` : ''}
    <div class="stat-pill">
      <div class="label">Entries</div>
      <div class="value">${entries.length}</div>
    </div>
    <div class="stat-pill">
      <div class="label">Avg Per Entry</div>
      <div class="value">₹${entries.length ? Math.round(entries.reduce((s,e) => s+e.amount,0) / entries.length).toLocaleString('en-IN') : 0}</div>
    </div>
  `;

  destroySpendingCharts();

  // Category doughnut
  const catData = d.categories.filter(c => c.total > 0);
  if (catData.length > 0) {
    makeChart('categoryChart', {
      type: 'doughnut',
      data: {
        labels: catData.map(c => c.name),
        datasets: [{ data: catData.map(c => c.total), backgroundColor: COLOR_PALETTE, borderColor: '#fff', borderWidth: 2 }]
      },
      options: { cutout: '60%', plugins: { legend: { position: 'bottom' } } }
    });
  }

  // Weekly bar
  const wkLabels = d.weekly_history.map(w => w.week);
  makeChart('weeklyChart', {
    type: 'bar',
    data: {
      labels: wkLabels,
      datasets: [
        { label: 'Regular', data: d.weekly_history.map(w => w.regular), backgroundColor: '#f97316', borderRadius: 4 },
        { label: 'Credit Card', data: d.weekly_history.map(w => w.credit_card), backgroundColor: '#7c3aed', borderRadius: 4 }
      ]
    },
    options: {
      scales: {
        x: { ticks: { color: '#737373' }, grid: { display: false } },
        y: { ticks: { color: '#737373', callback: v => '₹'+v }, grid: { color: '#f5f5f5' } }
      }
    }
  });

  // Daily line
  const dayLabels = d.daily_spending.map(dd => dd.date.slice(5));
  makeChart('dailyChart', {
    type: 'line',
    data: {
      labels: dayLabels,
      datasets: [
        { label: 'Regular', data: d.daily_spending.map(dd => dd.regular), borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,0.08)', fill: true, tension: 0.3, pointRadius: 2 },
        { label: 'Credit Card', data: d.daily_spending.map(dd => dd.credit_card), borderColor: '#7c3aed', backgroundColor: 'rgba(124,58,237,0.08)', fill: true, tension: 0.3, pointRadius: 2 }
      ]
    },
    options: {
      scales: {
        x: { ticks: { color: '#737373', maxTicksLimit: 7 }, grid: { display: false } },
        y: { ticks: { color: '#737373', callback: v => '₹'+v }, grid: { color: '#f5f5f5' } }
      }
    }
  });

  // Payment pie
  const pmLabels = Object.keys(d.payment_methods);
  if (pmLabels.length > 0) {
    makeChart('paymentChart', {
      type: 'pie',
      data: {
        labels: pmLabels,
        datasets: [{ data: Object.values(d.payment_methods), backgroundColor: COLOR_PALETTE, borderColor: '#fff', borderWidth: 2 }]
      },
      options: { plugins: { legend: { position: 'bottom' } } }
    });
  }

  // Entries table
  document.getElementById('entriesBody').innerHTML = entries.slice(0, 20).map(e => `
    <tr>
      <td>${e.date}</td>
      <td>${e.category.replace(/_/g, ' ')}</td>
      <td class="amount${e.is_credit_card ? ' amount-cc' : ''}">₹${e.amount.toLocaleString('en-IN')}</td>
      <td><span class="badge badge-${e.payment_method==='upi'?'upi':e.payment_method==='cash'?'cash':e.is_credit_card?'cc':'other'}">${e.payment_method||'—'}</span></td>
      <td style="color:var(--text-secondary)">${e.note||'—'}</td>
    </tr>
  `).join('');
}

// ── Utility ──
function escapeHtml(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// ── Init ──
updateDateDisplay();
setInterval(updateDateDisplay, 60000);
loadDashboard();
setInterval(() => { if (currentView === 'dashboard') loadDashboard(); }, 30000);
</script>
</body>
</html>"""


# ═══════════════════════════════════════════
#  HTTP SERVER
# ═══════════════════════════════════════════

class AgentHermesHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/index.html":
            self._serve_html(AGENTHERMES_HTML)

        elif path == "/api/data":
            self._serve_json(get_dashboard_data())

        elif path == "/api/summary":
            self._serve_text(get_summary())

        elif path == "/api/overview":
            self._serve_json(get_overview())

        elif path == "/api/tasks":
            data = load_json(TASKS_PATH)
            self._serve_json(data)

        elif path == "/api/schedule":
            data = load_json(SCHEDULE_PATH)
            self._serve_json(data)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()

        if path == "/api/tasks":
            data = load_json(TASKS_PATH)
            task = json.loads(body)
            task["id"] = max([t.get("id", 0) for t in data["tasks"]], default=0) + 1
            task["done"] = False
            task["created"] = datetime.now().isoformat()
            data["tasks"].append(task)
            save_json(TASKS_PATH, data)
            self._serve_json(task, 201)

        elif path == "/api/schedule":
            data = load_json(SCHEDULE_PATH)
            item = json.loads(body)
            item["id"] = max([s.get("id", 0) for s in data["schedule"]], default=0) + 1
            item["created"] = datetime.now().isoformat()
            data["schedule"].append(item)
            save_json(SCHEDULE_PATH, data)
            self._serve_json(item, 201)

        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        path = self.path.split("?")[0]
        parts = path.strip("/").split("/")

        if len(parts) == 3 and parts[1] == "tasks":
            task_id = int(parts[2])
            data = load_json(TASKS_PATH)
            for t in data["tasks"]:
                if t.get("id") == task_id:
                    t["done"] = not t.get("done", False)
                    save_json(TASKS_PATH, data)
                    self._serve_json(t)
                    return
            self.send_response(404)
            self.end_headers()

        elif len(parts) == 3 and parts[1] == "schedule":
            item_id = int(parts[2])
            body = self._read_body()
            data = load_json(SCHEDULE_PATH)
            for s in data["schedule"]:
                if s.get("id") == item_id:
                    updates = json.loads(body)
                    s.update(updates)
                    save_json(SCHEDULE_PATH, data)
                    self._serve_json(s)
                    return
            self.send_response(404)
            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        path = self.path.split("?")[0]
        parts = path.strip("/").split("/")

        if len(parts) == 3 and parts[1] == "tasks":
            task_id = int(parts[2])
            data = load_json(TASKS_PATH)
            data["tasks"] = [t for t in data["tasks"] if t.get("id") != task_id]
            save_json(TASKS_PATH, data)
            self._serve_json({"ok": True})

        elif len(parts) == 3 and parts[1] == "schedule":
            item_id = int(parts[2])
            data = load_json(SCHEDULE_PATH)
            data["schedule"] = [s for s in data["schedule"] if s.get("id") != item_id]
            save_json(SCHEDULE_PATH, data)
            self._serve_json({"ok": True})

        else:
            self.send_response(404)
            self.end_headers()

    # ── Helpers ──

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8") if length else "{}"

    def _serve_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _serve_text(self, text: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def log_message(self, format, *args):
        pass


def main():
    port = 8765
    if len(sys.argv) > 2 and sys.argv[1] == "--port":
        port = int(sys.argv[2])

    server = HTTPServer(("0.0.0.0", port), AgentHermesHandler)
    print(f"🦊 AgentHermes Dashboard → http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
