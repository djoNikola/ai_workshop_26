## Context

`ticket_lookup.py` already loads the CSV (including `ASSIGNEE`, with null shown as "Unassigned") and has a BM25 shortlist with scores. The server already serves `/` and `/categorize`.

## Goals / Non-Goals

**Goals:** recommend 2-3 people from similar assigned tickets, on a new URL, reusing the shortlist and the existing Copilot CLI call. Stay stdlib-only.

**Non-Goals:** workload or availability, changing existing endpoints.

## Decisions

1. **Separate URL.** `GET /recommend` serves the page; `POST /api/recommend` takes `{"prompt": ..., "lang": ...}` and returns `{"reply", "notes", "experts"}`. Same Host/Origin and Copilot-ready checks as the other pages.
2. **Tickets.** Take the BM25 shortlist (≤30) and drop unassigned tickets. Ticket IDs in the text are plain text.
3. **LLM ranking.** One Copilot call with the description and the assigned shortlist (`pkey`, `summary`, `description`, `assignee`). JSON reply: up to 3 `{assignee, pkeys, confidence, reason}`, best first, ≤5 tickets in total. Assignees outside the shortlist and pkeys not owned by that assignee are dropped; an expert with no valid ticket is dropped. Summaries come from the CSV. Rationale: the LLM judges which similar tickets really match and explains why, which BM25 term overlap cannot.
4. **Fallback.** LLM failure or invalid JSON: score per assignee = sum of BM25 scores of their tickets among the 5 most relevant assigned tickets; top 3, ties by name; relevance % = share of the total; notice "LLM ranking was unavailable".
5. **No match.** If no assigned ticket shares terms with the description, the LLM is not called and nobody is listed. An empty LLM list also lists nobody.

## Risks / Trade-offs

- Lexical shortlist: cross-language queries can miss (same as `ticket-lookup`).
- The description and assignee usernames of ≤30 tickets leave the machine (Copilot), as for the other pages.
- Confidence is the LLM's own estimate, not a computed score.
- The assignee of a closed ticket may have left the team; the app cannot know.
- Heavy assignees (the top assignee has ~15% of tickets) may dominate.
