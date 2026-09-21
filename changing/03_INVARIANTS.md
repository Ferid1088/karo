# Karo — Invariants

A rule that exists only in a prompt survives one implementation. A rule that
exists as a test survives every future one. Everything here must be an
executable assertion, not a paragraph.

Group A is architectural and applies to every lesson. Group B is the fractions
pilot. Group C is ordinary coverage.

---

## A. Architectural invariants — never weaken these

### A1 — No model output is ever executed

```
a catalog entry's visualization config contains no HTML, SVG, JS or CSS
a component id outside the registry is rejected, not rendered
invalid component parameters are rejected, not rendered
a rejected selection falls back to the safe generic component
```

### A2 — Every model output is schema-validated

```
malformed model JSON never reaches the database
malformed model JSON never reaches a template
a schema failure triggers deterministic fallback, not a 500
a truncated/stopped response is detected and not persisted
```

### A3 — Cached content does not call a model

```
a Tier-1 catalog hit triggers zero model calls
opening EXPLAIN_MORE triggers zero model calls
opening the FAQ triggers zero model calls
serving first-contact content triggers zero model calls
```

Assert on a mocked provider that records call count. This is the test that
protects the entire cost model.

### A4 — Errors, not topics, drive content selection

```
two differently worded answers expressing the same misconception
  resolve to the same error type
the same topic with two different misconceptions yields two different explanations
a new error type is not created when an existing one matches semantically
```

### A5 — Retries are finite

```
three unsuccessful teaching rounds on one error type → ESCALATED
ESCALATED serves no further explanation
ESCALATED flags the error type on the child's profile
no code path can loop teaching rounds without bound
```

### A6 — State survives interruption

```
a session resumes at the same phase after refresh
a session resumes at the same phase after re-login
phase, attempts, mastery and the submitted answer are all restored
```

### A7 — Privacy

```
name, school, teacher, DOB and contact details are stripped before any provider call
every provider call is recorded in the audit log
raw child content is not written to application logs
session replay is disabled
```

### A8 — Mastery is earned

```
one correct answer does not produce mastery
mastery thresholds come from configuration, not literals in code
```

---

## B. Fractions pilot

### B1 — Phase flow

```
RULE → WORKED_EXAMPLE → GUIDED_TASK is the actual transition order
the worked example's numbers differ from the guided task's numbers
GUIDED_TASK renders its own fractions visually from first display
INDEPENDENT_TASK renders no fraction pictures on either of its screens
ADAPTATION renders an alternate representation
```

*Amended 2026-09-21: the phase gained a transfer question after the
calculation, so the picture rule is stated per phase rather than per screen —
otherwise a picture could be added to the second screen without any test
objecting. The phase flow itself is unchanged; transfer is a screen inside
`INDEPENDENT_TASK`, not a phase.*

### B2 — Strip rendering correctness

```
the strip component is the only place strips are rendered
every strip has the same total width regardless of denominator
no individual piece has a fixed width
every rendered strip satisfies 0 <= gefuellt <= gesamt and gesamt > 0
every rendered strip has an accessible label
```

The width assertion is the important one: it is the difference between a picture
that teaches the concept and a picture that contradicts it.

### B3 — Help coverage

```
every phase except COMPLETE has an EXPLAIN_MORE entry
every EXPLAIN_MORE entry contains at least one picture
every EXPLAIN_MORE text differs from its phase's on-screen text
the FAQ is reachable in every phase except COMPLETE
EXPLAIN_MORE on an exercise screen does not contain the answer
```

### B4 — Help changes nothing

```
opening or closing help leaves the phase unchanged
opening or closing help leaves attempts unchanged
opening or closing help leaves mastery unchanged
opening or closing help consumes no hint
opening or closing help preserves the child's typed answer
```

---

## C. Ordinary coverage

**Unit:** error normalization · exact-match lookup · semantic-match decision ·
catalog lookup · retry selection · mastery policy · component parameter
validation · variant selection · first-contact sequencing.

**Integration:** input → diagnosis · diagnosis → classification · known error →
cached explanation · unknown error → model → persisted catalog entry · wrong
answer → simpler retry · repeated failure → escalation · correct answer →
progress update.

**Contract:** every provider response validated against its schema, including
the malformed, truncated and empty cases.

---

## How to treat this file

If an implementation makes one of the Group A tests awkward to write, the
implementation is wrong — not the test. Group B may change as the pilot teaches
you things, but only deliberately, with the reason recorded.

New lessons add their own Group B section. Group A does not grow easily; every
addition is a permanent constraint on the codebase.
