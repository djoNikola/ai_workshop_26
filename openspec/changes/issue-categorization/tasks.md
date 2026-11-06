## 1. Data

- [x] 1.1 Load `ISSUETYPE` in `TicketIndex.from_csv`; add `ISSUETYPE_LABELS` and `issuetype_label()` (unknown → `Type <code>`)

## 2. Categorization logic

- [x] 2.1 Add local scoring: shortlist with BM25 scores, sum per `ISSUETYPE`, confidence share, alternatives, examples
- [x] 2.2 Add categorization prompt (allowed fields only) and lenient JSON parsing; drop categories not in the shortlist
- [x] 2.3 Add `categorize(query, index, llm)` with empty-shortlist "no suggestion" and LLM-failure fallback notice

## 3. Server and UI

- [x] 3.1 Add `GET /categorize` and `POST /api/categorize` with existing Host/Origin and Copilot-ready checks
- [x] 3.2 Add `chatbot/sip-categorize.html` page with form and result rendering

## 4. Tests

- [x] 4.1 Unit tests in `chatbot/test_ticket_lookup.py`: scoring, label map, JSON parsing (valid, invalid, foreign category), no-match, fallback, result limits
- [ ] 4.2 Manual check of the demo queries in `SPEC.md` §13 against the real CSV

## 5. Docs

- [x] 5.1 Update `chatbot/README.md` with the new URL
- [ ] 5.2 Ask the PM to confirm `ISSUETYPE_LABELS`

