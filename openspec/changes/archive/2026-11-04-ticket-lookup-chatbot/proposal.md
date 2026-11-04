# Proposal

## Why

The PM is the single contact for client status requests on SIP tickets. Clients often give a wrong ticket number or only a vague description, so the PM must scan the ticket CSV export by hand. This is slow and error-prone, and it gets worse as tickets grow. See `SPEC.md` and `resources/problem_brief.md`.

## What Changes

- Turn the existing local web chat (`chatbot/sip-chatbot-web.py`, `chatbot/sip-chatbot.html`) from a generic Copilot passthrough into a ticket lookup assistant.
- Load `resources/issues_export.csv` locally and expose only the ID, summary, description, status and assignee fields to matching.
- Detect a ticket ID in the PM's message and return that ticket first. If the ID does not exist, say so and continue with text search.
- For free-text queries (Italian or English), shortlist tickets locally, then have the LLM re-rank the shortlist and return up to 3 candidates with a match reason.
- Show ID, summary, status label and assignee for each candidate, taken from the CSV and never from LLM text.
- Show "no match" when nothing is relevant. If the LLM fails, fall back to the local shortlist.
- Each lookup is independent; the `--continue` conversation behaviour is removed.

## Capabilities

### New Capabilities
- `ticket-lookup`: finding candidate SIP tickets from an ID or a free-text description and presenting their ID, summary, status and assignee in a local web chat.

### Modified Capabilities

None. `openspec/specs/` is empty.

## Impact

- Code: `chatbot/sip-chatbot-web.py` (data loading, matching, `/api/chat` behaviour), `chatbot/sip-chatbot.html` (candidate rendering), `chatbot/README.md`.
- Data: `resources/issues_export.csv` read-only (3,816 rows).
- External: Copilot CLI for LLM re-ranking. **Open risk:** this sends the query and about 30 ticket snippets from a real export off the machine, which conflicts with the brief's "no data leaves local" constraint. See design.md.
- Dependencies: Python 3 standard library only if practical.
