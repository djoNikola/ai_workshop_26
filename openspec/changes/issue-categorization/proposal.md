## Why

When a client reports a problem, the PM must create a new ticket and pick its category (`ISSUETYPE`). Today the chatbot only finds existing tickets. The PM needs help choosing the right category for a new ticket from a free-text description.

## What Changes

- Add a new page at `/categorize` in the existing local web server. The PM describes a problem and gets the suggested ticket category.
- Add `POST /api/categorize`. It reuses the loaded CSV export and the local BM25 shortlist, then derives the category from the `ISSUETYPE` of similar past tickets.
- The LLM may choose among the categories seen in the shortlist. If it fails, a local weighted vote gives the answer.
- The reply shows the suggested category, up to 2 alternatives, and up to 3 example tickets that support the suggestion.
- The existing `/` chat and `/api/chat` are unchanged.

## Capabilities

### New Capabilities
- `issue-categorization`: suggest the `ISSUETYPE` category for a new ticket from a free-text problem description, using similar tickets in the export.

### Modified Capabilities
- `ticket-lookup`: no requirement changes. It shares the CSV loader, shortlist and local-only service rules.

## Impact

- `chatbot/ticket_lookup.py`: load `ISSUETYPE`; add category suggestion logic.
- `chatbot/sip-chatbot-web.py`: new route `/categorize` and endpoint `/api/categorize`, same Host/Origin checks.
- New HTML page for the categorization form.
- `SPEC.md`: new section for this feature.
- Data boundary: the LLM prompt may additionally contain `ISSUETYPE` of shortlisted tickets.
- Out of scope: creating tickets, changing the existing chat, multi-label output, training a model.
