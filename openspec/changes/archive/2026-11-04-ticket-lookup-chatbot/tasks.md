# Tasks

## 1. Ticket data and search core

- [x] 1.1 Add a module that loads `resources/issues_export.csv` (needed fields only, `[NULL]` handled, descriptions trimmed) with a unit test checking 3,816 rows load without error
- [x] 1.2 Add a `STATUS_LABELS` map and a formatter for status and assignee, with unit tests for known code, unknown code (`Status <code>`) and empty assignee ("Unassigned")
- [x] 1.3 Implement ticket-ID extraction and exact lookup, with unit tests for `BTU-4114`, text without an ID, and a non-existent ID
- [x] 1.4 Implement the local keyword shortlist (top 30), with a unit test that the shortlist for the AC3 query contains BTU-4115

## 2. LLM re-rank and lookup flow

- [x] 2.1 Build the re-rank prompt (query plus shortlist, allowed fields only, JSON-only instruction) and a parser that drops IDs not in the shortlist, with unit tests for valid, invalid and unknown-ID output using a mocked LLM
- [x] 2.2 Implement the lookup flow: ID shortcut, "ID not found" note plus text search, "no match" response, degraded mode with notice on LLM failure; verify with mocked-LLM tests for each branch and the max-3 limit
- [x] 2.3 Replace `run_copilot` passthrough in `/api/chat` with the lookup flow, with no `--continue`; verify with a request test that the reply and optional `candidates` array match the CSV rows and that foreign Host/Origin is still rejected

## 3. UI and docs

- [x] 3.1 Update `chatbot/sip-chatbot.html` to render candidates (ID, summary, status, assignee, reason) and the notice/no-match messages; verify the script syntax and the API payload it renders (visual browser check still pending)
- [x] 3.2 Update `chatbot/README.md` for the new behavior, data source and the privacy note, and verify the documented start command works as written

## 4. Integration

- [x] 4.1 Run the demo scenario live (BTU-4114; wrong ID plus description; vague Italian description; unrelated query; English query) and verify AC1–AC5 from `SPEC.md`
- [x] 4.2 Force the LLM call to fail and verify the degraded-mode result (AC7)
- [x] 4.3 Record the decision on the privacy risk (approve, anonymise or local model) in `SPEC.md` §10 and confirm the status labels with the PM

## Workflow follow-up

- Archive the change after the mentor review and scope gate.
