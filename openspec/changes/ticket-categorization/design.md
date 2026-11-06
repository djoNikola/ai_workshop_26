## Context

The ticket-lookup chatbot loads `resources/issues_export.csv` (3,816 rows) into a BM25 index and re-ranks a 30-ticket shortlist with one `copilot -p` call. The export has an `ISSUETYPE` column, numeric with no decode table. Observed distribution: 10 (2,364), 9 (690), 11 (405), 18 (115), 19 (99), 17 (70), 16/13/12/20 (16 each), 15 (9).

The user asked for a feature on a new URL: describe a problem, and the app says which category (`ISSUETYPE`) to create the ticket in, using the same export.

## Goals / Non-Goals

**Goals**
- A `/categorize` page and `POST /api/categorize` endpoint that recommend an `ISSUETYPE`.
- Reuse the existing index, shortlist, LLM runner, language handling, security checks and static-file whitelist.
- Works without the LLM (degraded mode).

**Non-Goals**
- Creating or updating tickets.
- Predicting other fields (priority, assignee, component).
- Training a model or adding dependencies.
- Changing `/api/chat` or the lookup page behavior.

## Decisions

**1. Evidence-based categorization over the existing shortlist.**
Reuse the BM25 shortlist (top 30) as similar past tickets, now carrying `ISSUETYPE`. The LLM is given the description and the shortlist and picks the category. Alternative considered: ask the LLM with no tickets. Rejected, because the codes are opaque numbers and only the tickets show what each code means in practice.

**2. LLM output is constrained to codes present in the shortlist.**
The LLM replies JSON only: `{"categories":[{"issuetype":"10","reason":"..."}]}`, at most 3 items, best first. Codes not present in the shortlist are dropped, same as unknown pkeys in lookup. The server adds the label and the supporting tickets itself, not the LLM.

**3. Local fallback is a score-weighted vote.**
Without a usable LLM reply, sum the BM25 scores of the shortlist tickets per `ISSUETYPE` and rank categories by total. This needs the BM25 scores, so `shortlist` is extended (or a sibling method added) to also return scores, with the current return value unchanged for lookup. A notice says LLM ranking was unavailable.

**4. No-match rule is shared with lookup.**
An empty shortlist (no shared token) means "no category suggestion"; the LLM is not called. The LLM may also return an empty list.

**5. Label map as config.**
`ISSUETYPE_LABELS = {...}` in code, like `STATUS_LABELS`. The export has no decode table, so the shipped map is empty or provisional, and unknown codes display `Type <code>`. The PM must confirm real names (open item). Labels never come from the LLM.

**6. Routes and UI.**
`GET /categorize` serves a new HTML page; `POST /api/categorize` takes `{"prompt": ..., "lang": "en"|"it"}` and returns `{"reply", "category", "alternatives", "examples"}` (plus `error` on failure). Both go through the existing Host/Origin checks and the Copilot readiness check (`not_ready`, 409). New static files are added to `STATIC_FILES`; the page reuses `style.css`, `theme.js` and the EN/IT mechanism. The two pages link to each other.

**7. Evidence cards.**
Up to 3 examples are shown: the highest-scoring shortlist tickets whose `ISSUETYPE` equals the recommended one. They are displayed with ID, summary and status, from the CSV.

**8. Ticket-ID tokens are not special here.**
The input is a problem description for a new ticket. An ID in the text is treated as ordinary text, with no ID shortcut.

## Risks / Trade-offs

- **Opaque codes**: without labels the page shows `Type 10`. Mitigation: label map, confirmed by the PM.
- **Class imbalance**: code 10 is 62% of tickets, so a vote leans towards it. Mitigation: the LLM decides in the normal path; the fallback shows alternatives so the user can see others.
- **Lexical shortlist**: cross-language queries can miss (same limitation as lookup).
- **Privacy**: the same risk as lookup (SPEC §10.1). Only `ISSUETYPE` is added to the fields sent.
- **Single-ticket evidence**: a category backed by one ticket is weak. The response shows how many shortlist tickets support each category.

## Open Questions

- Real names for `ISSUETYPE` codes 9–20.
- Should the recommendation include a confidence indicator? Not in this slice; the supporting-ticket count stands in for it.
