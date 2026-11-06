# Tasks

## 1. Data and core

- [x] 1.1 Load `ISSUETYPE` into the ticket index (`[NULL]` becomes empty), with a unit test that all 3,816 rows still load
- [x] 1.2 Add an `ISSUETYPE_LABELS` map and a formatter (label plus code; unknown code shows `Type <code>`), with unit tests for known, unknown and empty codes
- [x] 1.3 Return BM25 scores with the shortlist without changing the current lookup result, with a test that lookup tests still pass
- [x] 1.4 Implement the local vote: total shortlist score per `ISSUETYPE`, ranked best first, with a unit test on a small fixture

## 2. LLM decision and flow

- [x] 2.1 Build the categorization prompt (description plus ≤30 tickets with only ID, summary, trimmed description, `ISSUETYPE`) and a parser that drops codes not in the shortlist, with tests for valid, invalid and unknown-code output using a mocked LLM
- [x] 2.2 Implement the categorize flow: empty shortlist gives "no category" without an LLM call; LLM failure gives the local vote with notice; result has recommended, ≤2 alternatives, support counts, ≤3 example tickets; verify each branch with mocked-LLM tests
- [x] 2.3 Add `MESSAGES` for categorization notes in EN and IT, with a test for `lang="it"` and an unknown `lang`

## 3. Server and UI

- [x] 3.1 Add `GET /categorize` and `POST /api/categorize` (same Host/Origin checks, `not_ready` 409, `lang` fallback, 400 on empty prompt), with a request test including a foreign Host/Origin
- [x] 3.2 Add the new page and script to `STATIC_FILES` and the page assets; reuse `style.css`, `theme.js` and EN/IT texts; link both pages to each other; confirm other `/static` paths still return 404
- [x] 3.3 Render the recommendation, alternatives, support counts, example tickets, notices and no-match message on the page; verify the payload rendering (visual browser check)

## 4. Docs and verification

- [x] 4.1 Update `chatbot/README.md` with the new URL, endpoint and privacy note
- [ ] 4.2 Run AC9–AC13 from `SPEC.md` §13 against the real CSV and adjust the examples, not the criteria, if rankings differ
- [ ] 4.3 Confirm the real `ISSUETYPE` names with the PM and fill `ISSUETYPE_LABELS`
