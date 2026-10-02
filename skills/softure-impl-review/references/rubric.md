# Rubric: dimensions, scales, finding format, verdicts

## Dimensions

Every finding belongs to one dimension. Every dimension gets a verdict, even when it has no
findings, so the reader sees what was looked at.

| Dimension | What to check | FAIL when |
|---|---|---|
| Plan adherence | each planned change exists and does what the phase said; each phase has its commit | a planned item is missing, or implemented with a different intent |
| Scope | unplanned files, endpoints, columns, flags; change.md Constraints (files owned by another change) | Constraints broken |
| Progress honesty | evidence for every `- [x]`; gates and command criteria re-run; agent-verified manual items point at real evidence | any ticked item without evidence, any red gate |
| Correctness | edge cases, error paths, concurrency, transactions, cache invalidation, time zones, rounding | wrong behaviour on a realistic input |
| Tests | a test per new behaviour that fails without it; specific assertions; edge and error cases; the break-it check | the riskiest behaviour can be broken with every test green |
| Data and migrations | forward-only, rollback note, indexes, constraints in the database, numbering, destructive steps | data loss possible, or an invariant enforced only in code where a constraint was planned |
| Security | authorization per action and route, input validation, parameterized SQL, secrets, error leakage, rate limits | any exploitable gap |
| Architecture and patterns | module boundaries and dependency direction; one or two sibling files compared for registration, error handling, structure, tests | a boundary is crossed (UI importing the database layer, a cycle) |
| Lessons | every rule in lessons.md whose "Applies to" matches the touched paths | a lesson is broken without a recorded reason |

Verdict per dimension: **PASS** (nothing above SUGGESTION), **WARNING** (WARNING findings
only), **FAIL** (the condition in the table, or any CRITICAL).

**Patterns, scaled to the diff.** For three files or fewer, a quick look at one sibling is
enough. For a larger diff, compare each new module with the closest existing one. Report only
mismatches that cost something: a job registered outside the scheduler the other jobs use, an
endpoint without the auth wrapper its neighbours use, an error type nobody else throws. A
different but working formatting choice is not a finding.

**Phase reviews** also ask: did this phase change something an earlier phase relied on (a
renamed export, a changed return shape, a migration that alters a column an earlier test seeds)?

## Severity

| Severity | Meaning | Blocks |
|---|---|---|
| CRITICAL | wrong behaviour, data loss risk, security hole, Progress claiming something not done | archive and merge |
| WARNING | real defect or gap with limited blast radius | nothing, but needs a decision with a reason |
| SUGGESTION | better, not wrong | never |

Grade by consequence, not by how easy it was to spot. When torn between two levels, ask "what
happens in production if nobody touches this?" and pick the level that answer describes.

## Impact

| Impact | Meaning, always printed next to the level |
|---|---|
| LOW | obvious, narrow fix; safe to decide in a batch |
| MEDIUM | a real trade-off; think before deciding |
| HIGH | wide blast radius or no clear best path; decide deliberately |

Severity says how bad it is to ignore; impact says how hard it is to decide. Print both on every
finding so the user can skim to the hard decisions.

## Finding format

```markdown
### F2 [WARNING] <one-line title, nothing else on this line>
**Impact:** MEDIUM (a real trade-off) · **Dimension:** Architecture and patterns · **Where:** jobs/late-fees.ts:12
**What:** what the code does, with evidence (plan line vs code line, or code vs the sibling it should match).
**Why it matters:** the consequence if it ships as is.
**Evidence:** the command, test, query or file that shows it.
**Fix:** one concrete change.
**Decision:** …
```

Default to **one** fix. Offer two only when a careful reviewer would genuinely weigh them (patch
the caller or fix the source; a database constraint or a code check). Then each option is one
block, and exactly one is recommended:

```markdown
**Fix A (recommended):** <one sentence>
- Strength: <the advantage, grounded in this codebase or the plan>
- Trade-off: <the cost or risk>
- Confidence: HIGH | MEDIUM | LOW, <why>
- Blind spot: <what was not verified, or "none found">
**Fix B:** <one sentence>
- Strength / Trade-off / Confidence / Blind spot as above
```

For a LOW-impact finding the single `**Fix:**` line is enough; strength and trade-off are noise
when the answer is obvious.

Specific beats general:
- Good: "`invoices/apply-late-fee.ts:41` inserts a fee row without checking for an existing one;
  the job runs hourly, so a second run in the same day doubles the fee (reproduced: two runs, two
  rows for invoice 1042)."
- Bad: "Fee logic might have idempotency issues."

## Overall verdict

Computed after triage, from the decisions, and stated in `## Verdict`:

- **Ready**: no finding needed a code change; every dimension PASS or WARNING with accepted or
  deferred findings.
- **Ready after fixes**: fixes were applied in this run; after them no CRITICAL is open, the gates
  are green, and every finding has a decision.
- **Not ready**: a CRITICAL is deferred or unresolved, a gate is red, a pending decision remains,
  or the review showed that the remaining work needs a re-plan (name the step: `softure-plan`).

Order findings CRITICAL, then WARNING, then SUGGESTION, and by impact within a severity. Cap
the list at ten: merge findings with one root cause into one (list every location), and drop
SUGGESTIONs before anything else. A CRITICAL is never merged away or dropped.

## Briefs for review subagents (large diffs)

Keep the plan and the file map in the main context; let subagents read the code. Two read-only
subagents in parallel, each with only what it needs:

**Plan drift.** Give it: the text of the phases under review and the list of files the plan
names. Ask: for each planned change, read the file and report path, what the plan said, what
exists, and a verdict MATCH / DRIFT / MISSING / EXTRA. Intent mismatches only, not formatting.

**Safety, correctness and patterns.** Give it: every changed file path, the project root, the
relevant AGENTS.md sections and lessons. Ask: read each file in full; report security,
correctness, performance, reliability and data-safety problems with file, line, dimension,
proposed severity, evidence and a fix; for each new module, compare with one or two siblings and
report substantive mismatches only.

Merge their output, verify every CRITICAL yourself in the code before it goes into the report,
and grade with this rubric. A subagent's severity is a proposal.
