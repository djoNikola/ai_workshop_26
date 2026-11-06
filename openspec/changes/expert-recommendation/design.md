## Context

`ticket_lookup.py` already loads the CSV (including `ASSIGNEE`, with null shown as "Unassigned") and has a BM25 shortlist with scores. The server already serves `/` and `/categorize`.

## Goals / Non-Goals

**Goals:** recommend 2-3 people from the 4-5 most relevant tickets, on a new URL, reusing the shortlist. Stay local and stdlib-only.

**Non-Goals:** LLM use, workload or availability, changing existing endpoints.

## Decisions

1. **Separate URL.** `GET /recommend` serves the page; `POST /api/recommend` takes `{"prompt": ...}` and returns `{"reply", "experts", "tickets"}`. Same Host/Origin checks.
2. **Tickets.** Take the BM25 shortlist, drop unassigned tickets, keep the top 5 (`RECOMMEND_TICKETS`). Ticket IDs in the text are plain text.
3. **People.** Score per assignee = sum of BM25 scores of their tickets among those 5. Return the top 3 (`RECOMMEND_EXPERTS`), ties broken by name. Relevance % = share of the total score of the 5 tickets. If fewer people exist, fewer are returned.
4. **Local only.** No Copilot call, so the page works even when Copilot is not installed or logged in, and no data leaves the machine. Alternative (LLM re-rank) rejected: ASSIGNEE is ground truth in the CSV, and the extra call adds latency and privacy risk.
5. **No match.** If no assigned ticket shares terms with the description, answer "No expert could be recommended" and list nobody.

## Risks / Trade-offs

- Lexical shortlist: cross-language queries can miss (same as `ticket-lookup`).
- The assignee of a closed ticket may have left the team; the app cannot know.
- Heavy assignees (the top assignee has ~15% of tickets) may dominate.
