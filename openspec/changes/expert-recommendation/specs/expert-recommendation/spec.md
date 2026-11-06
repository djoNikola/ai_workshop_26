## ADDED Requirements

### Requirement: Recommendation page on its own URL
The system SHALL serve a page at `/recommend` and accept descriptions at `POST /api/recommend`, without changing existing endpoints, and with the same local-only Host/Origin checks.

#### Scenario: Open the page
- **WHEN** the PM opens `http://localhost:8765/recommend`
- **THEN** a form to describe a problem is shown

#### Scenario: Copilot not needed
- **WHEN** Copilot CLI is not installed or not logged in
- **THEN** `/api/recommend` still answers

### Requirement: Recommend assignees of similar tickets
The system SHALL recommend 2-3 people (`ASSIGNEE`) for a free-text problem description in Italian, English or a mix, based on the 5 most relevant assigned tickets in the export.

#### Scenario: Description close to past tickets
- **WHEN** the PM sends a description matching several assigned tickets
- **THEN** at most 3 people are returned, ranked by the summed relevance of their tickets among the 5 most relevant tickets

#### Scenario: Unassigned tickets ignored
- **WHEN** a highly relevant ticket has no assignee
- **THEN** it is not used, and the next relevant assigned ticket is used instead

### Requirement: Evidence shown
The system SHALL show, for each recommended person, a relevance percentage and the similar tickets (ID and summary) they handled, taken from the export.

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
