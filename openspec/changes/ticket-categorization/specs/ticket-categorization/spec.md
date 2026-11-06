## ADDED Requirements

### Requirement: Categorization page
The system SHALL provide a page at its own URL (`/categorize`), separate from the ticket lookup chat, where the user enters a free-text problem description and receives a recommended ticket category.

#### Scenario: Open the page
- **WHEN** the user opens `/categorize` on the local server
- **THEN** a page with a description input is shown
- **AND** it links back to the ticket lookup chat

#### Scenario: Lookup page unaffected
- **WHEN** the user opens `/` or sends a message to `/api/chat`
- **THEN** the ticket lookup behaves as before

### Requirement: Category recommendation
The system SHALL search the same ticket export used by ticket lookup and recommend one `ISSUETYPE` value for a new ticket, plus at most 2 alternatives, best first. The input MAY be Italian, English or mixed.

#### Scenario: Clear problem
- **WHEN** the user describes a problem that matches past tickets
- **THEN** the response contains one recommended `ISSUETYPE`
- **AND** at most 2 alternative categories

#### Scenario: Category values come from the export
- **WHEN** a recommended or alternative category is displayed
- **THEN** its `ISSUETYPE` value is one that occurs in the ticket export rows similar to the description

#### Scenario: Reason language
- **WHEN** the user describes a problem in Italian or in English
- **THEN** the reason is written in the language of the description

### Requirement: Supporting evidence
The system SHALL show up to 3 similar past tickets whose `ISSUETYPE` equals the recommended category, each with task ID, summary and readable status, taken from the export.

#### Scenario: Examples shown
- **WHEN** a category is recommended
- **THEN** up to 3 similar tickets of that category are listed
- **AND** their ID, summary and status equal the export values

#### Scenario: Support count
- **WHEN** a category is displayed
- **THEN** the response indicates how many of the similar tickets considered belong to it

### Requirement: Readable category labels
The system SHALL show `ISSUETYPE` through a configurable label map, together with the raw code. A code with no configured label SHALL be shown as "Type <code>". Labels MUST NOT come from LLM-generated text.

#### Scenario: Known code
- **WHEN** a category code has a configured label
- **THEN** the label and the code are shown

#### Scenario: Unknown code
- **WHEN** a category code has no configured label
- **THEN** it is shown as "Type <code>"

### Requirement: No-match response for categorization
The system SHALL say that no category could be suggested, and SHALL NOT recommend one, when no ticket in the export is relevant to the description or the description has no usable words.

#### Scenario: Unrelated description
- **WHEN** the user sends "ricetta per la torta di mele"
- **THEN** the response says no category could be suggested and asks for more detail
- **AND** no category is recommended

### Requirement: Degraded mode without LLM decision
The system SHALL still recommend a category when the LLM call fails or returns unusable output, based on the similar tickets scored locally, and SHALL include a notice that LLM ranking was unavailable.

#### Scenario: LLM call fails
- **WHEN** the LLM call fails or returns invalid output
- **THEN** the response recommends the category with the highest total local similarity score
- **AND** it includes the notice that LLM ranking was unavailable

#### Scenario: LLM names an unknown category
- **WHEN** the LLM returns an `ISSUETYPE` that does not occur in the similar tickets
- **THEN** that category is not shown to the user

### Requirement: Independent categorization
The system SHALL treat each description as an independent request, and SHALL NOT write the description, results or the export to disk.

#### Scenario: Second description after the first
- **WHEN** the user sends a second description
- **THEN** the result depends only on the second description

### Requirement: Limited data exposure for categorization
The system SHALL send to the LLM only the description and, for at most 30 similar tickets, their ID, summary, trimmed description and `ISSUETYPE`. It MUST NOT send the full export or any other export column.

#### Scenario: Prompt content
- **WHEN** the system builds the categorization prompt
- **THEN** it contains the description and at most 30 tickets
- **AND** only the allowed fields

### Requirement: Categorization language and theme
The categorization page SHALL offer the same EN/IT language switch and light/dark theme as the lookup page, sharing the stored choices. Fixed notes returned by the API follow the request `lang`; an unknown or missing `lang` falls back to English.

#### Scenario: Italian notes
- **WHEN** a request is sent with `lang` set to `it` and no category can be suggested
- **THEN** the fixed note is in Italian

#### Scenario: Unknown language
- **WHEN** a request is sent with an unsupported `lang`
- **THEN** the fixed notes are in English

### Requirement: Categorization endpoint safety
The categorization endpoint SHALL apply the same local-only rules as the lookup service: loopback binding only, rejection of a foreign Host or Origin, and a not-ready response when Copilot is not installed or signed in. Only whitelisted static files are served for the page.

#### Scenario: Foreign origin
- **WHEN** a request to the categorization page or endpoint arrives with a non-local Host or Origin
- **THEN** the system rejects it

#### Scenario: Copilot not ready
- **WHEN** a categorization request arrives while Copilot is not ready
- **THEN** the response has the `not_ready` error and the page shows the setup state
