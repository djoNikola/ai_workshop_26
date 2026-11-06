# SPEC — Ticket Lookup Chatbot for Client Status Requests

Source: `resources/problem_brief.md`. Phase I PoC.

## 1. Goal

The PM types a free-text description of a client's issue, in Italian or English. The chatbot returns up to 3 candidate SIP tickets, each with **task ID, short summary, status and assignee**. This replaces manual scanning of the CSV export.

## 2. Scope

**In scope**
- Single-user local web chat, based on the existing `chatbot/sip-chatbot-web.py` and `sip-chatbot.html`.
- Ticket data: `resources/issues_export.csv`, used for both development and the demo.
- LLM-based matching of a free-text description to tickets.
- Ticket-ID detection in the input, with fallback to text search when the ID does not exist.
- Italian and English input; replies in the language of the question.
- Issue categorization page at `/categorize` (see §13).

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
- New endpoint behaviour: `/api/chat` keeps its URL and `{"reply": ...}` shape; the reply becomes the formatted candidate list. `sip-chatbot.html` may need light changes for rendering (a list or table per candidate).
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

## 13. Issue categorization (new URL `/categorize`)

OpenSpec change: `openspec/changes/issue-categorization/`.

### 13.1 Goal
The PM describes a client's problem (Italian, English or mixed). The app suggests the `ISSUETYPE` category under which the new ticket should be created, using similar tickets in `resources/issues_export.csv`.

### 13.2 Approach
- **URL**: `GET /categorize` (page) and `POST /api/categorize` (`{"prompt": ...}`). `/` and `/api/chat` are unchanged. Same local-only Host/Origin checks (R11).
- **Load**: additionally keep `ISSUETYPE` per ticket. Codes in the export: 10 (2364), 9 (690), 11 (405), 18 (115), 19 (99), 17 (70), 12/13/16/20 (16 each), 15 (9).
- **Shortlist**: the existing BM25 shortlist (top 30). No ticket-ID shortcut: IDs are treated as plain text.
- **Local vote**: score per `ISSUETYPE` = sum of BM25 scores of the shortlisted tickets of that type. The top type is the local suggestion; confidence = its share of the total score.
- **LLM step**: the prompt has the description and the shortlist (`pkey`, `summary`, `description`, `issuetype`). The LLM replies JSON only: `{"category": "<code or null>", "reason": "..."}`; `null` means nothing is relevant and gives "no category could be suggested". A category not present in the shortlist is dropped and the local suggestion is used.
- **Render**: label, confidence, up to 2 alternatives and up to 3 example tickets (ID and summary from the CSV, of the suggested type).
- **Fallback**: LLM failure or invalid output gives the local suggestion with the notice "LLM ranking was unavailable". An empty shortlist gives "no category could be suggested", with no LLM call.
- **Labels**: `ISSUETYPE_LABELS = {...}` config dict; unknown codes show as `Type <code>`.

### 13.3 Requirements

| ID | Requirement |
|----|-------------|
| C1 | `/categorize` shows a form; the PM enters a free-text problem description. |
| C2 | The response suggests exactly one `ISSUETYPE` category, as a readable label. |
| C3 | The response includes a one-line reason, a confidence percentage, up to 2 alternatives and up to 3 example tickets. |
| C4 | Example tickets (ID, summary) come from the CSV and have the suggested `ISSUETYPE`. |
| C5 | The LLM can only choose a category present in the shortlist. |
| C6 | If the LLM fails, the local top category is returned with a notice. |
| C7 | If no ticket shares terms with the description (LLM not called), or the LLM says none is relevant, no category is guessed. |
| C8 | Only the description and ≤30 tickets (`pkey`, `summary`, trimmed description, `ISSUETYPE`) go to the LLM. |
| C9 | Italian, English and mixed input are accepted. |

### 13.4 Acceptance criteria
- **AC-C1** (C2, C3): a description copied from a known ticket returns that ticket's `ISSUETYPE` as the suggestion, with that ticket among the examples.
- **AC-C2** (C7): `ricetta per la torta di mele` returns "no category could be suggested".
- **AC-C3** (C6): with the LLM call forced to fail, the local top category is returned with the notice.
- **AC-C4** (C5): an LLM reply with a category outside the shortlist is ignored.
- **AC-C5** (C3): no response has more than 1 suggestion, 2 alternatives or 3 examples.
- **AC-C6** (C4): every displayed example has ID, summary and `ISSUETYPE` equal to its CSV row.

Expected results must be checked against the real CSV before the demo.

### 13.5 Test cases

| # | Type | Input | Expected |
|---|------|-------|----------|
| TC1 | Unit | CSV load | `ISSUETYPE` kept for every ticket; no crash on empty or `[NULL]` |
| TC2 | Unit | Label map, known and unknown code | label, and `Type <code>` |
| TC3 | Unit | Local vote on a fixed mini index | highest summed score wins; confidence = share |
| TC4 | Unit | LLM JSON parsing: valid, invalid, category not in shortlist | valid accepted; invalid triggers fallback; foreign category dropped |
| TC5 | Unit | Empty shortlist | no suggestion; LLM not called |
| TC6 | Unit | Limits | ≤2 alternatives, ≤3 examples |
| TC7 | Unit | Prompt content | only allowed fields, ≤30 tickets |
| TC8 | E2E (manual) | AC-C1, AC-C2 in the browser at `/categorize` | as in §13.4 |
| TC9 | E2E | LLM unavailable | local suggestion and notice |

### 13.6 Open items and risks
1. **`ISSUETYPE` decode.** The export has only numeric codes. The PM must confirm the labels for 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20.
2. **Class imbalance.** Type 10 is ~62% of tickets, so the vote leans towards it. Confidence and alternatives are shown to compensate; no re-weighting in the first slice.
3. **Lexical shortlist.** Cross-language queries can miss (see §4 and §10). Low confidence is shown.
4. **Data privacy.** Same open risk as §10.1.

### 13.7 Demo scenario
With the server running, open `http://localhost:8765/categorize`:
1. Type a description taken from a known ticket. The suggested category matches that ticket's `ISSUETYPE` (AC-C1).
2. Type `ricetta per la torta di mele`. The app says no category could be suggested (AC-C2).



## 14. Expert recommendation (new URL `/recommend`)

OpenSpec change: `openspec/changes/expert-recommendation/`.

### 14.1 Goal
The PM describes a problem (Italian, English or mixed). The app recommends 2-3 people who can solve it: the `ASSIGNEE` of the most similar tickets in `resources/issues_export.csv`.

### 14.2 Approach
- **URL**: `GET /recommend` (page) and `POST /api/recommend` (`{"prompt": ...}`). Existing endpoints are unchanged; same Host/Origin checks (R11). Copilot is not needed.
- **Tickets**: the existing BM25 shortlist, unassigned tickets dropped, top 5 kept. Ticket IDs in the text are plain text.
- **People**: score per assignee = sum of BM25 scores of their tickets among the 5; top 3 by score (ties by name). Relevance = share of the total score.
- **Render**: per person, name, relevance %, and the similar tickets (ID, summary from the CSV).
- **No match**: no shared terms with any assigned ticket gives "No expert could be recommended".
- **Links**: `/`, `/categorize` and `/recommend` link to each other.

### 14.3 Requirements

| ID | Requirement |
|----|-------------|
| E1 | `/recommend` shows a form; the PM enters a free-text problem description. |
| E2 | The response recommends 2-3 assignees (fewer only if fewer distinct assignees exist among the matched tickets). |
| E3 | Recommendations are based on the 5 most relevant assigned tickets. |
| E4 | Each person is shown with a relevance % and the tickets (ID, summary) they handled, from the CSV. |
| E5 | Unassigned tickets are never used. |
| E6 | With no relevant ticket, nobody is recommended. |
| E7 | The data stays local; no LLM call. |
| E8 | The three pages link to each other. |

### 14.4 Acceptance criteria
- **AC-E1** (E2, E4): a description copied from a known ticket includes that ticket's assignee, with that ticket listed.
- **AC-E2** (E6): `ricetta per la torta di mele` recommends nobody.
- **AC-E3** (E2, E3): no response has more than 3 people or 5 tickets.
- **AC-E4** (E5): no recommended person is "Unassigned".

### 14.5 Test cases
Unit tests (`RecommendTests` in `chatbot/test_ticket_lookup.py`): limits and CSV facts; known ticket's assignee recommended; unassigned skipped; no match. Manual: AC-E1, AC-E2 in the browser at `/recommend`, and a link check on the three pages.

### 14.6 Risks
Lexical shortlist (cross-language misses); assignees may have left the team; frequent assignees can dominate.
