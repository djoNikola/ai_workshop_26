## Why

When a problem comes in, the PM wants to know who can solve it. In `resources/issues_export.csv` the `ASSIGNEE` of a ticket is the person who handled it, so the assignees of similar past tickets are the best candidates.

## What Changes

- Add a page at `/recommend` and `POST /api/recommend` in the existing local server. The PM describes a problem and gets 2-3 recommended people.
- The recommendation uses the 5 most relevant assigned tickets from the existing BM25 shortlist; assignees are ranked by the summed score of their tickets.
- Each recommended person is shown with the similar tickets they handled.
- Links to the new page are added on `/` and `/categorize`, and the new page links back to both.

## Capabilities

### New Capabilities
- `expert-recommendation`: recommend assignees for a free-text problem description from similar tickets in the export.

### Modified Capabilities
- `ticket-lookup`, `issue-categorization`: no requirement changes; only a navigation link is added to their pages.

## Impact

- `chatbot/ticket_lookup.py`: `recommend()`.
- `chatbot/sip-chatbot-web.py`: route `/recommend`, endpoint `/api/recommend` (same Host/Origin checks; no Copilot needed).
- New `chatbot/sip-recommend.html`; link added to `sip-chatbot.html` and `sip-categorize.html`.
- `SPEC.md` §14, `chatbot/README.md`.
- Data boundary: purely local, nothing is sent to an LLM.
- Out of scope: availability or workload of people, contacting them, LLM re-ranking.
