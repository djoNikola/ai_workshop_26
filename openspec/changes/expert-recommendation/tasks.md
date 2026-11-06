## 1. Logic

- [x] 1.1 Add `recommend(query, index)` in `ticket_lookup.py`: top 5 assigned tickets, score per assignee, top 3, relevance share, no-match reply

## 2. Server and UI

- [x] 2.1 Add `GET /recommend` and `POST /api/recommend` (Host/Origin checks, no Copilot-ready check)
- [x] 2.2 Add `chatbot/sip-recommend.html`
- [x] 2.3 Add links to `/recommend` on `sip-chatbot.html` and `sip-categorize.html`

## 3. Tests

- [x] 3.1 Unit tests in `chatbot/test_ticket_lookup.py`: limits, CSV facts, known-ticket assignee, unassigned skipped, no match
- [ ] 3.2 Manual check in the browser at `/recommend`

## 4. Docs

- [x] 4.1 Add `SPEC.md` §14 and update `chatbot/README.md`
