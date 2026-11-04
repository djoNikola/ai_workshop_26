# Spec Delta

## Purpose

Lets the Project Manager find SIP tickets from a ticket ID or a vague client description, so client status requests can be answered without manually scanning the ticket export.

## ADDED Requirements

### Requirement: Free-text ticket search
The system SHALL accept a free-text query in Italian, English or a mix, in a local web chat, and return at most 3 candidate tickets ranked best first.

#### Scenario: Vague Italian description
- **WHEN** the PM sends "il cliente vuole filtrare i campioni consegnati e da consegnare"
- **THEN** the response lists at most 3 candidates
- **AND** BTU-4115 is among them

#### Scenario: English description against Italian tickets
- **WHEN** the PM sends "deliver sample management Cardarelli Napoli"
- **THEN** BTU-4113 is among the returned candidates

#### Scenario: More matches than the limit
- **WHEN** more than 3 tickets are relevant to the query
- **THEN** the response contains no more than 3 candidates

### Requirement: Candidate details
The system SHALL show for each candidate its task ID, summary, readable status, assignee and a one-line match reason.

#### Scenario: Candidate fields come from the export
- **WHEN** a candidate is displayed
- **THEN** its ID, summary, status and assignee equal the values in the ticket export row for that ID

#### Scenario: Unassigned ticket
- **WHEN** a displayed ticket has no assignee
- **THEN** the assignee is shown as "Unassigned"

#### Scenario: Unknown status code
- **WHEN** a ticket's status code has no configured label
- **THEN** the status is shown as "Status <code>"

### Requirement: Ticket ID lookup
The system SHALL recognise a ticket ID in the PM's message and, when that ticket exists, list it first.

#### Scenario: Existing ID
- **WHEN** the PM sends "BTU-4114"
- **THEN** BTU-4114 is the first result with its summary, status and assignee

### Requirement: Fallback for non-existent ticket ID
The system SHALL report that a given ticket ID does not exist and still search on the rest of the message.

#### Scenario: Wrong ID with description
- **WHEN** the PM sends "BTU-99999 servizio per pannellini e stampanti preanalitica"
- **THEN** the response states that BTU-99999 was not found
- **AND** BTU-4114 is among the candidates

### Requirement: No-match response
The system SHALL say that no matching ticket was found, and SHALL NOT return unrelated tickets, when no ticket is relevant to the query.

#### Scenario: Unrelated query
- **WHEN** the PM sends "ricetta per la torta di mele"
- **THEN** the response says no matching ticket was found
- **AND** no candidates are listed

### Requirement: Degraded mode without LLM ranking
The system SHALL return the top 3 locally scored tickets with a notice that LLM ranking was unavailable when the LLM call fails or returns unusable output.

#### Scenario: LLM call fails
- **WHEN** the LLM call fails or returns invalid output
- **THEN** the response lists up to 3 candidates from the local shortlist
- **AND** it includes a notice that LLM ranking was unavailable

#### Scenario: LLM names an unknown ticket
- **WHEN** the LLM returns an ID that is not in the shortlist
- **THEN** that ID is not shown to the PM

### Requirement: Independent lookups
The system SHALL treat each query as an independent lookup that does not depend on earlier messages.

#### Scenario: Second query after the first
- **WHEN** the PM sends a second query after an earlier one
- **THEN** the results depend only on the second query

### Requirement: Limited data exposure
The system SHALL expose to the LLM only the query and, for a bounded shortlist of tickets, their ID, summary, status, assignee and trimmed description. It MUST NOT send the full export or other export columns.

#### Scenario: Prompt content
- **WHEN** the system builds a prompt for the LLM
- **THEN** it contains the query and at most the shortlist size in tickets
- **AND** only the allowed fields

### Requirement: Local-only service
The system SHALL listen only on the local loopback address and reject requests with a foreign Host or Origin.

#### Scenario: Foreign origin
- **WHEN** a request arrives with a non-local Host or Origin header
- **THEN** the system rejects it
