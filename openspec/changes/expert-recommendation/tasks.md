## 1. Logic

- [x] 1.1 Add `recommend_local(query, index)` in `ticket_lookup.py`: top 5 assigned tickets, score per assignee, top 3, relevance share, no-match reply
- [x] 1.2 Add LLM ranking `recommend(query, index, llm, lang)`: prompt with the assigned shortlist, JSON parsing that drops unknown people/tickets, ≤5 evidence tickets, fallback to `recommend_local` with notice

## 2. Server and UI

- [x] 2.1 Add `GET /recommend` and `POST /api/recommend` (Host/Origin and Copilot-ready checks; passes `run_copilot` and `lang`)
- [x] 2.2 Add `chatbot/sip-recommend.html` (shows the LLM reason per person)
- [x] 2.3 Add links to `/recommend` on `sip-chatbot.html` and `sip-categorize.html`

## 3. Tests

- [x] 3.1 Unit tests in `chatbot/test_ticket_lookup.py`: local vote, LLM ranking, invented people/tickets dropped, evidence limit, unassigned not sent, no match skips LLM, fallback
- [ ] 3.2 Manual check in the browser at `/recommend`

## 4. Docs

- [x] 4.1 Add `SPEC.md` §14 and update `chatbot/README.md`
