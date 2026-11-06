## ADDED Requirements

### Requirement: Categorization page on its own URL
The system SHALL serve a categorization page at `/categorize` and accept descriptions at `POST /api/categorize`, without changing `/` or `/api/chat`.

#### Scenario: Open the page
- **WHEN** the PM opens `http://localhost:8765/categorize`
- **THEN** a form to describe a problem is shown

#### Scenario: Existing chat unchanged
- **WHEN** the PM uses `/` and `/api/chat`
- **THEN** the behaviour is as defined in `ticket-lookup`

### Requirement: Category suggestion from similar tickets
The system SHALL suggest one `ISSUETYPE` category for a free-text problem description in Italian, English or a mix, based on similar tickets in the same export used by `ticket-lookup`.

#### Scenario: Description close to past tickets
- **WHEN** the PM sends a description that matches several tickets of one `ISSUETYPE`
- **THEN** the response suggests that category

#### Scenario: Ticket ID in the description
- **WHEN** the description contains a ticket ID
- **THEN** the ID is not looked up and the text is categorized like any other

### Requirement: Category details in the response
The system SHALL show the suggested category as a readable label, a short reason, a confidence percentage, up to 2 alternative categories and up to 3 example tickets of the suggested category.

#### Scenario: Examples come from the export
- **WHEN** example tickets are displayed
- **THEN** their ID and summary equal the values in the export row, and their `ISSUETYPE` equals the suggested category

#### Scenario: Unknown category code
- **WHEN** a category code has no configured label
- **THEN** it is shown as "Type <code>"

#### Scenario: Result limits
- **WHEN** many categories and tickets are relevant
- **THEN** the response has one suggestion, at most 2 alternatives and at most 3 examples

### Requirement: LLM chooses only among supported categories
The system SHALL let the LLM choose only among categories that appear in the local shortlist, and SHALL ignore any other category the LLM returns.

#### Scenario: LLM returns a category outside the shortlist
- **WHEN** the LLM returns a category not present in the shortlist
- **THEN** the locally scored top category is used instead

### Requirement: Degraded mode without LLM
The system SHALL return the locally scored top category with a notice that LLM ranking was unavailable when the LLM call fails or returns unusable output.

#### Scenario: LLM call fails
- **WHEN** the LLM call fails or returns invalid output
- **THEN** the response suggests the category with the highest local score
- **AND** it includes a notice that LLM ranking was unavailable

### Requirement: No suggestion when nothing is similar
The system SHALL say that no category could be suggested, and SHALL NOT guess, when no ticket shares terms with the description or the LLM reports that none of the shortlisted tickets is relevant.

#### Scenario: Unrelated description
- **WHEN** the PM sends "ricetta per la torta di mele"
- **THEN** the response says no category could be suggested

#### Scenario: No shared terms
- **WHEN** no ticket shares a term with the description
- **THEN** the response says no category could be suggested
- **AND** the LLM is not called

### Requirement: Limited data exposure
The system SHALL send to the LLM only the description and, for at most 30 shortlisted tickets, their ID, summary, trimmed description and `ISSUETYPE`.

#### Scenario: Prompt content
- **WHEN** the system builds the categorization prompt
- **THEN** it contains only the allowed fields and at most 30 tickets

### Requirement: Local-only service
The categorization routes SHALL listen only on the loopback address and reject a foreign Host or Origin, like the existing routes.

#### Scenario: Foreign origin
- **WHEN** a request to `/categorize` or `/api/categorize` has a non-local Host or Origin
- **THEN** the system rejects it
