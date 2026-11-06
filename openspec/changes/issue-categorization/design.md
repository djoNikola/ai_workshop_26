## Context

`resources/issues_export.csv` (3,816 rows) has an `ISSUETYPE` column with numeric codes and no decode table. Observed codes and counts: 10 (2364), 9 (690), 11 (405), 18 (115), 19 (99), 17 (70), 16/13/12/20 (16 each), 15 (9). `ticket_lookup.py` already loads the CSV and has a BM25 shortlist; `sip-chatbot-web.py` already serves the chat and calls Copilot CLI.

## Goals / Non-Goals

**Goals:** suggest one category for a new ticket on a separate URL, reusing existing data, shortlist and LLM call. Stay local and stdlib-only.

**Non-Goals:** creating tickets, changing `/api/chat`, multi-label output, fixing class imbalance.

## Decisions

1. **Separate URL.** `GET /categorize` serves a new page; `POST /api/categorize` takes `{"prompt": ...}` and returns `{"reply", "category", "alternatives", "examples"}`. Same Host/Origin checks as the existing routes. Alternative (a mode toggle on `/`) rejected: the user asked for a new URL and the output shape differs.
2. **Local vote first, LLM second.** Shortlist the top 30 tickets with the existing BM25 (the ticket-ID shortcut is not used). Score per `ISSUETYPE` = sum of BM25 scores of shortlisted tickets with that type. The top-scoring type is the local suggestion. Reason: it is deterministic and works without the LLM.
3. **LLM picks among shortlist categories only.** The prompt has the description and the shortlist (`pkey`, `summary`, `description`, `issuetype`). The LLM replies JSON-only: `{"category":"<code or null>","reason":"..."}`; `null` means nothing is relevant and yields "no category could be suggested". A code not present in the shortlist is dropped and the local vote is used. Alternative (LLM free choice among all categories) rejected: it could return a category with no supporting tickets.
4. **Category labels.** Config dict `ISSUETYPE_LABELS = {...}` in `ticket_lookup.py`. Unknown codes display as `Type <code>`. Real labels must be confirmed by the PM (open item), as for `STATUS_LABELS`.
5. **Confidence.** The reply includes the share of the suggested type in the total score (a number 0–100%). If the shortlist is empty, the answer is "no category suggestion" and the LLM is not called.
6. **Examples.** Up to 3 top-scoring shortlisted tickets of the suggested type are shown (`pkey`, `summary`, from the CSV, not from LLM text).
7. **Alternatives.** Up to 2 other types ordered by local score, only if their score is above zero.

## Risks / Trade-offs

- Lexical shortlist: cross-language queries can miss (same limitation as `ticket-lookup`). Mitigation: low confidence shown.
- Class imbalance: type 10 is 62% of rows, so the vote leans to it. Mitigation: show alternatives and confidence; no re-weighting in the first slice.
- Labels unknown until the PM confirms them.
- Privacy: same open risk as `SPEC.md` §10; only the description and ≤30 ticket snippets with `ISSUETYPE` are sent to the LLM.
