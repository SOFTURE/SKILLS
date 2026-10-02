# Example lessons

Fictional projects. Use them for the bar a lesson must clear, not for content.

## A new lesson (booking app)

The incident: change `prevent-double-bookings` added a unique index on
`(therapist_id, starts_at)`. The migration passed on the dev database and in CI (both empty of
conflicts) and failed on production, where 11 duplicate rows existed. The release was rolled
back and the deploy window lost.

```markdown
## L-019: Before adding a unique constraint, count the rows that violate it on production-like data
**Why:** 2026-09-18, prevent-double-bookings: the unique index on bookings(therapist_id, starts_at) passed on dev and CI, which had no conflicts, and failed on production with 11 duplicates; release rolled back, deploy window lost.
**How to apply:** in research or plan for any change that adds UNIQUE, NOT NULL, CHECK or a foreign key, run the violating-rows query against the freshest copy available and put the count in research.md; when it is not zero, the plan's first phase resolves those rows. Plan-review flags a constraint migration without that count.
**Applies to:** `drizzle/*.sql`, `src/db/schema.ts`; skills: research, plan, plan-review.
```

Why it is good: the title can be checked against a plan ("where is the count?"); the incident
is findable by change id and date; the trigger lists the kinds of migration, not "migrations
in general"; it names who enforces it.

## The same mechanism again: add an incident, no new number

Two months later, change `invoice-number-unique` hit the same failure with a different table.
Dedupe finds L-019. The rule is unchanged, so only **Why** grows:

```markdown
**Why:** 2026-09-18, prevent-double-bookings: … release rolled back, deploy window lost.
Also: 2026-11-04, invoice-number-unique: UNIQUE on invoices(number) failed on staging with 3 duplicates created by a 2025 import script.
```

## A broader rule: widen the title, keep the number

The team lead points out that the same trap applies to `NOT NULL` backfills, which L-019's
title does not mention. The title is widened in place, keeping `L-019`, and the widening is noted:

```markdown
## L-019: Before adding any constraint, count the rows that violate it on production-like data
**Why:** … (widened 2026-11-10 from "unique constraint" after a NOT NULL backfill on customers.vat_id failed the same way)
```

## Bad entries, and why

```markdown
## L-020: Be careful with migrations
**Why:** Migrations can break things.
**How to apply:** Always test migrations carefully.
**Applies to:** everywhere.
```
Not testable (what does "careful" look like in a diff?), no incident, and "everywhere" matches
nothing. Either find the concrete mechanism (as in L-019) or record nothing.

```markdown
## L-021: Anna forgot to run the seed script before the demo
```
Blame and a one-off. The mechanism, if there is one, is "the demo checklist has no seed step",
and that is a task for the checklist, not a lesson.

```markdown
## L-022: Use parameterized SQL
```
Already in the conventions block. A lesson repeats a convention only when a real incident shows
the convention was not enough, and then the lesson names what specifically was missed (for
example, a raw query builder that bypassed parameters in `src/reports/`).
