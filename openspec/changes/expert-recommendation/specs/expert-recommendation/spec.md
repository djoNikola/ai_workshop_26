## ADDED Requirements

### Requirement: Recommendation page on its own URL
The system SHALL serve a page at `/recommend` and accept descriptions at `POST /api/recommend`, without changing existing endpoints, and with the same local-only Host/Origin checks.

#### Scenario: Open the page
- **WHEN** the PM opens `http://localhost:8765/recommend`
- **THEN** a form to describe a problem is shown

#### Scenario: Copilot not ready
- **WHEN** Copilot CLI is not installed or not logged in
- **THEN** `/api/recommend` answers 409, like the other endpoints

### Requirement: Recommend assignees of similar tickets
The system SHALL recommend 2-3 people (`ASSIGNEE`) for a free-text problem description in Italian, English or a mix, ranked by the LLM from the assigned tickets in the BM25 shortlist.

#### Scenario: Description close to past tickets
- **WHEN** the PM sends a description matching several assigned tickets
- **THEN** at most 3 people are returned in the LLM's order, with at most 5 evidence tickets in total

#### Scenario: Unassigned tickets ignored
- **WHEN** a highly relevant ticket has no assignee
- **THEN** it is not sent to the LLM and not shown

#### Scenario: LLM cannot invent people or tickets
- **WHEN** the LLM names a person or ticket not in the shortlist, or a ticket not assigned to that person
- **THEN** it is dropped

#### Scenario: LLM unavailable
- **WHEN** the LLM call fails or returns invalid JSON
- **THEN** people are ranked by the summed BM25 score of their tickets among the 5 most relevant assigned tickets, with the notice "LLM ranking was unavailable"

### Requirement: Evidence shown
The system SHALL show, for each recommended person, a relevance percentage, a reason and the similar tickets (ID and summary) they handled, taken from the export.

#### Scenario: Evidence equals the export
- **WHEN** tickets are displayed under a person
- **THEN** their ID and summary equal the export row, and the person equals the ticket's `ASSIGNEE`

### Requirement: No recommendation without a match
The system SHALL NOT recommend anyone when no assigned ticket shares terms with the description.

#### Scenario: Unrelated description
- **WHEN** the PM sends `ricetta per la torta di mele`
- **THEN** the response says no expert could be recommended and lists no people

### Requirement: Navigation links
The system SHALL link to `/recommend` from `/` and `/categorize`, and `/recommend` SHALL link back to both.

#### Scenario: Links present
- **WHEN** any of the three pages is open
- **THEN** it links to the other two
