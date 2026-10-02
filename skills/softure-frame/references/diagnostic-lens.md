# Diagnostic lens: from observation to the real problem

Read this when steps 3 to 5 of softure-frame run on a bug, scope or assumption shape and the
surface is large enough to need subagents or careful narrowing.

## Building the map

The map is the set of places where the observation could originate. It comes from reading
this system, not from a generic checklist.

- **Trace the chain** from the stated cause to the observed effect. For runtime problems the
  chain is the data flow: input, validation, transformation, storage, read, render, side
  effects. For scope problems it is the layers of the decision: user need, product rule,
  data model, UI. For assumption problems it is the chain of "because": we want X because
  users do Y because Z.
- **Keep only plausible nodes.** A node belongs on the map if a fault there would produce
  roughly this observation. A node you have no reason to suspect stays off.
- **Mark the stated cause** with `<- stated`. The rest of the map is the hypothesis space.

Present it as a short list before investigating:

```text
The observation could originate at:
  1. Client form submits twice on slow networks     <- stated
  2. Server write has no uniqueness check
  3. Calendar sync job re-imports bookings
Investigating each before deciding.
```

## Expected-evidence brief (one subagent per hypothesis)

Launch all of them in one message so they run in parallel. Read-only.

```text
Observation (verbatim): "<observation>".
Hypothesis to test: the problem originates at <node>: <one line>.
Question: if this hypothesis were true, what would we expect to see in the code, data, logs or
history? Look for exactly that. Also look for what should be ABSENT if it were true.
Report: present / partial / absent, each with path:line, query result or log line.
Rules: read-only; no fixes or proposals; at most <N> words; say what you searched and did not find.
```

Use a fast search agent for "find where X is handled", a general-purpose read-only agent for
"trace this chain and tell me whether assumption Y holds".

## Grading

| Verdict | Meaning |
| --- | --- |
| STRONG | Expected evidence present, the inverse check holds, and it explains the observation's timing and frequency |
| WEAK | Some expected evidence, or it explains the observation only partly |
| NONE | Expected evidence absent, or the inverse check fails |

The candidate reframe is a STRONG hypothesis that is not the stated cause. Two STRONG
hypotheses usually mean two problems: say so instead of picking one.

## Pressure test

Before trusting the leader, try to break it from a different angle:

- **Blind search.** A fresh subagent gets only the observation, not your hypothesis: "What in
  this system most likely produces this? Look without preconception." Agreement raises
  confidence; a different answer is a signal to read carefully.
- **Prior occurrences.** Search `context/archive/*/`, `context/foundation/lessons.md`, commit
  messages and issue history for the same symptom or the same scope argument.
- **Inverse check.** What else must be true if the leader is right? Verify one such
  consequence. What must not be visible? Confirm it is absent.
- **Original framing once more.** If the stated cause fits the evidence just as well, keep it.

If the pressure test produces a credible alternative, put it on the map and run step 4 again
once. If the case is still open after that second round, the honest output is LOW confidence
and a verification step.

## Narrowing questions

Good narrowing questions are decisive: whatever the answer, at least one hypothesis moves.

| Weak question | Why weak | Decisive version |
| --- | --- | --- |
| "Is it a frontend or backend issue?" | asks the user to diagnose | "Do the duplicates have the same creation second, or seconds apart?" (same second: double submit; apart: re-import) |
| "Should we add a lock?" | a solution, not an observation | "Have you seen duplicates on bookings made by staff in the admin panel, which has no double-click?" |
| "How important is this?" | does not split hypotheses | "Since when have you seen it: always, or since the calendar sync launched?" |

Every narrowing question offers "I have not checked". A "not checked" answer becomes a
verification task, not a guess.
