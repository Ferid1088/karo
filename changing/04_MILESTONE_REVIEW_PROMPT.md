# Karo — Milestone Review Prompt

Run this after every milestone report from the implementation agent, before
accepting the milestone as done. Paste the agent's report below the line, then
work through the checks in order.

---

You are reviewing a milestone report against three governing documents:
`01_ARCHITECTURE.md`, `02_LESSON_BRUECHE.md`, `03_INVARIANTS.md`, and the
stop-and-ask rules in `00_MASTER_PROMPT.md`.

Do not re-approve based on tone or thoroughness of the report. Check specific,
falsifiable things. For each item below, answer yes/no/unclear and quote the
part of the report your answer is based on — if the report doesn't say, that's
"unclear", not "no", and gets flagged separately.

## 1. Silent deletions or removals

Scan the "files" section for any delete, removal, or replacement of existing
code — not just new additions.

- Was every deletion of previously working functionality called out explicitly,
  not folded into a files list?
- Does `00_MASTER_PROMPT.md`'s stop-and-ask list cover this deletion? If yes,
  was it actually asked, or just done and reported after?
- If it was prototype/dead code being replaced, does the report say how it knows
  that, rather than asserting it?

## 2. Budget and size

- Does any changed or created file exceed the ~400-line guideline from
  `00_MASTER_PROMPT.md`? If the report doesn't mention file sizes, ask for them
  rather than assuming compliance.
- Were changes delivered as several reviewable commits, or one large one?

## 3. Invariant coverage — check against the actual list, not the report's summary

Open `03_INVARIANTS.md`. For every Group A item relevant to this milestone's
scope, and every Group B item if lesson content was touched, ask: is there a
named test for this, or is it only implied by "X tests, Y passed"?

A milestone report that says "21 tests, all invariants covered" without mapping
tests to invariant IDs (A1–A8, B1–B4) has not demonstrated coverage — it has
asserted it. Ask for the mapping if it's missing.

Specifically confirm, don't take on faith:

- A3 (cached paths call zero models) — is there an actual call-count assertion
  on a mocked provider, or just an absence of errors?
- A4 (error type, not wording, drives matching) — is there a test with two
  differently worded answers resolving to the same error type?
- A5 (retries are finite) / A6 (state survives interruption) — same question.
- Any Group A invariant not yet applicable at this milestone: is that stated
  explicitly, or silently absent?

## 4. Scope discipline

- Did this milestone stay inside its own boundary from `01_ARCHITECTURE.md` §9,
  or did it reach into a later milestone's territory (e.g. touching Tier 2/3
  matching, the database engine, or content experimentation before its
  milestone)?
- Any reused component, endpoint, or shortcut described as temporary — is the
  real version scoped into a specific future milestone, or left open-ended?

## 5. Known limitations — press on vagueness

For each limitation listed:

- Is it specific enough to act on, or a vague hedge ("could be improved")?
- Does it name what will fix it and which milestone that belongs to?
- Could any of these actually be a Group A invariant violation described in
  softer language? (e.g. "sometimes regenerates" might mean A3 is not actually
  holding in every case.)

## 6. What the report doesn't mention

- Are there sections of `01_ARCHITECTURE.md` relevant to this milestone that
  the report is silent on (privacy/audit logging, escalation behavior,
  observability metrics)? Silence is not evidence of correctness.
- Does the report state test results verified in a real environment, or only
  that the test suite passed? For UI/rendering claims (e.g. strip width),
  demand the visual verification, not just a green test.

## 7. Verdict

State clearly:

- **Accept** — every check above is yes or explicitly and reasonably deferred
  to a later milestone.
- **Accept with follow-up** — minor gaps, name them as concrete action items
  with an owner (you or the agent) and a deadline (which milestone).
- **Reject** — any Group A invariant is unclear or unmet, any undisclosed
  deletion of working functionality, or any budget/scope violation without
  justification. Say exactly what must be resolved before re-review.

Do not accept a milestone on the strength of its narrative alone. A well-written
report and a correct implementation are different things, and this review
exists to catch the gap between them.

---

## Milestone report to review:

[paste report here]
