
# SIP Tickets Miner (web chat)

Local web chat for project managers: enter a description of a customer's problem (IT/EN) or a ticket number, and the chat returns up to 3 candidates
(ID, title, status, assignee, and a short explanation). Data is read from `../resources/issues_export.csv`.

## How it works

1. If the message contains an ID (e.g. `BTU-4114`) and the ticket exists, it is shown first. If it does not exist, the chat says so and continues searching using the remaining text.
2. A local BM25 search selects up to 30 candidates from the CSV.
3. Copilot CLI (`copilot --silent`, with the prompt passed through stdin) ranks those candidates and returns JSON; the ID, status, and assignee are always read from the CSV.
4. If Copilot is unavailable, the top 3 local matches are shown with a notice. If nothing matches: "No matching ticket found".

Each query is independent (no `--continue`). Status labels are defined in `STATUS_LABELS` in `ticket_lookup.py`
(1/3/4/5/6 follow Jira defaults — the project manager should confirm them); unknown codes are displayed as `Status <code>`.

**Interface language:** English by default; the `EN`/`IT` button in the top-right corner switches to Italian, and the choice is saved
in the browser (`localStorage`). Page text is defined in the `T` object in `static/app.js`, and fixed chat notices
("not found", "no match", etc.) are in `MESSAGES` in `ticket_lookup.py` (`/api/chat` accepts `lang`: `en` or `it`).
Copilot's explanation remains in the language of the query.

**Theme:** light and dark (both muted). On the first visit, the page follows the system theme. The sun/moon icon to the left of
the language selector switches themes; the choice is saved in the browser. Colors are CSS variables in `static/style.css`
(`[data-theme="light"]` / `[data-theme="dark"]`).

**Privacy:** the query and up to 30 ticket excerpts (ID, title, shortened description, status, and assignee) are sent to the Copilot service.
Since the CSV is a real export, this must be approved or the data anonymized before actual use (see `SPEC.md` §10).

## Pages

Categorization: `http://localhost:8765/categorize` suggests an `ISSUETYPE` for a new ticket based on similar tickets and Copilot classification.

Assignee recommendations: `http://localhost:8765/recommend` sends Copilot a description and up to 30 similar tickets with an assignee (ID, title, shortened description, and assignee); Copilot ranks up to 3 people (the `ASSIGNEE` column), providing a percentage, an explanation, and up to 5 supporting tickets. People and tickets outside the list are discarded. If Copilot is unavailable, the local sum of BM25 scores for the 5 most similar tickets is used, with a notice.

All three pages share the chat layout, navigation, EN/IT selector, and light/dark theme.

## Tests

```bash
cd chatbot && python3 -m unittest test_ticket_lookup test_sip_chatbot_web
```

## Files

- `sip-chatbot-web.py` – local server (standard library only, no `pip install` required)
- `ticket_lookup.py` – CSV loading, search, and ranking
- `test_ticket_lookup.py` – unit tests
- `sip-chatbot.html` – page structure (HTML); must be in the same folder as the server
- `sip-categorize.html` – chat for suggesting an `ISSUETYPE`
- `sip-recommend.html` – chat for assignee recommendations
- `static/style.css` – page styles
- `static/app.js` – page logic (chat, setup panel, EN/IT translations, theme switching)
- `static/categorize.js` – chat flow for issue categorization
- `static/theme.js` – applies the saved/system theme before rendering the page
- `sip-chatbot.py` – original Tkinter version (optional)

## Prerequisites

- Python 3
- Node.js with `npm` (required only if Copilot CLI is not already installed)
- A GitHub account with an active Copilot subscription

## Starting the server

```powershell
python sip-chatbot-web.py
```

If `python` is not available in PATH, use `py sip-chatbot-web.py` or the full path to `python.exe`.

The server listens on `http://localhost:8765/` and opens the browser automatically. Keep the server window open while using the chat. Press `Ctrl+C` to stop the server.

Always open the page through `http://localhost:8765/`. Double-clicking the HTML file does not work because no server is running that way.

## First use

A panel at the top of the page shows the current status:

1. **Copilot is not installed** – click "Yes, install". The server runs `npm install -g @github/copilot` and streams the output live.
2. **Not signed in** – click "Sign in". Open the displayed link (`https://github.com/login/device`), enter the displayed code, and authorize access. The page detects the sign-in automatically.
3. **Ready** – the panel disappears, and you can write messages.

The "Send" button is disabled until Copilot is ready.

## Using the chat

- Type a message and press Enter or click "Send".
- The first response may take around ten seconds or longer because `copilot` is launched for each message.
- Messages are sent one at a time. Each query is independent; previous messages are not taken into account.

## Troubleshooting

| Problem | Solution |
|---|---|
| "Failed to fetch" / "Server is not reachable" | The server has not been started or has stopped. Restart it and refresh the page. |
| Port 8765 is already in use | Close the other program using that port or change `PORT` in `sip-chatbot-web.py`. |
| "npm was not found" | Install Node.js from https://nodejs.org, then restart the terminal. |
| Installed, but "not in PATH" | Restart the terminal and the server. |
| Sign-in fails | Run `copilot login` manually in the terminal, or set `GH_TOKEN`/`COPILOT_GITHUB_TOKEN`. |
| "LLM ranking was unavailable" | Check the server console for `LLM ranking failed` and the traceback: errors from the CLI call or JSON response parsing are logged there. Keyword results remain available. |

## Security

- The server listens only on `127.0.0.1`, so it is accessible only on your computer.
- Requests with foreign `Host` and `Origin` headers are rejected.
- All queries use the Copilot account of the person who started the server. Do not expose it to the internet without user authentication and rate limiting.
