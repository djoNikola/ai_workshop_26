## Why

When a problem comes in, the PM wants to know who can solve it. In `resources/issues_export.csv` the `ASSIGNEE` of a ticket is the person who handled it, so the assignees of similar past tickets are the best candidates.

## What Changes

- Add a page at `/recommend` and `POST /api/recommend` in the existing local server. The PM describes a problem and gets 2-3 recommended people.
- The BM25 shortlist (unassigned tickets dropped) is sent to Copilot, which ranks up to 3 assignees with a confidence, a reason and the supporting tickets. People and tickets outside the shortlist are dropped. If Copilot fails, assignees are ranked locally by the summed BM25 score of their tickets among the 5 most relevant assigned tickets.
- Each recommended person is shown with the similar tickets they handled.
- Links to the new page are added on `/` and `/categorize`, and the new page links back to both.

## Capabilities

### New Capabilities
- `expert-recommendation`: recommend assignees for a free-text problem description from similar tickets in the export.

### Modified Capabilities
- `ticket-lookup`, `issue-categorization`: no requirement changes; only a navigation link is added to their pages.

## Impact

- `chatbot/ticket_lookup.py`: `recommend()` (LLM ranking), `recommend_local()` (fallback).
- `chatbot/sip-chatbot-web.py`: route `/recommend`, endpoint `/api/recommend` (same Host/Origin and Copilot-ready checks).
- New `chatbot/sip-recommend.html`; link added to `sip-chatbot.html` and `sip-categorize.html`.
- `SPEC.md` §14, `chatbot/README.md`.
- Data boundary: the description and ≤30 assigned ticket snippets (`pkey`, `summary`, trimmed description, `ASSIGNEE`) are sent to Copilot.
- Out of scope: availability or workload of people, contacting them.
