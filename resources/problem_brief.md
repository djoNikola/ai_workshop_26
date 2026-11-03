# Problem Brief — Ticket Lookup Chatbot for Client Status Requests

## Problem

The Project Manager (PM) is the single point of contact for client status
requests on SIP tickets (bugs, tasks, requests). When a client asks "what's
the status of my issue," the client often gives incomplete or incorrect
information — a wrong ticket number, or no number at all, just a description
of the problem. The PM must then manually search the ticket export to find
the right ticket, reading through summaries and descriptions by hand. This is
slow, error-prone, and does not scale as the number of tickets grows.

- **User**: Project Manager (client-facing, single point of contact)
- **Current process**: client reports an issue informally -> PM manually
  searches the ticket export (CSV) for a matching ticket by scanning
  summaries/descriptions
- **Pain point**: manual search is time-consuming and unreliable when the
  client's information is vague, partial, or wrong (incorrect ticket number,
  fuzzy description)
- **Intended improvement**: a chatbot that takes a free-text description from
  the PM (relayed from the client), searches the ticket data, and returns one
  or more candidate tickets with: task ID, a quick summary, its status, and
  the assigned person — removing the need for manual searching

## Expected Benefit

- Reduces time PM spends manually searching tickets per client request
- Reduces chance of PM reporting the wrong ticket status back to a client
- Lets PM handle ambiguous/incomplete client reports confidently, without
  needing an exact ticket number up front

## Constraints

- Phase I is a PoC: ticket data and any lookup data are **mocked/generated
  files**, not a live connection to the real ticketing system
- Single-user tool (PM only), local file-based, no multi-user or server
  component in scope
- No client or patient data leaves the local environment (data stays in
  local files processed locally)

## Assumptions

- A single mock ticket file (CSV, shaped like `resources/issues_export.csv`)
  is sufficient to represent the ticket population for the PoC
- Ticket descriptions in the mock data are in free text good enough for
  similarity/semantic matching against a client's informal description
- Status and assignee fields in the mock data are human-readable (the real
  export's `ISSUESTATUS`/`ISSUETYPE` are opaque numeric codes with no
  decode table included — the mock data will use readable values instead,
  e.g. "In Progress", "Closed", assignee name)
- A client description may match zero, one, or multiple tickets; returning
  "best candidates" (not necessarily a single exact match) is acceptable
- The previously proposed "focal point person per environment" mock file is
  **out of scope** — not needed, since the ticket's own assignee field
  already answers "who is working on this"

## Dependencies

- Mock ticket data file (generated for PoC, modeled on
  `resources/issues_export.csv` fields: ticket ID, summary, description,
  status, assignee)
- A matching/search approach to go from free-text description to candidate
  ticket(s) — exact mechanism (keyword search vs. embedding/semantic search
  vs. LLM-based matching) is **not yet decided** and belongs in SPEC.md
- Chatbot interface for the PM to type a description and receive results —
  interface choice (CLI, simple UI, etc.) not yet decided

## Data Involved

Reference shape from `resources/issues_export.csv` (real export, for
structure reference only — PoC will use a generated mock file):

| Field        | Used for                                   |
|--------------|---------------------------------------------|
| PKEY / ID    | Task ID returned to PM                      |
| SUMMARY      | Short text, candidate for matching + display|
| DESCRIPTION  | Longer text, candidate for matching         |
| ISSUESTATUS  | Task status returned to PM                  |
| ASSIGNEE     | Assigned person returned to PM              |

No client/patient-identifying data is used; mock data will use synthetic
summaries/descriptions modeled after the real export's style.
