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
| [`/recommend`](http://localhost:8765/recommend) | Recommends up to three assignees based on the five closest assigned tickets. The recommendation logic is local and does not send ticket data to Copilot. |

The pages have English and Italian text and light and dark themes. Each query is
independent; the app does not use conversation history.

## Requirements

- Python 3. The server uses only the Python standard library.
- The ticket export at `resources/issues_export.csv`.
- A free local port `8765`.
- GitHub Copilot CLI installed and signed in for ticket search and category
  suggestions. The setup panel can install the CLI (requires Node.js and npm)
  and start device-code sign-in.

The web server currently checks Copilot readiness before accepting requests to
all three analysis endpoints. The expert recommendation calculation itself
does not call Copilot.

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
- `recommend()` aggregates scores for assignees of the closest assigned
  tickets; it does not call an LLM.
- The server exposes `POST /api/chat`, `POST /api/categorize` and
  `POST /api/recommend`. It binds to `127.0.0.1`, checks local Host/Origin
  headers and serves only whitelisted static files.

## Privacy

The ticket search and categorization features send the query and up to 30
shortlisted ticket snippets to GitHub Copilot. Search snippets contain the
ticket ID, summary, description, status and assignee; categorization snippets
contain the ID, summary, description and `ISSUETYPE`. The expert recommendation
feature uses the CSV locally and sends nothing to Copilot. The included CSV is
a real export: obtain approval or anonymize the data before using Copilot with
it.

## Tests

Run the chatbot unit tests from the project root:

```bash
python3 -m unittest discover -s chatbot
```

See [`chatbot/README.md`](chatbot/README.md) for setup, usage and
troubleshooting details. Feature requirements and acceptance criteria are
documented in [`SPEC.md`](SPEC.md); OpenSpec proposals and specifications are
under [`openspec/`](openspec/).