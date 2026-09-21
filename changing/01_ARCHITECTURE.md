# Karo — Architecture

Governing document. `02_LESSON_BRUECHE.md` is one instance of what is described
here; `03_INVARIANTS.md` is how these rules are enforced.

---

## 1. The loop

| # | Step | Actor |
|---|---|---|
| 1 | Child submits material: worksheet photo, PDF, topic sheet, or typed topic | child/parent |
| 2 | Extract subject, grade, topic, tasks, visible answers | AI |
| 3 | Ask 3–5 diagnostic questions, stopping early once the gap is clear | app |
| 4 | Classify a wrong answer into a specific error type | catalog, then AI |
| 5 | Serve the best existing explanation for that error type | app |
| 6 | One task, same structure, different values | app |
| 7 | Correct → mastery advances. Wrong → next variant or one level simpler | app |
| 8 | After three unsuccessful teaching rounds → escalation (§7) | app |

Steps 5 and 6 are a lookup, not a generation, in the normal case. That is the
entire cost argument for the product.

---

## 2. Error types are the unit of content

Do not organize reusable content around broad topics ("fractions", "cell
respiration"). Organize it around specific misconceptions:

- adds numerator and denominator
- treats exhaled CO₂ as coming directly from inhaled air
- omits the closing comma on an embedded clause
- uses present tense where German requires perfect

A topic contains many error types. Model the relationship explicitly:

```
Subject → Topic → Concept → ErrorType → ExplanationVariant
                                      → VisualizationConfig
                                      → PracticeTask
```

Use the existing Karo domain vocabulary where it already has good names. These
are the relationships that matter, not the class names.

---

## 3. Visualization: selection, never generation

Models must never produce HTML, SVG, Canvas, React, animation code, video or
image assets — not at runtime, not in a background job, not "just for review".

Build a registry of trusted, tested, parametrized components. Each declares:

- unique id and version
- which subjects/concepts it serves
- a parameter schema
- allowed animation modes
- accessibility metadata
- the renderer

A model's only permitted output is a selection plus parameters:

```json
{ "component": "FractionStrip", "parameters": { "a": [1,2], "b": [1,3] },
  "animation": "cut_then_slide" }
```

Validate against the registry. Unknown component id → reject and fall back to a
safe generic component. Invalid parameters → reject, never render.

The model-facing selector sees component *metadata only*, never implementation.

**Initial set (maths first):** FractionStrip, NumberLine, AreaModel, Balance,
GenericStepFlow.

---

## 4. Teaching content format

The didactic model receives: grade, subject, topic, concept, identified error,
the child's answer. It returns:

```json
{
  "haken": "...",
  "erkenntnis": "...",
  "regel": "...",
  "bild": { "zeigt": "...", "bewegt": "...", "bleibt_gleich": "..." },
  "aufgabe": { "frage": "...", "loesung": "...", "tipp": "..." }
}
```

Validated with Pydantic (or the project's existing schema layer).

Rules the content must follow:

- exactly one concept
- open with an everyday question the child can already answer, mirroring their error
- let the child notice their result cannot be right *before* stating the rule; never open with "that is wrong"
- name one reason for the error, in one sentence
- state the rule as an action, not a definition
- describe exactly one picture: what is shown, what moves, what stays the same
- exactly one practice task, same structure, different values
- no technical vocabulary before the picture, no praise, no emojis, short

`erkenntnis` and `bild.bleibt_gleich` are the quality signals. An explanation
whose `bleibt_gleich` is vague or missing is a weak explanation — flag it rather
than serving it.

---

## 5. Two models

**Model A — didactics.** Analyzes unseen errors, proposes canonical error types,
writes the structured explanation, creates a new variant when explicitly
requested. Stronger and more expensive. **Never called when an adequate catalog
entry exists.**

**Model B — selection.** Picks a component, fills parameters, performs cheap
classifications. Small and fast. Output must conform to the strict schema in §3.

Both sit behind one provider interface so the models can be swapped.

---

## 6. Error catalog and matching

### Key

```
subject / topic / error_type / grade
→ biology/cell-respiration/co2-from-inhaled-air/8
```

### Stored per entry

subject · topic · concept · grade · canonical error type · known wrong answers
and aliases · explanation JSON · visualization config · practice task template ·
difficulty · times served · successful next attempts · success rate · version ·
active flag · creation source · timestamps.

Version, never destructively replace. Losing variants are archived, not deleted.

### Matching, cheapest tier first

| Tier | Method | Uses a model? |
|---|---|---|
| 1 | Exact match against known wrong answers and aliases | no |
| 2 | Embedding + vector search above a configurable similarity threshold | embedding only |
| 3 | Unseen error: Model A analyzes, proposes the type, writes content, persists it | yes |

Never create a new error type because the wording differs, if an existing
misconception matches semantically. Thresholds live in configuration, defined
once — not repeated across the code.

---

## 7. State

One session state machine. Lesson phases are nested inside `TEACHING`.

```
Session:
  INPUT_RECEIVED → MATERIAL_ANALYZED → DIAGNOSING → ERROR_IDENTIFIED
                → TEACHING → MASTERED
                           → ESCALATED

Lesson phases (inside TEACHING):
  HOOK → RULE → WORKED_EXAMPLE → GUIDED_TASK → INDEPENDENT_TASK → COMPLETE
                                             ↘ ADAPTATION ↗
```

Every transition is persisted and testable. A refresh or re-login must resume
the session exactly where it was. Learning state must not live in scattered
route logic.

### Escalation, concretely

After three unsuccessful teaching rounds on the same error type:

1. the session enters `ESCALATED` and stops offering further explanations;
2. the child sees a calm, non-blaming message and can move to a different topic;
3. the error type is flagged on the child's profile as *needs a person*;
4. the next parent report names the topic, the specific misconception, and what
   was already tried.

Escalation is a normal outcome, not a failure state. Do not retry silently, and
do not let the child sit in a loop.

---

## 8. Progress

Track mastery separately from task completion: subject, topic, concept,
encountered error types, attempts, successes, retries, difficulty, last
activity, mastery state.

One correct answer is never mastery. Start with a simple, configurable policy
(no magic numbers in code) and expect to revise it once real data exists.

---

## 9. Milestones

Build vertically, maths first. Do not start a milestone while the previous one
is unstable.

| # | Milestone | Contains |
|---|---|---|
| 1 | Domain foundation | normalized learning input, concepts, error types, catalog, schemas, migration, repository/service layer. No UI redesign. |
| 2 | Maths vertical slice | one topic end-to-end: diagnosis, several known error types, Tier-1 matching, explanation delivery, practice, retry, mastery. Fully usable. |
| 3 | Visualization registry | the five components, strict selection schema, fallback component. |
| 4 | Semantic + generative pipeline | Tier 2 and Tier 3 behind interfaces and feature flags. **This is where Postgres + pgvector enters (§10).** |
| 5 | Worksheet ingestion | photo/PDF/topic-sheet → normalized input. |
| 6 | Measurement | success-rate tracking, analytics, variant experimentation. |

### Definition of done for the first usable version (end of milestone 3)

A child starts a maths session, enters a topic, gets a diagnostic task, gives a
known wrong answer, Karo names the specific misconception, loads the catalog
explanation **without any generation**, renders the correct parametrized
visualization, gives one follow-up task, updates progress, offers a simpler
intervention on a further wrong answer, escalates after three, survives a
refresh, and the parent can see meaningful progress. Tests cover the whole path.

Classes and routes existing is not done.

---

## 10. Storage — decided, do not revisit

**Milestones 1–3 keep the existing database engine.** No engine change, no
pgvector, no separate vector database. Tier-1 matching is exact lookup and needs
none of it.

**Milestone 4 introduces PostgreSQL with pgvector**, because Tier 2 needs vector
search. Write the repository layer in milestones 1–3 so this swap touches the
repository layer only. Plan it as an explicit migration with a documented
rollback, not as an incidental change.

Never introduce a dedicated vector database.

Indexes must support: catalog key lookup, subject/topic/error filtering,
semantic retrieval, a child's active sessions, progress history. All schema
changes go through proper migrations; never silently recreate tables.

---

## 11. Content is generated offline, served deterministically

This resolves an apparent tension: *deterministic at runtime* does not mean
*hand-written*.

- Explanations, help texts, FAQ answers and first-contact content are produced
  by Model A **in a background job or an authoring tool**, reviewed, and
  persisted.
- At runtime they are a pure lookup. No model call, no latency, no surprises.
- A content entry that has not been reviewed is not served to a child.

That is how you get both scale and safety. Nobody types 50,000 help texts, and
no child ever waits for a model to answer "I don't understand this".

### First contact — a topic with no error signal yet

Do not lecture. Per concept, store `anchor`, `first_task`, `naming`, generated
once and identical for every child:

1. **Anchor** — an everyday situation containing the concept, no technical terms.
   Its answer also reveals the child's level without feeling like a test.
2. **Productive failure** — a task just beyond them; let the misconception surface.
3. **Picture** — the rule becomes visible; emphasize what stays invariant.
4. **Naming** — the formal term comes last.

Within twenty seconds this produces a real error signal, which puts you back in
the normal loop with data instead of an assumption.

---

## 12. Content experimentation — not before milestone 6

Record per variant: times served, next-attempt correctness, success rate,
sample size.

Policy, all thresholds configurable: once a variant has ≥ 200 observations *and*
a success rate below 70%, generate exactly one alternative; serve both; stop
permanently once a winner emerges; maximum three variants per error type. Good
explanations are never touched.

Do not generate per child, ever.

---

## 13. Ingestion

Three input paths — worksheet/test scan, topic sheet, manually entered topic —
normalize into one internal learning-input structure.

Keep these as separate steps, not one giant prompt: OCR/document understanding →
task extraction → topic classification → diagnostic generation. Store extraction
confidence. If parsing fails, fall back to manual topic entry.

---

## 14. Privacy

Before anything leaves for an AI provider, run a sanitization layer that strips
name, teacher, school, contact details, date of birth and identifiers.

Do not claim sanitization is perfect — a name inside a word problem cannot be
reliably filtered, and the product should say so.

Log per call: provider/model, timestamp, request type, an audit representation
of the sanitized content, and whether stripping was applied. Do not log raw
child content unnecessarily. Session replay stays off.

---

## 15. Latency and failure

Cache hits must feel instant. For a Tier-3 generation, either stream, or serve a
cached hook while generation runs in the background — the child never stares at
a spinner right after getting something wrong.

Explicit UX states: analyzing, preparing explanation, retrying, recovering.

Degrade, never collapse:

| Failure | Behavior |
|---|---|
| AI unavailable | serve catalog entries and deterministic tasks |
| Semantic search unavailable | continue with Tier 1; Tier 3 only if enabled |
| Visualization mapping fails | safe generic component |
| Worksheet parsing fails | manual topic entry |

---

## 16. Engineering constraints

**Prefer:** the existing Karo architecture, a modular monolith, typed schemas,
deterministic logic, background-task abstraction, provider code behind interfaces.

**Do not introduce:** Kubernetes, microservices, event-sourcing frameworks,
agent frameworks, or a separate vector database.

Prompts live in one dedicated module, versioned, never inline in routes.
Educational policy lives apart from HTTP and UI code, and is independently
testable. Functions do one thing; no giant service classes; configuration
centralized.

Feature-flag the new system so it can ship progressively without breaking the
current app: `adaptive_learning_enabled`, `semantic_error_matching_enabled`,
`llm_error_creation_enabled`, `content_experimentation_enabled`,
`worksheet_ai_analysis_enabled`.

Preserve authentication, the parent/child role separation, existing routing
conventions, database abstractions and design language. If the existing
architecture conflicts with this document, document the conflict and take the
smallest safe path — or stop and ask, per `00_MASTER_PROMPT.md`.

---

## 17. Observability

Metrics: catalog hit rate, Tier 1/2/3 distribution, model calls, tokens and cost
where available, explanation success rate, average attempts before mastery,
escalation rate, latency per pipeline stage, component errors.

The four numbers that actually decide the product:

1. worksheet recognition accuracy
2. diagnostic accuracy — is the child placed correctly?
3. learning success after an explanation
4. catalog hit rate

---

## 18. Parent experience

Parent remains the administrative role with broader access; the child sees only
the child's area. Structure learning data so it can later produce: what the
child understands, where they struggle, recurring error patterns, improvement
over time, suggested next focus.

Report observable learning signals. Never expose raw model reasoning.

---

## 19. Principles, when a judgement call is needed

- Diagnosis before explanation.
- Misconceptions matter more than topic labels.
- Generation creates reusable knowledge, not disposable output.
- Runtime visualization is selection, never code generation.
- One explanation → one concept → one picture → one task.
- The child discovers the contradiction before receiving the rule.
- Terminology comes after intuition.
- An explanation is judged by the next answer.
- Prefer deterministic logic and cached content over a model call.
- Do not replace school material — connect to it.
