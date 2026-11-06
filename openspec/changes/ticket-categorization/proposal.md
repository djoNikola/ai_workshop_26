## Why

The PM (and anyone raising a ticket) often knows the problem but not which ticket category (`ISSUETYPE`) to file it under. Today the chatbot finds existing tickets but does not help choose the category for a new one. Past tickets in the export already carry an `ISSUETYPE`, so they can show which category similar problems were filed under.

## What Changes

- Add a new page at `/categorize` where the user describes a problem in free text (Italian, English or mixed).
- Add `POST /api/categorize`, which searches the same ticket export (`resources/issues_export.csv`) and returns the recommended `ISSUETYPE` for a new ticket, up to 2 alternatives, a short reason, and up to 3 similar past tickets as evidence.
- Reuse the existing hybrid approach: local BM25 shortlist, then LLM decision, with a local fallback (score-weighted vote on the shortlist) when the LLM fails.
- Add an `ISSUETYPE` label map (codes have no decode table in the export); unknown codes display as `Type <code>`.
- Add a link between the existing chat page and the new page, and EN/IT texts and light/dark theme support for the new page.
- Update `SPEC.md` with the new feature (§13) and the new requirements and acceptance criteria.

No changes to the existing `ticket-lookup` behavior or to `/api/chat`.

## Capabilities

### New Capabilities
- `ticket-categorization`: classify a free-text problem description into an `ISSUETYPE` category using the existing ticket export, on its own URL.

### Modified Capabilities
<!-- None: ticket-lookup requirements are unchanged. -->

## Impact

- `chatbot/sip-chatbot-web.py`: new routes `GET /categorize`, `POST /api/categorize`; new static files whitelisted.
- `chatbot/ticket_lookup.py` (or a sibling module): `ISSUETYPE` loaded in the index, new categorize flow.
- `chatbot/` front end: new page, script and shared styles.
- `chatbot/README.md`, `SPEC.md`.
- Data privacy: same open risk as the lookup feature (query and ≤30 ticket snippets go to Copilot). One extra field, `ISSUETYPE`, is sent. No new export columns beyond it.
