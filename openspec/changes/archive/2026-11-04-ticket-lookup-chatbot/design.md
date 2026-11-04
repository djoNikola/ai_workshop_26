# Design

## Context

`chatbot/sip-chatbot-web.py` is a st
dlib `ThreadingHTTPServer`. Its `/api/chat` forwards the raw prompt to `copilot -p`, with `--continue` after the first message. It also handles Copilot install and login. `sip-chatbot.html` renders replies as plain text. `resources/issues_export.csv` has 3,816 rows, with opaque numeric `ISSUESTATUS`, and descriptions in Italian with some `[NULL]` values. See proposal.md for motivation and `SPEC.md` for the full analysis.

## Goals / Non-Goals

**Goals:**
- Reuse the existing server, status/install/login handling and UI shell.
- Keep factual fields deterministic by sourcing them from the CSV.
- Keep the matching code testable without calling the LLM.

**Non-Goals:**
- Persistent index, database or vector store.
- Authentication or multi-user support.
- Conversation memory.
- Query translation or expansion.

## Decisions

1. **Hybrid matching: local shortlist, then LLM re-rank.** The CSV is too big for one prompt. Keyword scoring (BM25-style, stdlib) keeps the top 30. The LLM picks up to 3 and returns JSON `{"results":[{"pkey","reason"}]}`. *Alternatives:* LLM-only over the full CSV (too large, slow); keyword-only (poor for vague text, but kept as the fallback).
2. **Facts come from the CSV.** The server maps LLM-returned `pkey`s back to loaded rows and drops unknown IDs. This prevents hallucinated status or assignee.
3. **ID shortcut before the LLM.** A regex for `[A-Z]+-\d+` finds IDs. Existing IDs skip ranking for that ticket; a missing ID adds a "not found" note and the remainder goes through the normal search.
4. **Keep Copilot CLI as the LLM.** It already works with the existing install/login flow. The call sits behind one function so that a local model can replace it. Each lookup runs without `--continue` and with the JSON-only instruction.
5. **Status labels via a config dict.** `STATUS_LABELS` in the server, since the export has no decode table. Unknown codes show `Status <code>`.
6. **Structured reply.** `/api/chat` keeps `{"reply": ...}` and adds an optional `candidates` array. The HTML renders candidates as cards and falls back to the text reply. *Alternative:* text only (simpler, but harder to read).
7. **Data minimisation.** Load only `PKEY, SUMMARY, DESCRIPTION, ISSUESTATUS, ASSIGNEE`. Descriptions are trimmed to about 500 characters. Nothing is logged to disk.

## Risks / Trade-offs

- **[Privacy: real export goes to Copilot]** → The brief says no client data leaves local. Resolve at the mentor scope gate: get approval, anonymise the CSV, or swap in a local model (Decision 4 keeps this cheap). Until resolved, treat this as blocking for any real use.
- **[Italian/English recall]** An English query may miss Italian tickets in the keyword shortlist → larger shortlist; query expansion is out of scope.
- **[Latency]** Each Copilot CLI call takes ~10 s or more → acceptable for a PoC; the UI shows a pending state.
- **[Unconfirmed status labels]** The PM must confirm what codes 6, 10008, 1, 10001 and 10002 mean → fallback label, easy to change.
- **[LLM output malformed]** → strict JSON parsing, then the degraded-mode fallback.
