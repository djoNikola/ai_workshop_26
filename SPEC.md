# SPEC — Ticket Lookup Chatbot for Client Status Requests

Source: `resources/problem_brief.md`. Phase I PoC.

## 1. Goal

The PM types a free-text description of a client's issue, in Italian or English. The chatbot returns up to 3 candidate SIP tickets, each with **task ID, short summary, status and assignee**. This replaces manual scanning of the CSV export.

## 2. Scope

**In scope**
- Single-user local web chat named **SIP Tickets Miner** (the bot is "Miner"), based on the existing `chatbot/sip-chatbot-web.py` and `sip-chatbot.html`.
- UI in English (default) or Italian, switchable in the page (EN/IT, choice saved in `localStorage`), and light/dark themes (first visit follows the system theme, choice saved).
- Ticket data: `resources/issues_export.csv`, used for both development and the demo.
- LLM-based matching of a free-text description to tickets.
- Ticket-ID detection in the input, with fallback to text search when the ID does not exist.
- Italian and English input. The LLM's match reason is in the language of the question; the fixed chat notes (not found, no match, LLM unavailable, exact ID match) follow the UI language.

**Out of scope**
- Live connection to the ticketing system.
- Multi-user use, authentication, hosting.
- Writing to or updating tickets.
- The "focal point per environment" file.
- Conversation memory beyond a single lookup. Each query is an independent lookup.

## 3. User flow

1. The PM starts `python chatbot/sip-chatbot-web.py`; the browser opens `http://localhost:8765/`.
2. The PM types a client's description, for example "il cliente di Olbia non riesce a stampare le etichette, ticket BTU-9999".
3. The system extracts any ticket-ID-like token (`BTU-\d+`).
   - If the ID exists, that ticket is returned first (exact match).
   - If it does not exist, the chat says so and continues with step 4.
4. The system shortlists tickets, and the LLM ranks the shortlist against the description.
5. The chat shows up to 3 candidates, best first, each with ID, summary, status, assignee and a short reason for the match.
6. If nothing is relevant, the chat says "no matching ticket found" and suggests adding detail. It does not invent a ticket.

## 4. Matching approach (decision)

**Hybrid: local shortlist, then LLM re-rank.** The CSV has ~3,800 tickets with long descriptions, which is too large to send in one prompt.

0. **ID shortcut**: a ticket ID in the message (`[A-Za-z]{2,10}-\d+`, case-insensitive) is looked up directly. An existing ticket is listed first. A missing ID adds a "not found" note, and the message with the ID removed continues to step 2. If only an existing ID was given, steps 2–3 are skipped.
1. **Load**: parse the CSV once at server start, keeping `PKEY, SUMMARY, DESCRIPTION, ISSUESTATUS, ASSIGNEE`. Trim descriptions to 500 characters. `[NULL]` values become empty.
2. **Shortlist** (local, no LLM): BM25 ranking (k1 = 1.5, b = 0.75, stdlib only) over SUMMARY + DESCRIPTION, keeping the top 30.
   - Text is lowercased and accents removed. Tokens of 2 characters or fewer and common Italian/English stopwords are dropped.
   - Each token is cut to its first 5 characters as a crude stem, so "consegna", "consegnati" and "consegnare" match.
   - SUMMARY counts twice, so it weighs more than DESCRIPTION.
   - Tickets sharing no token with the query are never shortlisted. An empty shortlist means "no match" without calling the LLM.
3. **Re-rank** (LLM via the existing Copilot CLI call, one independent `copilot -p` call per query, 120 s timeout): the prompt contains the PM's query and the shortlist (`pkey`, `summary`, `description`, `status`, `assignee`). The LLM must reply with JSON only: up to 3 `{pkey, reason}` items, or an empty list. The reply is parsed leniently (first valid JSON object in the output). IDs not in the shortlist are dropped.
4. **Render**: the server looks up ID, summary, status and assignee from the loaded data by `pkey`, not from LLM text. This stops the LLM from altering factual fields.
5. **Fallback**: if the LLM call fails or returns unusable output, show the top 3 shortlist tickets (without a reason) and a notice that LLM ranking was unavailable. If the LLM returns an empty list, answer "no match".

Result limit: at most 3 candidates in total, with ID-matched tickets first.

**Known limitation**: the shortlist is lexical. A cross-language query (for example English words against an Italian ticket) can miss the right ticket when no tokens overlap, and the LLM only sees what the shortlist contains.

## 5. Requirements

| ID | Requirement |
|----|-------------|
| R1 | The PM can enter a free-text query in a web chat and get a response. |
| R2 | The query may be Italian, English or mixed. |
| R3 | The response lists at most 3 candidates. Each has task ID (`PKEY`), summary, status, assignee and a one-line match reason. |
| R4 | If the query contains an existing ticket ID, that ticket is listed first. |
| R5 | If the query contains a non-existent ticket ID, the response says it was not found and still runs text search on the remaining text. |
| R6 | If no candidate is relevant, the response says no match was found. It must not return unrelated tickets. |
| R7 | Candidate fields (ID, status, assignee, summary) come from the CSV, never from LLM-generated text. |
| R8 | Status codes are shown as readable labels (see §7). |
| R9 | A null assignee is shown as "Unassigned". |
| R10 | If the LLM call fails or returns invalid JSON, the chat shows the local shortlist top 3 and a notice that LLM ranking was unavailable. |
| R11 | The server runs locally, binds only to `127.0.0.1` and keeps the existing Host/Origin checks. |
| R12 | Responses arrive within ~30 s (the Copilot CLI call dominates). |
| R13 | The UI is English by default with an EN/IT switch; the choice persists. Fixed chat notes follow the selected language, and unknown `lang` values fall back to English. |
| R14 | The UI offers light and dark themes, following the system theme on first visit and persisting the user's choice. |
| R15 | The server serves only the whitelisted static files; any other `/static` path returns 404. |

## 6. Acceptance criteria

- **AC1** (R4): the query `BTU-4114` returns BTU-4114 as the first result with its summary, status label and assignee `alfmancu`.
- **AC2** (R5): the query `BTU-99999 servizio per pannellini e stampanti preanalitica` reports that BTU-99999 does not exist and lists BTU-4114 among the candidates.
- **AC3** (R1–R3): the query `il cliente vuole filtrare i campioni consegnati e da consegnare` returns BTU-4115 within the top 3.
- **AC4** (R2): the English query `deliver sample management Cardarelli Napoli` returns BTU-4113 within the top 3.
- **AC5** (R6): the query `ricetta per la torta di mele` returns the "no matching ticket found" message and no tickets.
- **AC6** (R7): for every displayed candidate, ID, status and assignee exactly equal the CSV row.
- **AC7** (R10): with the LLM call forced to fail, the shortlist top 3 is returned with the fallback notice.
- **AC8** (R3): no response contains more than 3 candidates.

These expected results must be checked against the real CSV before the demo. If a ranking differs, adjust the query or the expected ticket, not the criteria.

## 7. Data and boundaries

**Source**: `resources/issues_export.csv` (3,816 rows). It is a real export, so it may contain client-identifying text. **Open risk in §10.**

| Field | Use |
|-------|-----|
| `PKEY` | Task ID shown to PM, and ID shortcut key |
| `SUMMARY` | Matching and display |
| `DESCRIPTION` | Matching (trimmed) |
| `ISSUESTATUS` | Status shown to PM, via a status map |
| `ASSIGNEE` | Assignee shown to PM |

**Status map**: `ISSUESTATUS` is a numeric code with no decode table in the export. Add a small config dict in the server (`STATUS_LABELS = {...}`). Unknown codes display as `Status <code>`. The real labels for the top codes (6, 10008, 1, 10001, 10002) must be confirmed by the PM (**open item**).

**Data boundaries**
- Only the 5 fields above leave the CSV loader. Other columns (reporter, environment, etc.) are never sent to the LLM.
- Only the query and the shortlist (≤30 tickets) are included in an LLM prompt; the full CSV is never sent.
- No data is written to disk (no logs of queries or results beyond the console).

## 8. Integration assumptions

- Copilot CLI (`copilot -p`) is installed and logged in, as already handled by `sip-chatbot-web.py`.
- Change `run_copilot` so that each lookup is independent (no `--continue`) and the prompt requests JSON-only output.
- New endpoint behaviour: `/api/chat` keeps its URL; the reply becomes the formatted candidate list. The request body is `{"prompt": ..., "lang": "en"|"it"}`; an unknown or missing `lang` falls back to `en`. `ticket_lookup.lookup()` returns its fixed notes (`MESSAGES`) in that language. Errors return an `error` key (`not_ready`, `generic`) plus `reply`.
- Setup/login failures are reported as keys (`SetupError`: `npm_missing`, `install_failed`, `not_in_path`, `login_failed`) that the page translates.
- Front end is split into `sip-chatbot.html` (structure), `static/style.css` (CSS variables for light/dark themes), `static/app.js` (chat, setup panel, EN/IT texts, theme toggle) and `static/theme.js` (loaded in `<head>` to apply the theme before first render). The server serves only the files listed in `STATIC_FILES`; any other `/static` path returns 404.
- UI: user messages on the right, Miner's on the left (mining-helmet avatar); ticket cards show the ID as a badge and status/assignee as pills.
- Python 3, standard library only if practical. If a ranking library is added, it is pinned in a `requirements.txt`.

## 9. Test cases

| # | Type | Input | Expected |
|---|------|-------|----------|
| T1 | Unit | CSV load | 3,816 rows, no crash on `[NULL]` values or empty assignees |
| T2 | Unit | ID extraction from `"ticket BTU-4114 non va"` | `BTU-4114` |
| T3 | Unit | ID extraction, no ID | none |
| T4 | Unit | Status map, known and unknown code | label, and `Status <code>` |
| T5 | Unit | Shortlist for the AC3 query | BTU-4115 in the top 30 |
| T6 | Unit | LLM JSON parsing: valid, invalid, ID not in shortlist | valid accepted; invalid triggers fallback; unknown ID dropped |
| T7 | Unit | Rendering | at most 3 candidates; fields come from the CSV |
| T8 | E2E (manual) | AC1–AC5 in the browser | as in §6 |
| T9 | E2E | LLM unavailable (AC7) | fallback notice and shortlist |
| T10 | Unit | Fixed notes with `lang="it"`, and with an unknown language | Italian notes; English fallback |

LLM calls are mocked in unit tests. T8 is run live.

## 10. Open risks and decisions

1. **Data privacy.** The brief says no client data leaves the local environment. The LLM-based approach sends the query and ≤30 ticket snippets from a *real* export to GitHub Copilot's service. Options: (a) get explicit approval to use the real export with Copilot; (b) anonymise or synthesise the data for the PoC; (c) use a local model (for example Ollama, as in `resources/example_client.py`). **The mentor or owner should decide this at the scope gate.**
2. **Status code decode.** Needed for R8 (see §7).
3. **Latency.** Each Copilot CLI call takes ~10 s or more. Acceptable for a PoC.
4. **Italian/English matching.** The shortlist is keyword-based, so cross-language queries (English query against Italian tickets) may miss. The LLM only sees what the shortlist contains. Mitigation: a larger N, or an LLM query-expansion step. This is not in the minimal slice.

## 11. Demo scenario

Using `resources/issues_export.csv`, with `python chatbot/sip-chatbot-web.py` running:

1. **Exact ID**: type `BTU-4114`. The ticket appears with summary, status and assignee (AC1).
2. **Wrong ID plus description**: type `BTU-99999 servizio per pannellini e stampanti preanalitica`. The chatbot says BTU-99999 is not found and suggests BTU-4114 (AC2).
3. **Vague Italian description**: type `il cliente vuole filtrare i campioni consegnati e da consegnare`. Candidates are returned, with BTU-4115 among them (AC3).
4. **No match**: type `ricetta per la torta di mele`. The chatbot answers that nothing matched (AC5).

## 12. Minimal slice (for the scope gate)

Must have: CSV load, ID shortcut, keyword shortlist, LLM re-rank with JSON output, status map, formatted top 3 (R1–R7, R10).
Nice to have: reason text, English-to-Italian expansion, richer HTML rendering.
