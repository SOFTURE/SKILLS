# Review lenses: what to ask, what a finding looks like

Read this during the first reviews in a repo, and whenever a lens feels thin. Each lens lists
the questions to ask of the plan and a typical finding with its usual severity. Severity is a
starting point: raise it when the consequence is worse in this codebase.

## Coverage and end state

- Walk the phases in order. At the end, is change.md Intent true for the user it names?
- Could every Done-when criterion pass while the goal is unmet? (Tests prove the rule, nothing
  ever calls it.)
- Does the plan do 90% and stop: data written but never shown, a job built but never scheduled,
  a setting saved but never read?
- Is every roadmap Unknown and research risk answered by a phase or a mitigation?

Typical: "The job is implemented and tested, but no step registers it with the scheduler."
CRITICAL.

## Slicing

- After each phase, do the gates pass and could it be deployed alone?
- Do phases follow layers (all schema, then all logic, then all UI)?
- Does a later phase quietly fix something an earlier phase leaves broken?

Typical: "Phase 1 changes the column type, but the code that reads it is only updated in
phase 3; the app is broken between the two." CRITICAL.

## Verifiability

- Could a stranger check each criterion with a command, a query or a precise look?
- Are there "works", "correctly", "looks good", "handles errors", "is fast" without a measure?
- Is each criterion an end state rather than an activity ("implement X")?

Typical: "2.3 'Errors are handled' names neither the error nor the visible result." WARNING.

## Data and migrations

- Is the migration in the configured folder, ordered correctly against the code that needs it?
- Does it lock a large table (adding a non-null column with a default, a new index without a
  concurrent build)? How many rows does research say the table has?
- Is the backfill separate and restartable? What happens if it stops halfway?
- Rollback or "forward-only, because..."? Does rollback lose data written since?
- Does a criterion read real rows after the change?
- Does another in-flight change touch the same tables or migration numbers?

Typical: "A non-null column with a backfill in the same migration, on a table research sized at
2 million rows; no restart path." CRITICAL.

## Tests

- TDD where the logic has clear inputs and outputs (money, dates, parsing, permissions, state)?
- Are the edge cases named: empty, null, boundary values, duplicates, concurrency, failures?
- Is a user-visible outcome covered end to end, or only by unit tests of its parts?
- For a bug fix: is there a test that fails without the fix?

Typical: "The eligibility rule has a test per happy path but none for the day boundary in a
non-UTC zone, which research named as a risk." WARNING.

## Security

- Does every new route, server action, job input or webhook check authorisation, not just a
  session?
- Is external input validated at the boundary?
- Are secrets read from the environment, and never logged?
- Do error messages stay free of stack traces, internal paths and other users' data?

Typical: "The new action takes `clientId` from the form and updates it without checking the
user owns the client." CRITICAL.

## Lean

- Remove the phase or step in your head. Is the goal still met? Then it is not needed.
- Is there an abstraction with one or two users (a provider system for two config sources)?
- Is there "while we are here" work that change.md does not ask for?

Typical: "Phase 1 builds a generic notification channel layer; the change sends one kind of
email." WARNING.

## Fit

- Does the plan introduce a second way to do something the codebase already does (a second
  retry helper, a second date library, a second form pattern)?
- Do dependencies point the right way (domain code importing UI, a shared module importing a
  feature)?
- Does it change a shared utility used in many places, and does it list those callers?
- Are there vague steps ("refactor as needed", "update the callers accordingly")?

Typical: "'Update format_amount as needed': research shows 14 importers across 5 areas; the
plan names none." WARNING.

## Cost and defaults

- What does this cost at the expected volume: paid API calls, emails, compute, storage?
- Does a changed default alter behaviour for existing users or data without them asking?
- Does a new background job run often enough to matter, and is that intended?

Typical: "The job runs every minute and calls the exchange-rate API per invoice; at current
volume that is 40,000 calls a day on a 1,000-a-day plan." CRITICAL.

## Scope

- Does any phase do something outside change.md Intent?
- Does it touch files that change.md Constraints or the roadmap assign to another change?
- Does an out-of-scope item from the plan's own goal reappear in a phase?

## Reuse

- Does a SOFTURE module cover what the plan builds by hand (WORKFLOW.md §10)? If it almost
  covers it, is the gap recorded as an issue instead of a local re-implementation?
- Does the codebase already have a helper for this?

## Lessons

- For each lesson whose "Applies to" matches the touched paths: does the plan follow it?
- Quote the lesson id in the finding. A finding backed by a lesson is at least a WARNING.

## Progress format

- Result of the mechanics check: one Progress section, last; matching phase titles; one item
  per criterion; no checkboxes elsewhere; gates item last in every phase.
- Any defect here is CRITICAL: softure-implement resumes from this section.
