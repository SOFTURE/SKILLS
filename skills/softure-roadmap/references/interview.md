# Framing interview: three anchors, each with a recommendation

Read this before step 4 of the procedure. The PRD says *what* to build. The order depends on
three calls the PRD rarely makes explicit. Ask them, one at a time, each with a recommendation
you can defend from the material. Everything else in the roadmap is derived.

Two ways this goes wrong:

- **Interrogation:** asking what the PRD, the shape notes or the code already answer, or asking
  more than three questions. The owner's attention is the scarcest input.
- **False confidence:** deciding the framing silently. These three calls change the order of
  everything; the owner must see them as choices.

## The three anchors

### 1. What this roadmap optimises for (goal)

| Value | Signals in the material | Effect on the order |
|---|---|---|
| `feedback` | "learn from real users", an unvalidated assumption named in the shape notes | ties go to the item that tests the riskiest assumption soonest |
| `quality` | NFRs that gate launch (privacy, correctness, uptime), regulated domain | foundations (observability, access control) are not pushed behind features |
| `simplicity` | small audience, single operator, appetite stated as small | ties go to the smallest viable item; defer aggressively |
| `speed` | a hard date in the PRD summary or shape notes | strict `must` path first; everything else is deferred, not sequenced late |
| `learning` | exploratory project, a stack the team has not shipped | ties go to items that exercise the unfamiliar part earliest |
| `other` | none of the above fits | owner states it in their words |

Adjacent values often fire together (`feedback` and `speed` when the PRD says "ship to learn").
Offer the adjacent one as the alternative, not an unrelated value.

### 2. Which item proves the idea first (north star)

The smallest end-to-end flow that, once merged, shows the core promise of the PRD works for a
real user. It usually traces to the first `must` FR under the primary goal (`G-1`). Offer up to
three candidates by name (`<ID candidate>: <outcome>`), each with why it is a good first proof and
what it costs in prerequisites. The north star is placed as early as its prerequisites allow.

### 3. What most likely stalls the work (main risk)

| Value | Fires when |
|---|---|
| `decisions` | three or more open PRD questions, or one open question that gates a `must` FR |
| `capacity` | scope is wide and the owner is the only reviewer; parallelism is the lever |
| `time` | scope versus the stated date does not fit |
| `skills` | a layer nobody on the project has shipped (payments, offline sync, a new runtime) |
| `external` | a vendor, an account, a legal text or a design asset that is not in hand |
| `none` | no signal fires; say so |

The answer shapes the roadmap: `decisions` → items gated by open questions become
`blocked (<question>)` and the questions go to `## Owner decisions and checks`; `capacity` →
compute parallel lanes generously; `external` → the dependency is a named prerequisite, and an
item that needs the owner's account gets `Mode: owner`.

### Derived, never asked: where to invest depth

For each layer (UI, server, data, infrastructure) decide "invest" or "keep simple" from the goal
answer, launch-gating NFRs, baseline gaps under `must` FRs, and where the open questions cluster.
Name the signal for every "invest". State the result in the recap; the owner may override it in
one line.

## How to ask

- One question per message, in the order goal → north star → main risk.
- Option 1 is the recommendation, labelled `(Recommended)`, with one line of evidence: a quoted
  phrase or an ID from the PRD, the shape notes or the baseline, and why it matters *for this
  question*. A quote that does not change the answer is noise; drop it.
- At most two alternatives, each with the condition under which it would be the right call and
  what it would change in the order. An alternative without that condition is a strawman; remove it.
- Always a last option "something else: tell me".
- If the material supports only one reading, offer the recommendation plus the free-form option
  and say "the material supports only one reading here; correct me if yours differs".
- Ask in `workflow.json` → `language`, in plain product words. Not "north star" but "the first
  thing that shows the product works". If no question tool exists, ask in plain chat with
  labelled options.

**Skip an anchor** only when the material states the value outright (a launch date plus "must be
live before the season" locks `speed`). Announce the skip with the quote. If any plausible
alternative exists, ask.

**Unusual product shape.** When the product is not a familiar pattern (dashboard, CRUD tool,
content site, marketplace, wrapper around a model), say before the first question that your
recommendations are weaker than usual and invite pushback. Phrase the evidence as "my best read".
You may add up to two free-form follow-up exchanges after the anchors. That is the only way to go
beyond three.

**Cap.** Three anchors (plus two follow-ups in the exception above). If an anchor is still open
after that, take the recommendation, record it with its reason under `## Order`, and continue.

## Recap (no new question)

After the last answer, send one message that locks the framing:

```
Locking in the framing:
- Optimising for: speed. You chose it; PRD summary: "live before the spring season".
- First proof: BK-2, a visitor books a free slot and gets a confirmation. It exercises G-1 end to end.
- Main risk: decisions. PRD has 3 open questions; the cancellation one gates FR-5.
- Depth: data (availability rules are the core; NFR-2 forbids double booking). The rest stays simple.

Say "go", or correct any line ("depth should be in UI, not data"). I will not re-ask the others.
```

## `--auto`

No questions. Take each recommendation; when two values are equally supported, choose the one
that orders risk earlier. Record every anchor under `## Decisions (auto)`:
`- Optimising for → speed (PRD summary: "live before the spring season")`.

## Example: a good and a bad question

Good (booking app, anchor 2):

```
Which item should prove the product works first?

1. BK-2: a visitor books a free slot and gets a confirmation (Recommended)
   It is FR-1 + FR-3, the core of G-1 "clients book without calling". Needs only the
   availability model (BK-1).
2. BK-4: staff see the day's bookings
   Right if the clinic's first pain is the paper diary, not phone calls; it would move the staff
   view ahead of public booking.
3. Something else: tell me.
```

Bad:

```
What is the north star wedge? 1) Booking  2) Payments  3) Analytics  4) Notifications  5) Other
```

Why it is bad: jargon the owner has to decode; five options with no evidence; "Analytics" is not in
the PRD (a strawman that also invents scope); no recommendation, so the owner does the analysis the
skill was supposed to do.
