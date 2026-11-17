# SIP Tickets Miner

A local web app for exploring SIP support tickets in
`resources/issues_export.csv`. Describe a problem in English or Italian to find
similar tickets, suggest a category for a new ticket, or identify people who
handled similar issues.

## Features

| Page | What it does |
|---|---|
| [`/`](http://localhost:8765/) | Finds up to three matching tickets. An existing ticket ID is shown first; other matches are ranked from a local BM25 shortlist by GitHub Copilot. |
| [`/categorize`](http://localhost:8765/categorize) | Suggests an `ISSUETYPE` for a new ticket using similar tickets, with alternatives and examples. Copilot chooses from shortlisted categories; if its ranking call fails, a local weighted vote is used. |
| [`/recommend`](http://localhost:8765/recommend) | Recommends up to three assignees from similar assigned tickets. Copilot ranks people from a local BM25 shortlist and provides its confidence estimate, explanation, and supporting tickets. If its call fails or the response cannot be parsed, a local score vote over the five closest assigned tickets is used. |

The pages have English and Italian text and light and dark themes. Each query is
independent; the app does not use conversation history.

## Requirements

- Python 3 (recommended: **3.14**). The server uses only the Python standard
  library; no pip packages are required.
- The ticket export at `resources/issues_export.csv`, already there by default.
- A free local port `8765`.
- GitHub Copilot CLI (latest stable release), installed and signed in for ticket
  search, category suggestions, and expert recommendations.
- Node.js **22 or later**, with its bundled npm, if installing Copilot CLI
  through npm. The setup panel uses this installation method and can start
  device-code sign-in. See the [official CLI installation requirements](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli).
- On Windows, PowerShell **6 or later** for Copilot CLI.

The web server currently checks Copilot readiness before accepting requests to
all three analysis endpoints.

## Run

From the project root:

```bash
python3 chatbot/sip-chatbot-web.py
```

On Windows:

```powershell
python chatbot/sip-chatbot-web.py
```

The server listens at <http://localhost:8765/> and attempts to open the page in
your browser. Keep the terminal running while using the app; press `Ctrl+C` to
stop it. Always access pages through the local URL rather than opening an HTML
file directly.

## How it works

- `TicketIndex.from_csv()` loads ticket fields and prepares the local BM25
  index. `TicketIndex.shortlist_scored()` provides ranked matches and scores.
- `lookup()` handles ticket-ID detection, shortlisting, Copilot ranking and
  fallback results.
- `categorize()` suggests an issue type from similar tickets, using Copilot
  ranking and a local fallback.
- `recommend()` sends the problem description and up to 30 shortlisted assigned
  tickets to Copilot. Copilot can recommend up to three assignees and cite up
  to five tickets in total. The app drops people outside the shortlist and
  tickets that are not in the shortlist or are assigned to someone else;
  ticket summaries always come from the CSV. If Copilot fails or its response
  cannot be parsed, `recommend_local()` ranks assignees by aggregating BM25
  scores from the five closest assigned tickets. A valid empty Copilot result
  means no recommendations. If no assigned ticket matches the description, no
  Copilot call is made.
- The server exposes `POST /api/chat`, `POST /api/categorize` and
  `POST /api/recommend`. It binds to `127.0.0.1`, checks local Host/Origin
  headers and serves only whitelisted static files.

## Privacy

All three features send the query and up to 30 shortlisted ticket snippets to
GitHub Copilot. Search snippets contain the ticket ID, summary, description,
status and assignee; categorization snippets contain the ID, summary,
description and `ISSUETYPE`; expert recommendation snippets contain the ID,
summary, description and assignee of assigned tickets. Expert recommendation's
local BM25 shortlist is sent to Copilot for ranking; only assignees and tickets
from that shortlist can appear in the result. The included CSV is a real
export: obtain approval or anonymize the data before using Copilot with it.

## Presentation plan

Open [`presentation-plan.html`](presentation-plan.html) directly in a browser for
a plain-English presentation plan covering the problem, features, acceptance
checks, AI-assisted development and known limitations. It is a standalone reading
guide, separate from the running app, and can be printed or saved as a PDF.

## Tests

Run the chatbot unit tests from the project root:

```bash
python3 -m unittest discover -s chatbot
```

See [`chatbot/README.md`](chatbot/README.md) for setup, usage and
troubleshooting details. Feature requirements and acceptance criteria are
documented in [`SPEC.md`](SPEC.md); OpenSpec proposals and specifications are
under [`openspec/`](openspec/).