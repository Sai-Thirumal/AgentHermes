# AgentHermes (Personal Assistant)

A personal spending tracker that works through Telegram. Log expenses naturally, get budget alerts, and visualize everything on a local web dashboard.

## Features

- **Telegram-native** — Log expenses by messaging naturally: *"Spent ₹200 on food via UPI — lunch"*
- **Smart parsing** — Auto-detects amount, category, payment method, and notes
- **Budget alerts** — Warning at 80%, critical at 100% of weekly limits (overall + per-category)
- **Web dashboard** — Dark-themed charts: category breakdown, weekly trends, daily spending, payment methods
- **Credit card tracker** — Separate tab, doesn't count against regular limits
- **Weekly summary** — Auto-delivered every Sunday via Telegram
- **On-demand queries** — Ask *"how's my spending?"* anytime

## Quick Start

```bash
# Clone
git clone https://github.com/Sai-Thirumal/spending-tracker.git
cd spending-tracker

# Install dependencies (none needed — stdlib only!)
# Start the dashboard
python3 dashboard.py --port 8765

# Add an expense
python3 cli.py add "Spent ₹200 on food via UPI — lunch"

# View summary
python3 cli.py summary
```

Open `http://localhost:8765` for the dashboard, or use the public ngrok tunnel at:
**[Live Dashboard](https://nervous-excess-idiocy.ngrok-free.dev)**

## Project Structure

```
spending-tracker/
├── config.json      # Budgets, categories, limits
├── data.json        # All spending entries (auto-created)
├── tracker.py       # Core logic — add, query, budget checks
├── parser.py        # Natural language spending parser
├── cli.py           # Command-line interface
├── dashboard.py     # Web dashboard server (Chart.js)
└── README.md
```

## Budget Configuration

Edit `config.json` to set your own limits:

```json
{
  "weekly_budget": 1500,
  "categories": {
    "food": {"weekly_limit": 500, "keywords": ["food", "lunch", "swiggy", "zomato"]},
    "transport": {"weekly_limit": 300, "keywords": ["uber", "ola", "auto", "metro"]},
    ...
  }
}
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `python3 cli.py add "<message>"` | Parse and log an expense |
| `python3 cli.py summary` | Weekly spending summary |
| `python3 cli.py alerts` | Check budget alerts |
| `python3 cli.py parse "<message>"` | Parse without saving (test mode) |
| `python3 cli.py weekly-summary` | Full summary with alerts (for cron) |
| `python3 cli.py dashboard-data` | JSON data for dashboard API |

## Powered by Hermes

This tracker is designed to run inside [Hermes Agent](https://hermes-agent.nousresearch.com), processing Telegram messages and delivering alerts automatically.
