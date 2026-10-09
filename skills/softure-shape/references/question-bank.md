# Shape interview: question bank, pushback patterns and anti-patterns

Read this before the interview. It holds what to ask in each phase (greenfield and brownfield
variants), the option sets to offer, how to push back, and the two anti-pattern scripts. The
questions are starting points: rephrase them in the user's domain and in `chatLanguage` (default: `language`). Never
paste a whole phase at once; one question per message.

## The loop inside every phase

1. **Open** with one sentence saying what this phase produces, then one open question. Let the
   user make the first attempt in their own words.
2. **Echo back** what you heard, split into labelled parts (see each phase). Missing or vague
   parts become the next question.
3. **Offer positions** where the answer is a choice: 2 to 4 real options, each with its
   trade-off in a few words. Put the recommended one first and mark it "(Recommended)", with
   the one-line reason. Add "Not decided yet" as the last option; picking it sends the point
   to `## Open questions` with an owner.
4. **Lock** the phase: a one-line summary per section, "Correct?". Write only after a yes.
5. **Write** the sections of this phase into `shape-notes.md` and move on.

With a question tool (AskUserQuestion or similar), use it for step 3. Without one, number the
options in plain text so the user can answer "1".

`--auto`: there is no loop. For each phase, take what the inputs say, apply the same echo
split to find the gaps, and write `UNKNOWN: <what would answer it>` for each gap. A
recommended option may be written only when the inputs support it; record it under
`## Decisions (auto)`.

## Phase 1: Problem and who

**Produces:** `## Problem`, `## Who it is for`; brownfield also `## Current system`.

Greenfield opener: "Let's start with the pain, not the product. Who has it, in what moment do
they feel it, and what does it cost them today?"

Echo split:
```
Pain:       <the problem in the user's words>
Person:     <a role or a named person, never "users">
Moment:     <the situation that triggers it>
Cost today: <time, money, errors, or stress, with a number if there is one>
Evidence:   <quote, number, incident; or "none yet">
```

Brownfield opener: "What exists today, who uses it, and what is missing or broken that makes
you want to change it?"

Echo split:
```
Current system: <product or module, in one line>
Users today:    <roles and rough count>
Gap:            <what is wrong or missing>
Must preserve:  <behaviour, data or integrations that must not break>
Evidence:       <ticket, quote, metric; or "none yet">
```

Option sets (offer when the first answer is fuzzy):
- *Kind of pain:* workflow friction / missing capability / data stuck in the wrong place /
  decisions made blind / coordination overhead between people.
- *Kind of change (brownfield):* new capability / change to existing behaviour / replacing a
  manual step / integration / performance or reliability.
- *Primary person:* one role inside one organisation / the same role across many
  organisations / one named person (often the user) / a hobby niche.

Pushback prompts:
- Vague scope words ("everyone", "always", "a lot"): "Who specifically ran into this in the
  last month, and what did they do?"
- No evidence: "How do we know? A quote, a support ticket, a number, or your own last week?"
  "None yet" is an acceptable answer; record it as such.
- Premise check: "What would have to be true for this to be the wrong problem?"
- Insight: "If this is obvious, why does nobody solve it well today?" The answer is the
  insight the PRD summary needs.
- Brownfield, no "must preserve": "If this shipped tomorrow and broke something, what would
  you hear about first?"

## Phase 2: Today and why now

**Produces:** `## Today`, `## Why now`.

- "Walk me through the last time this happened. What did you do, step by step?"
- "What do people use instead? Include a spreadsheet, a chat group, or doing nothing."
- "What changed recently that makes this worth doing now? What does waiting three months
  cost?"

Pushback: if the workaround is cheap and painless, say so and ask whether the problem is big
enough. A real problem has a workaround that hurts.

## Phase 3: Access

**Produces:** `## Access`. Every product has an access model, even "one person, one device".

Greenfield: "How does this person get in, and does anyone else see their data?" Options:
- account with sign-in (Recommended for anything multi-user or shared);
- local only, data stays on the device (Recommended for single-user, privacy-first tools);
- link or code, no account;
- none: single user, single device.

Follow-up when there is more than one person: "Does everyone see and do the same things, or
are there roles (for example owner, member, guest)?" Pushback: "What is the smallest access
model that still makes the first version useful?"

Brownfield: "How do people get in today, and which roles exist? Does this change touch
either?" When nothing changes, write "No change: current model preserved."

## Phase 4: Appetite and the first flow

**Produces:** `## Appetite` and the `First flow` part of `## Solution sketch`.

- Appetite: "How much time is this worth to you? A fixed budget (days or weeks), not a
  guess at how long it takes." Also ask about a hard deadline and whether this is full-time
  or side work. Record all three.
- First flow (greenfield): "Describe the first session of a new user, step by step, until
  they get the value."
- First flow (brownfield): "Describe how one existing user's day changes after this ships.
  What do they do differently?"

Echo the flow as numbered steps. Then run the **scope-cost check** below.

## Phase 5: Solution sketch and the core rule

**Produces:** the rest of `## Solution sketch`, `## Core rule`.

- Sketch: "What are the few elements this needs? Think boxes and arrows, not screens."
- Modules: when an element is generic (sign-in, mail, waitlist, billing, consent, feature
  switches…), note "use `@softure-ai/<module>`" next to it.
- Core rule (greenfield): "In one sentence: what does the product decide or compute for the
  user that a spreadsheet would not?"
- Core rule (brownfield): "What rule does the current system apply here, and does this change
  add a rule, modify it, or leave rules alone (pure infrastructure)?" For a modification,
  write the current rule first, then the change. For infrastructure work, write "No domain
  rule change."

Run the **empty-CRUD check** below when the answer is only "users can add, edit and delete
things".

## Phase 6: Rabbit holes, constraints and no-gos

**Produces:** `## Rabbit holes`, `## No-gos`; brownfield also
`## Constraints and preserved behaviour`.

- Rabbit holes: "Which part could quietly eat the whole budget?" For each, get a decision:
  cut it, fake it (manual or hardcoded first), time-box it, or accept the risk.
- Constraints (brownfield): "Which integrations, exports or contracts must keep working?
  What happens to existing data? Who relies on the current behaviour?" Record outcomes ("old
  invoices keep their numbers"), not mechanisms.
- No-gos: offer 3 to 5 options **drawn from this domain** (multi-select), covering both kinds:
  - capabilities we will not build now (for example: "no team workspaces", "no own payment
    processing");
  - quality levels we will not aim for now (for example: "no offline use", "no multi-region
    availability");
  - brownfield: parts of the existing system we will not touch ("no change to sign-in").

  Technology choices ("no PHP", "avoid a monorepo") are **not** no-gos. Put them under
  `## Forward notes`.

## Phase 7: Success signals and guardrails

**Produces:** `## Success signals`.

- "What would you see, a month after release, that tells you it worked?" Turn the answer into
  signal → threshold → how measured.
- "What must not get worse while we do this?" These are guardrails (privacy, response time a
  user would notice, an existing flow). Brownfield guardrails always include the preserved
  behaviour from phase 6.
- Scale probe: "Roughly how many people will use it in the first months: a handful, dozens,
  thousands?" Then: "Does the core rule still hold at a hundred times that?" Record a
  surprise as an open question or rabbit hole.

## Scope-cost check (phase 4)

Run it when any of these is true:
- the first flow has more than about six user actions before the first value;
- it needs two or more external services or integrations before anything works;
- the user's own estimate, or yours, is larger than the appetite.

Name the expensive pieces. Never say only "this is big". Then offer:

1. **Scope down (Recommended)**, with 2 or 3 concrete moves for this idea:
   - greenfield: drop <piece> from the first version; replace <integration> with a manual
     step; serve one user (often the user themselves) first;
   - brownfield: one role or one use case first; keep the old path as a fallback and add the
     new one beside it; leave <integration> for a later round.

   The brownfield trap to name: a large change left half-done in an existing system is worse
   than no change.
2. **Keep the scope, grow the appetite.** Allowed, but only knowingly. Record one line under
   `## Appetite`: `Accepted on <date>: <scope> needs about <N> weeks; owner accepted the
   longer budget.` Do not repeat the warning after that.
3. **Re-sketch the first flow** from scratch.

`--auto`: never grow the appetite. Record the expensive pieces and the scope-down moves under
`## Decisions (auto)` and leave the choice to the owner as an open question.

## Empty-CRUD check (phase 5)

When the "core rule" is only storing and listing records, name it: a product that only
stores and lists what the user typed gives nothing a spreadsheet or a notes app would not.
Then offer the common shapes of a real rule, asking which one this product applies:

| Shape | The product… |
|---|---|
| Recommendation | suggests items from the user's state |
| Prioritisation | orders items by urgency or importance it infers |
| Classification | tags items by type, quality or risk |
| Validation | checks items against a rule and flags problems |
| Scoring | rates items so they can be compared |
| Workflow | moves items through states with rules for each transition |
| Calculation | derives a value from the user's inputs |
| Allocation | hands out a limited resource (slots, seats, stock) by a rule |

Options: one of the shapes (then return to the one-sentence question) / "Give me a moment" /
"It really is a plain list; record that". The last one is allowed: write
`UNKNOWN: core rule` and add a **blocking** open question. Brownfield infrastructure work
skips this check.

## Reframing quality wishes (any phase)

Users often state a quality as a mechanism. Reflect it back as something an outside observer
could measure, and keep the mechanism under `## Forward notes`:

| User says | Write in shape notes |
|---|---|
| "cache the dashboard in Redis" | the dashboard shows within 1 s for a typical account |
| "add a spinner while it loads" | any wait over 2 s shows visible progress |
| "rate-limit the login per IP" | repeated wrong passwords from a script are stopped; a person who mistypes three times is not locked out |
| "store everything in Postgres" | (nothing: this is a stack choice, goes to `## Forward notes`) |

## Sample exchange

How one turn should look: one question, a recommendation with its reason, and a pushback
that parks the solution instead of dropping it.

> **Agent:** Who feels this most: the studio manager who fixes the double bookings, or the
> members who turn up to a taken wheel?
> 1. The manager (Recommended: she spends the time, and she decides whether to adopt a tool)
> 2. The members
> 3. Both equally
> 4. Not decided yet
>
> **User:** 1. Honestly we just need an app with a calendar and push notifications.
>
> **Agent:** Noted under *Solution sketch*: calendar and notifications; we will come back to
> them. Before that: the last time a double booking happened, what exactly did the manager
> do, and how long did it take?

Bad turn, for contrast: "Tell me about the users, their goals, the main features, your
timeline and how you will measure success." Five questions at once, no recommendation, and
it invites a feature list before the problem is clear.
