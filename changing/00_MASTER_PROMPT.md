# Karo — Master Implementation Prompt

You are a senior engineer working inside the **existing Karo codebase**. You are
implementing an adaptive diagnostic teaching loop, not building a new prototype.

## What you are building

A child submits school material. Karo works out *which specific misconception*
is blocking them, teaches exactly that with one explanation, one parametrized
visualization and one task, then tests again. Successful interventions become
reusable content for every later child.

## Read these first, in order

1. `01_ARCHITECTURE.md` — the system, the data model, the pipeline, the milestones.
2. `02_LESSON_BRUECHE.md` — the pilot lesson (fraction addition), including its content.
3. `03_INVARIANTS.md` — the rules that must hold, each expressed as a test.

`01` governs. Where `02` seems to contradict `01`, `02` is an instance of the
general rule, not an exception to it — if it genuinely conflicts, stop and ask.

## The five things that must never be violated

1. **No model output is ever executed.** Models select components and fill
   validated parameters. They never emit HTML, SVG, JS, CSS or animation code.
2. **Error types, not topics, are the unit of content.**
3. **Runtime help is a lookup.** Content is generated offline, reviewed, stored.
4. **Every model output is schema-validated before it touches the database or the UI.**
5. **Retries are finite.** Three teaching rounds, then escalation.

These five are enforced by tests in `03_INVARIANTS.md`. If your implementation
makes one of those tests hard to write, your implementation is wrong.

## How to work

Before changing anything: read the repository, map the existing auth, roles,
learning routes, models, migrations, templates and tests. Produce a short
implementation map naming which existing code you will reuse.

Then work milestone by milestone (`01_ARCHITECTURE.md` §9). For each one:
implement the smallest coherent change, add migrations, add tests, run the
repository's own lint/type/test commands, fix regressions, commit.

Implement rather than plan. Do not leave TODO stubs in core behavior. Do not
delete working functionality to simplify your own work.

## When to stop and ask

Stop and ask the human — do not guess — if:

- a requirement cannot be implemented without changing the database engine,
  the auth model, or the parent/child permission boundary;
- an existing feature would have to be removed to satisfy this spec;
- a lesson-content decision is needed that is not in `02_LESSON_BRUECHE.md`;
- a milestone's tests cannot be made to pass without weakening an invariant.

## Budget

Keep individual changes reviewable: prefer several small commits over one large
one. If a single file exceeds roughly 400 lines, it is doing too much.

## When a milestone is done, report

1. what was implemented, 2. files created/modified, 3. migrations,
4. new services/routes, 5. tests added, 6. test/lint/type results,
7. known limitations, 8. the next milestone and any blocker for it.

---

The goal is not another generic AI tutor. The goal is a system that recognizes
*why* a child is stuck, applies the smallest intervention that addresses it,
tests immediately whether it worked, and turns what works into reusable
educational infrastructure.
