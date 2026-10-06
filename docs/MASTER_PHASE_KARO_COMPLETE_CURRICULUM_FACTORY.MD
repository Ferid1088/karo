GLOBAL EXECUTION RULE — EVERY PHASE MUST RUN AS A CLOSED LOOP

IMPORTANT:

Do NOT execute any phase as a one-shot task.

EVERY phase in this prompt must be executed as its own closed quality loop.

For each phase, always follow:

AUDIT
→ FINDINGS
→ DESIGN / PLAN
→ IMPLEMENT
→ TARGETED TEST
→ REAL / E2E VERIFICATION
→ CRITIQUE
→ GAP ANALYSIS
→ FIX
→ RETEST
→ FULL RELEVANT SUITE
→ REPEAT

Do not move to the next phase merely because:
- code was written
- unit tests are green
- schema validates
- one happy-path example worked

A phase is complete only when:
1. its acceptance criteria are explicitly checked,
2. relevant edge cases are tested,
3. real or end-to-end behavior is verified where possible,
4. self-critique has been performed,
5. remaining gaps have been analyzed,
6. relevant gaps have been fixed,
7. the phase has been retested after the fixes.

If critique or testing finds any relevant gap:
DO NOT CONTINUE TO THE NEXT PHASE.

Instead:

FIX
→ RETEST
→ CRITIQUE AGAIN
→ REPEAT

Only proceed when the current phase is genuinely closed.

==================================================
MANDATORY PHASE REPORT
==================================================

At the end of EVERY phase, output:

PHASE <N> — <NAME>

1. AUDIT
What existed before?

2. FINDINGS
What problems / gaps / risks were found?

3. IMPLEMENTATION
What was changed?

4. TESTS
What targeted tests were run?

5. REAL / E2E VERIFICATION
What real flow was tested?

6. CRITIQUE
What is still weak, risky, incomplete, expensive, duplicated, or unclear?

7. GAP ANALYSIS
Which gaps are:
- BLOCKING
- IMPORTANT
- OPTIONAL

8. FIXES FROM CRITIQUE
What was fixed before closing the phase?

9. RETEST
What was rerun after the fixes?

10. ACCEPTANCE GATES
List every acceptance gate:
✓ passed
✗ failed

11. DECISION
Either:

PHASE CLOSED — proceed to next phase

or:

PHASE NOT CLOSED — repeat loop

==================================================
DO-NOT-STOP RULE
==================================================

Do not stop while any relevant:

- bug
- dead end
- missing path
- untested scenario
- broken acceptance gate
- unsafe fallback
- incomplete data flow
- unresolved provider failure
- missing provenance
- invalid content
- runtime AI dependency
- subject-specific gap

still exists.

Green tests alone are NEVER sufficient evidence of completion.

==================================================
REALITY CHECK RULE
==================================================

Whenever possible, each phase must include a real flow, not only mocks.

Examples:

catalog phase:
research → staged diff → admin review → approval

content generation phase:
request → agent pipeline → validation → READY_COMPLETE

runtime phase:
import → child session → wrong answer → intervention → correct → mastery

provider phase:
real provider call → structured output → validation → persistence

admin UI phase:
real browser flow → action → DB state → visible result

==================================================
CROSS-PHASE REGRESSION RULE
==================================================

After each major phase, verify that previously closed invariants still hold.

Examples:

- runtime AI calls remain 0
- serving_ok remains true
- queue isolation remains intact
- exam/personal evidence remains separated
- provider failures remain bounded
- generated content still passes deterministic validation

If a new phase breaks an older invariant:
the current phase is NOT closed.

==================================================
FINAL RULE
==================================================

Treat the whole project as:

PHASE 1 LOOP
→ PHASE 2 LOOP
→ PHASE 3 LOOP
→ ...

and inside every phase:

AUDIT
→ IMPLEMENT
→ TEST
→ REAL VERIFY
→ CRITIQUE
→ GAP ANALYSIS
→ FIX
→ RETEST
→ REPEAT

Only then move forward.



MASTER PHASE — KARO COMPLETE CURRICULUM FACTORY
CATALOG → COMPLETE LEARNING PROGRAM → DETERMINISTIC KARO RUNTIME

THIS IS A MAJOR PRODUCT PHASE.

Do not treat this as “generate lessons”.

The purpose of karo-curriculum-team is:

For every supported school topic, prepare enough validated curriculum,
teaching logic, tasks, explanations, misconceptions, visuals, rubrics,
prerequisites and deterministic decision rules so that Karo can later
teach a child from their actual level all the way to mastery WITHOUT
requiring an external LLM in the active child-learning loop.

The desired end state is:

OFFICIAL CURRICULUM
        ↓
CURRICULUM CATALOG
        ↓
TOPIC
        ↓
COMPLETE LEARNING PROGRAM
        ↓
VALIDATED / COMPILED CURRICULUM PACKAGE
        ↓
KARO DATABASE
        ↓
DETERMINISTIC TEACHING ENGINE
        ↓
CHILD
        ↓
diagnose
→ explain
→ guide
→ practice
→ detect misconception
→ prerequisite detour
→ return
→ independent work
→ transfer
→ mastery
→ spaced review

NO LIVE LLM REQUIRED.

============================================================
GLOBAL DEVELOPMENT LOOP
============================================================

AUDIT
→ FINDINGS
→ DESIGN
→ IMPLEMENT MINIMAL VERTICAL SLICE
→ GENERATE REAL CURRICULUM
→ VALIDATE
→ DOMAIN CHECK
→ COMPILE LEARNING JOURNEY
→ STATIC DEAD-END CHECK
→ ADVERSARIAL LEARNER SIMULATION
→ IMPORT INTO KARO
→ ACTUALLY USE IN KARO
→ CRITIQUE
→ GAP ANALYSIS
→ FIX
→ RETEST
→ FULL SUITES
→ REPEAT

DO NOT STOP because tests are green.

DO NOT STOP while any relevant:

- missing learning path
- unsupported child state
- dead end
- weak prerequisite route
- incomplete answer contract
- missing clarification
- missing misconception repair
- invalid visual
- unsupported difficulty level
- untested subject family
- runtime AI dependency
- catalog ambiguity
- unsafe bulk-generation path
- unvalidated curriculum artifact

still exists.

============================================================
PART 0 — FIRST AUDIT THE EXISTING SYSTEM
============================================================

Before changing architecture, audit the entire current
karo-curriculum-team and relevant Karo integration.

Inventory:

- existing agents
- prompt roles
- lesson_draft contract
- lesson_exports
- topic_requests
- concept graph
- prerequisites
- misconceptions
- explanations
- tasks
- templates / vorlage DSL
- answer types
- validators
- concept rubrics
- visual component registry
- generated images
- inspector
- learner simulation
- provider abstraction
- Devin provider
- OpenRouter code if any
- admin UI
- database tables
- generation jobs
- job provenance
- curriculum imports in Karo
- deterministic teaching engine
- runtime state transitions
- mastery rules
- repetition
- exam usage
- personal-learning usage

For every proposed component below classify:

KEEP
EXTEND
SPLIT
MERGE
REPLACE
NOT NEEDED

Do not create parallel duplicate architecture.

============================================================
PART 1 — DEFINE THE REAL PRODUCT CONTRACT
============================================================

A curriculum topic is NOT complete because:

- it has an explanation
- it has five questions
- the JSON validates
- the inspector says PASS

A curriculum topic is complete only if Karo can use it
to conduct an entire deterministic learning journey.

Define first-class concept:

COMPLETE_TOPIC_PACKAGE

A released COMPLETE_TOPIC_PACKAGE must contain:

1. curriculum alignment
2. concept identity
3. target competencies
4. prerequisite graph
5. competency ladder
6. diagnostic probes
7. misconception model
8. teaching strategies
9. explanation variants
10. worked examples
11. guided practice
12. independent practice
13. transfer practice
14. mastery checks
15. spaced-review material
16. prerequisite-detour material
17. clarification material
18. exam-practice material
19. deterministic answer contracts
20. task templates / variant generation
21. hints / scaffold ladders
22. visual learning assets
23. optional illustrative images
24. accessibility text
25. deterministic transition mappings
26. quality evidence
27. coverage manifest
28. provenance/versioning

If an item is pedagogically not applicable,
store explicit NOT_APPLICABLE + reason.

Never silently omit it.

============================================================
PART 2 — ADMIN CURRICULUM FACTORY
============================================================

Build a first-class Curriculum Factory admin UI.

The admin must be able to choose:

CURRICULUM / REGION
SCHOOL TYPE
GRADE
SUBJECT
TOPIC(S)

Primary initial main-subject matrix:

Grades 1–2:
- Deutsch
- Mathematik
- Sachunterricht

Grades 3–4:
- Deutsch
- Mathematik
- Englisch
- Sachunterricht

Grades 5–6:
- Deutsch
- Mathematik
- Englisch
- Naturwissenschaften / supported subject decomposition

Grades 7–10:
- Deutsch
- Mathematik
- Englisch
- Biologie
- Physik
- Chemie

Grades 11–13:
- Deutsch
- Mathematik
- Englisch
- Biologie
- Physik
- Chemie

This matrix is configuration / catalog seed,
NOT a hard architectural limitation.

Architecture must support additional subjects later.

============================================================
PART 3 — ADMIN SELECTION SEMANTICS
============================================================

CASE A:

Admin selects:

Grade 7

Meaning:

all enabled main subjects
→ all approved topics
→ complete missing/outdated curriculum packages

CASE B:

Grade 7 + Biology

Meaning:

all approved Biology topics in Grade 7

CASE C:

Grade 7 + Biology + one topic

Meaning:

complete exactly that topic

CASE D:

Grade 7 + multiple subjects

Meaning:

all approved topics in exactly those subjects

CASE E:

multiple specific topics

Meaning:

only those topics

============================================================
PART 4 — TWO SEPARATE ADMIN ACTIONS
============================================================

Never combine discovery and expensive generation into one blind button.

Admin actions:

A.
THEMENKATALOG ERSTELLEN / AKTUALISIEREN

B.
LERNPROGRAMME ERSTELLEN

First establish what should exist.

Then generate it.

============================================================
PART 5 — CURRICULUM CATALOG AGENT
============================================================

Create logical role:

CURRICULUM_CATALOG_RESEARCHER

Its job is to answer:

For this curriculum framework,
school type,
grade,
subject:

WHAT SHOULD BE TAUGHT?

It does NOT create lessons.

It researches and structures curriculum coverage.

============================================================
PART 6 — CATALOG RESEARCH RULES
============================================================

Prefer authoritative sources:

1. official education authority
2. official curriculum documents
3. official competency standards
4. official examination frameworks where relevant
5. trusted educational sources only as secondary support

Never create an “official” topic from model memory alone.

Every discovered item needs provenance.

============================================================
PART 7 — CATALOG OUTPUT HIERARCHY
============================================================

Generate:

SUBJECT
  ↓
DOMAIN / THEMENBEREICH
  ↓
TOPIC
  ↓
SUBTOPIC
  ↓
COMPETENCY
  ↓
ATOMIC CONCEPT

Do not flatten everything into one topic list.

Example structure only:

Mathematik
└── Zahlen und Operationen
    └── Brüche
        ├── Bruch als Anteil
        ├── Brüche vergleichen
        ├── erweitern
        ├── kürzen
        └── ...

Actual topics must come from researched curriculum,
not from this example.

============================================================
PART 8 — CATALOG PROVENANCE
============================================================

Persist:

framework
country
region
school_type
grade
subject
source
source_version
source_reference
retrieved_at
agent_role
provider
model
prompt_version
confidence

============================================================
PART 9 — CATALOG STAGING
============================================================

Catalog discovery NEVER directly mutates approved production catalog.

Flow:

research
→ normalize
→ compare existing
→ staged_change_set
→ admin review
→ approve / edit / reject
→ active catalog

============================================================
PART 10 — CATALOG DIFF
============================================================

Support changes:

ADD
RENAME
UPDATE
MOVE
SPLIT
MERGE
DEPRECATE
UNCHANGED

Never silently delete.

============================================================
PART 11 — MANUAL ADMIN CONTROL
============================================================

Admin can:

- manually add topic
- edit topic
- rename
- change parent
- reorder
- deactivate
- restore
- merge
- split

Track provenance:

manual
agent_research
import

============================================================
PART 12 — CATALOG UPDATE BUTTON
============================================================

Admin:

“THEMENLISTE MIT AGENT AKTUALISIEREN”

can target:

one grade
one grade + subject
multiple subjects
whole configured curriculum

Display staged diff before approval.

============================================================
PART 13 — AFTER TOPIC APPROVAL: TOPIC COMPILATION
============================================================

An approved topic is input to the Curriculum Factory.

The system now creates a:

COMPLETE LEARNING PROGRAM

not a simple lesson.

============================================================
PART 14 — AGENT / ROLE ARCHITECTURE
============================================================

Use logical roles, NOT an uncontrolled agent swarm.

Target roles:

1. CURRICULUM_CATALOG_RESEARCHER

2. COMPETENCY_ARCHITECT

3. LEARNING_JOURNEY_ARCHITECT

4. SUBJECT_EXPERT

5. MISCONCEPTION_ANALYST

6. DIDACTIC_DESIGNER

7. EXPLANATION_WRITER

8. ASSESSMENT_DESIGNER

9. TASK_TEMPLATE_ENGINEER

10. RUBRIC_AND_VALIDATOR_ENGINEER

11. VISUAL_LEARNING_DESIGNER

12. IMAGE_PROMPT_DESIGNER

13. VISUAL_INSPECTOR

14. RETENTION_AND_EXAM_DESIGNER

15. ADVERSARIAL_LEARNER_SIMULATOR

16. CURRICULUM_CRITIC

17. COMPLETENESS_CONTROLLER

Some roles may share implementation infrastructure.

Do not turn every role into a separate service.

============================================================
PART 15 — MODEL TIERS
============================================================

Core domain references CAPABILITIES, not model slugs.

Define:

reasoning_xhigh
reasoning_high
reasoning_balanced
writing_high
high_volume
multimodal_high
image_generation

Provider config maps role → capability → model.

No OpenRouter model name in curriculum domain logic.

============================================================
PART 16 — INITIAL OPENROUTER MODEL BASELINE
============================================================

Use this only as initial benchmark configuration,
NOT permanent truth.

Current suggested baseline:

CURRICULUM_CATALOG_RESEARCHER
→ reasoning_high
→ GPT-5.6 Sol + web/search tools

COMPETENCY_ARCHITECT
→ reasoning_high
→ GPT-5.6 Sol

LEARNING_JOURNEY_ARCHITECT
→ reasoning_high / xhigh
→ GPT-5.6 Sol
→ Sol Pro allowed for hard repair/final cases

SUBJECT_EXPERT
→ reasoning_high
→ GPT-5.6 Sol

DIDACTIC_DESIGNER
→ writing_high
→ Claude Sonnet 5.5

EXPLANATION_WRITER
→ writing_high
→ Claude Sonnet 5.5

MISCONCEPTION_ANALYST
→ reasoning_balanced
→ GPT-5.6 Terra

ASSESSMENT_DESIGNER
→ reasoning_balanced
→ GPT-5.6 Terra

TASK_TEMPLATE_ENGINEER
→ reasoning_high
→ GPT-5.6 Sol

RUBRIC_AND_VALIDATOR_ENGINEER
→ reasoning_high
→ GPT-5.6 Sol

RETENTION_AND_EXAM_DESIGNER
→ reasoning_balanced
→ GPT-5.6 Terra

VISUAL_LEARNING_DESIGNER
→ reasoning_balanced / multimodal
→ Terra or Sonnet

VISUAL_INSPECTOR
→ multimodal_high
→ strong configured vision-capable model

ADVERSARIAL_LEARNER_SIMULATOR
→ high_volume
→ GPT-5.6 Luna

CURRICULUM_CRITIC
→ reasoning_high
→ use a different model family than primary generator where useful

COMPLETENESS_CONTROLLER
→ reasoning_xhigh
→ GPT-5.6 Sol / Sol Pro

IMAGE GENERATION
→ image_generation capability
→ configured OpenRouter image model

Benchmark before locking role assignments.

============================================================
PART 17 — TOKEN / POWER POLICY
============================================================

DO NOT give every role the whole topic package.

Each role receives only necessary context.

Suggested initial output budgets:

catalog researcher:
8k–16k

competency architect:
10k–18k

learning journey architect:
10k–18k

subject expert:
4k–10k

misconception analyst:
6k–12k

didactic designer:
8k–16k

explanation writer:
8k–16k

assessment designer:
chunked, max 12k–20k per level/role batch

template engineer:
8k–16k

rubric engineer:
8k–16k

visual designer:
4k–8k

learner simulator:
3k–6k per simulation batch

critic:
6k–12k

completeness controller:
6k–12k

Do not treat these as hard constants.
Make configurable.

Measure actual:

tokens
cost
latency
first-pass success
repair count
quality outcome.

============================================================
PART 18 — STRUCTURED OUTPUT EVERYWHERE POSSIBLE
============================================================

Every logical role gets:

ROLE
INPUT CONTRACT
NON-RESPONSIBILITIES
OUTPUT JSON SCHEMA
QUALITY REQUIREMENTS
FAIL CONDITIONS

Prefer native structured output.

No free-form prose between pipeline stages.

============================================================
PART 19 — COMPETENCY ARCHITECT
============================================================

For every topic:

define exact target competency.

Decompose into atomic competencies.

Build concept structure.

Identify:

- necessary prerequisite
- useful prerequisite
- parallel concept
- extension concept

Create Level 0..N.

IMPORTANT:

Level 0 means:

lowest meaningful prerequisite for THIS concept.

It does NOT mean “Grade 1”.

============================================================
PART 20 — LEVEL LADDER
============================================================

For every level store:

level_id
goal
required knowledge
observable evidence
allowed task types
typical misconceptions
entry criteria
exit criteria
next level
fallback level/prerequisite

The ladder may have different lengths per topic.

Do not force the same number of levels.

============================================================
PART 21 — RECURSIVE PREREQUISITES
============================================================

Prerequisites may themselves have prerequisites.

Example structure:

target
→ prerequisite A
→ prerequisite B
→ prerequisite C

Karo must be able to descend until meaningful foundation,
then rebuild upward.

Detect cycles.

============================================================
PART 22 — LEARNING JOURNEY ARCHITECT
============================================================

This role is CRITICAL.

Its job is not to write material.

Its job is to design the complete deterministic teaching journey.

Input:

competency architecture
prerequisites
levels
misconceptions

Output:

states
outcomes
actions
fallbacks
return paths
mastery paths

============================================================
PART 23 — DETERMINISTIC JOURNEY CONTRACT
============================================================

For each relevant state define behavior for:

CORRECT
PARTIAL
INCORRECT
MISCONCEPTION
UNKNOWN
REPEATED_WRONG
REPEATED_UNKNOWN
MASTERED
PREREQUISITE_FAILED
PREREQUISITE_MASTERED

Runtime does not ask LLM what to do.

Curriculum provides policy.

============================================================
PART 24 — EXAMPLE POLICY SHAPE
============================================================

Concept / Level / Role / State

Outcome:
INCORRECT

Possible ordered actions:

1. targeted hint
2. smaller guided step
3. worked example
4. simpler parallel task
5. prerequisite diagnostic
6. prerequisite detour

Never:

automatic topic abandonment.

============================================================
PART 25 — CHILD STOP VS SYSTEM STOP
============================================================

System does not give up.

Only child may choose:

pause
enough for today
next topic

Topic remains resumable.

Human help can be offered,
but must not be terminal architecture.

============================================================
PART 26 — RETURN FROM PREREQUISITE
============================================================

Every prerequisite detour must contain explicit:

target_before_detour
prerequisite_path
return_condition
return_target
resume_level

Dead-end return paths are forbidden.

============================================================
PART 27 — SUBJECT EXPERT
============================================================

Create subject-specialized policies for:

Mathematik
Deutsch
Englisch
Biologie
Physik
Chemie
Sachunterricht / Naturwissenschaften where configured

Architecture extensible.

============================================================
PART 28 — SUBJECT VALIDATION
============================================================

Mathematics:

- recompute answers
- symbolic equivalence
- numeric constraints
- equation validity
- template solvability

Physics:

- values
- formulas
- units
- dimensional consistency
- conceptual explanations

Chemistry:

- formulas
- reactions
- stoichiometry when relevant
- conservation
- conceptual correctness

German:

- grammar
- orthography
- linguistic concepts
- acceptable variants
- meaning

English:

- grammar
- tense
- vocabulary context
- accepted variants
- semantics

Biology:

- factual correctness
- process relationships
- terminology
- misconception accuracy

============================================================
PART 29 — MISCONCEPTION MODEL
============================================================

For every meaningful concept identify real plausible learner misconceptions.

Not random wrong answers.

For each:

misconception_id
description
likely cause
observable answer patterns
disambiguating probe
repair explanation
guided repair
independent check
resolution evidence

============================================================
PART 30 — ERROR TYPE DISTINCTION
============================================================

Distinguish:

CARELESS
PROCEDURAL
CONCEPTUAL_MISCONCEPTION
PREREQUISITE_GAP
LANGUAGE_MISUNDERSTANDING
PARTIAL_KNOWLEDGE
UNKNOWN

Do not invent diagnosis when evidence insufficient.

============================================================
PART 31 — DIDACTIC DESIGNER
============================================================

For every level create teaching strategy:

HOOK
EXPLANATION
WORKED EXAMPLE
GUIDED PRACTICE
INDEPENDENT PRACTICE
TRANSFER

But adapt per subject.

Do not force identical pedagogy everywhere.

============================================================
PART 32 — MULTIPLE EXPLANATION MODES
============================================================

A topic must not rely on one explanation.

Where useful produce:

- concise rule
- intuitive explanation
- concrete example
- worked example
- visual explanation
- analogy
- misconception-specific explanation

They must be pedagogically different,
not paraphrases.

============================================================
PART 33 — AGE WITHOUT BABYING
============================================================

Explanation language follows current competency level.

Tone follows learner age.

A Grade 8 child learning a Grade 4 prerequisite
must get simple content without infantile language.

============================================================
PART 34 — ASSESSMENT ROLES
============================================================

Support explicit task roles:

DIAGNOSTIC
MISCONCEPTION_PROBE
PREREQUISITE_PROBE
WORKED
GUIDED
SCAFFOLDED
INDEPENDENT
TRANSFER
MASTERY_CHECK
SPACED_REVIEW
EXAM_PRACTICE
EXAM_SIMULATION
CLARIFICATION

============================================================
PART 35 — DIAGNOSTIC MATERIAL
============================================================

Diagnostics must discriminate between plausible learner states.

Do not ask ten questions where two high-information questions suffice.

Use:

concept discrimination
misconception discrimination
prerequisite discrimination

============================================================
PART 36 — HINT LADDERS
============================================================

Each suitable task includes ordered help levels:

hint 1:
light cue

hint 2:
strategy cue

hint 3:
partial structure

hint 4:
worked step

then:
new guided problem

Do not immediately reveal complete answer.

============================================================
PART 37 — TASK DIFFICULTY
============================================================

Difficulty variation must include more than smaller/larger numbers.

Possible dimensions:

number of reasoning steps
abstraction
language complexity
representation
distractors
context transfer
required recall
combined concepts
scaffold amount

============================================================
PART 38 — TASK POOLS + DETERMINISTIC GENERATORS
============================================================

To minimize future curriculum calls,
do NOT store only finite static questions.

Where safe, generate validated task templates.

Use the existing / evolved vorlage DSL.

A template must contain:

parameter domains
constraints
solution function
validator
difficulty metadata
variant exclusions
visual dependencies
known misconceptions

============================================================
PART 39 — TEMPLATE SAFETY
============================================================

Before READY:

enumerate small spaces where possible.

sample large spaces.

Verify:

- solvability
- answer validity
- no division by zero
- no impossible conditions
- no ambiguous solution
- appropriate values
- correct difficulty

============================================================
PART 40 — LANGUAGE TASK GENERATION
============================================================

For languages, deterministic generation may use:

validated sentence banks
slot grammars
accepted variant sets
transformation rules
word-order templates
matching pools

Do not force numeric-template DSL onto language subjects.

============================================================
PART 41 — SCIENCE TASK GENERATION
============================================================

Use structured template families where possible:

value + unit
classification
cause/effect
labeling
sequence
matching
concept selection
experiment interpretation
formula substitution
structured explanation

============================================================
PART 42 — INITIAL COVERAGE POLICY
============================================================

Create configurable coverage requirements.

Do not hardcode arbitrary universal counts.

But begin with strong defaults approximately like:

PER CONCEPT/LEVEL where applicable:

diagnostic probes:
2–4

distinct explanation strategies:
3+

worked examples:
2+

guided tasks:
4+

independent static/tasks/templates:
enough for repeated attempts without obvious repetition

target effective variant capacity:
10–20+ where safe

transfer tasks:
3+

mastery checks:
3+

spaced review:
3+

For EACH important misconception:

diagnostic probe
repair explanation
guided repair
independent repair check

Adjust by subject and concept complexity.

============================================================
PART 43 — NO EXCESS CONTENT FOR TRIVIAL CONCEPTS
============================================================

Completeness ≠ useless volume.

Coverage Controller should allow:

lower counts

when concept genuinely needs less.

Require reason.

============================================================
PART 44 — ANSWER CONTRACT ENGINEERING
============================================================

Karo must evaluate without runtime LLM.

Prefer deterministic answer types:

numeric
integer
decimal
fraction
term
equation
unit_value
single_select
multi_select
ordering
matching
fill_blank
token_sequence
classification
diagram_label
structured_formula
concept_rubric

============================================================
PART 45 — FREE TEXT
============================================================

Use free text only when pedagogically useful.

For concept rubric define:

required_concepts
accepted_variants
optional_concepts
misconceptions
contradictions
partial_rules
unknown_rules
clarification_task

============================================================
PART 46 — UNKNOWN IS FIRST-CLASS
============================================================

If answer cannot be safely judged:

UNKNOWN

Never pretend INCORRECT.

Curriculum must provide deterministic clarification.

Example:

open answer unclear
→ targeted multi-select
→ ordering
→ classification
→ short structured response

============================================================
PART 47 — PARTIAL
============================================================

PARTIAL must identify what is missing.

Next teaching action targets the missing element.

Do not restart whole topic by default.

============================================================
PART 48 — MISCONCEPTION PRIORITY
============================================================

If answer contains superficially correct words
but clearly expresses a misconception:

MISCONCEPTION wins.

============================================================
PART 49 — RUBRIC VALIDATION
============================================================

Adversarial test:

synonyms
inflections
typos
negation
contradictions
substring collisions
irrelevant additions
correct + wrong statement
very short answer
long answer

============================================================
PART 50 — EXAM CONTENT
============================================================

Shared concepts, separate child evidence.

Curriculum package supplies:

exam-style practice
timed-practice-ready tasks
typical formulations
mixed-topic tasks
simulation tasks
core-competency prioritization

Karo exam planner decides scheduling.

Curriculum provides assets.

============================================================
PART 51 — SPACED REPETITION
============================================================

Curriculum provides:

review task pool
review variants
retention probes
transfer review

Karo decides when to schedule them.

============================================================
PART 52 — MASTERY
============================================================

Correct ≠ mastered.

Curriculum defines mastery evidence such as:

independent correctness
repetition across variants
transfer success
absence/resolution of key misconceptions

Do not require exact same mastery pattern for every subject.

============================================================
PART 53 — VISUAL LEARNING
============================================================

Every concept must explicitly classify visual need:

DETERMINISTIC_DIAGRAM
DATA_CHART
ILLUSTRATIVE_IMAGE
NO_VISUAL_NEEDED

Never add images for decoration.

============================================================
PART 54 — DETERMINISTIC DIAGRAMS
============================================================

Use structured components for precision-critical visuals.

Examples:

number line
fraction bars
coordinate plane
geometry
function graph
timeline
process flow
concept map
cell structure
force diagram
circuit
particle model

Prefer component registry.

============================================================
PART 55 — VISUAL SPEC
============================================================

Store:

visual_type
learning_goal
what_child_should_notice
structured_data
labels
interaction if any
accessibility_text
age_tone
fallback_text

============================================================
PART 56 — CHARTS
============================================================

Graphs based on quantitative data are generated from structured data.

Never let an image model invent a numerical chart.

============================================================
PART 57 — ILLUSTRATIVE IMAGES
============================================================

Use image generation only where free illustration adds pedagogical value.

Flow:

VISUAL_LEARNING_DESIGNER
→ IMAGE_PROMPT_DESIGNER
→ IMAGE MODEL
→ VISUAL_INSPECTOR
→ APPROVED ASSET

============================================================
PART 58 — IMAGE QA
============================================================

Inspector checks:

required elements
unexpected elements
scientific correctness
misleading relations
age appropriateness
confusing text
visual clarity
accessibility

Bad image never becomes READY.

============================================================
PART 59 — RETENTION + EXAM DESIGNER
============================================================

Create:

spaced-review sets
cumulative review
mixed practice
exam-style transfer
simulation-ready task sets

Do not duplicate Assessment Designer unnecessarily.

If audit proves role overlap,
merge roles.

============================================================
PART 60 — LEARNING JOURNEY COMPILER
============================================================

After materials exist,
compile curriculum into deterministic state/action rules.

This is central.

Input:

competency graph
levels
task roles
misconceptions
rubrics
prerequisites
fallbacks

Output:

compiled learning policy.

============================================================
PART 61 — COMPILED POLICY
============================================================

A policy should answer:

Current concept?
Current level?
Current role?
Evidence?
Known misconception?
Repeated failure count?
Unknown count?
Prerequisite state?

Given outcome:

what next?

No LLM call.

============================================================
PART 62 — DO NOT ENUMERATE EVERY CHILD
============================================================

Avoid combinatorial giant trees.

Use:

generic deterministic teaching state machine
+
topic-specific curriculum rules
+
misconception mappings
+
level/prerequisite metadata

Compile and validate the composition.

============================================================
PART 63 — STATIC DEAD-END CHECKER
============================================================

Implement deterministic graph/state analysis.

For all relevant reachable states:

there must be a next action unless:

MASTERED
or
CHILD_SELECTED_STOP

Detect:

missing action
cycle
unreachable mastery
prerequisite cycle
return-path loss
infinite help loop
unreachable content role

============================================================
PART 64 — ADVERSARIAL LEARNER SIMULATOR
============================================================

Simulate at least:

STRONG
AVERAGE
LARGE_GAP
TYPICAL_MISCONCEPTION
REPEATED_MISCONCEPTION
CARELESS
PARTIAL
UNKNOWN
CONTRADICTORY
INCONSISTENT

============================================================
PART 65 — SIMULATOR DOES NOT DEFINE TRUTH
============================================================

Simulator is critic/tester.

The deterministic engine remains source of runtime behavior.

Simulator searches for:

dead ends
bad routing
poor help
premature mastery
overtraining
incorrect level changes
broken prerequisite return
insufficient content variants

============================================================
PART 66 — COMPLETENESS CONTROLLER
============================================================

Create a dedicated:

COMPLETE_CURRICULUM_CONTROLLER

This is the final orchestration/coverage role the product needs.

Its responsibility:

not generation.

Its responsibility is to ask:

“Could Karo teach this topic from any reasonable starting state
all the way to mastery without needing new AI content?”

============================================================
PART 67 — COMPLETENESS MANIFEST
============================================================

For every topic generate machine-readable manifest:

catalog_alignment
competency_graph
levels
prerequisites
diagnostics
misconceptions
explanations
worked_examples
guided
independent
transfer
mastery
review
exam
clarifications
rubrics
templates
visuals
journey_policy
dead_end_check
simulations
validators
subject_review
critic_review

Each:

COMPLETE
PARTIAL
NOT_APPLICABLE
MISSING

============================================================
PART 68 — RELEASE GATE
============================================================

Topic cannot become READY_COMPLETE if:

any required manifest component = MISSING

or

dead_end_check fails

or

subject validation fails

or

deterministic validator coverage missing

or

critical simulation fails.

============================================================
PART 69 — PARTIAL SERVING
============================================================

Existing system may need PARTIAL packages.

Define explicit states:

CATALOG_ONLY
BUILDING
PARTIAL
READY_CORE
READY_COMPLETE
OUTDATED
REVIEW_REQUIRED
FAILED
BLOCKED

Do not pretend PARTIAL is complete.

============================================================
PART 70 — LOCAL REPAIR LOOPS
============================================================

Do not rebuild everything for one defect.

Examples:

rubric incomplete
→ Rubric Engineer
→ validator test
→ controller

bad visual
→ Visual Designer/Image pipeline
→ visual inspector
→ controller

weak misconception coverage
→ Misconception Analyst
→ repair tasks
→ simulator
→ controller

bad prerequisite
→ Competency Architect
→ Journey Architect
→ affected dependencies
→ controller

============================================================
PART 71 — CROSS-MODEL CRITIQUE
============================================================

Where economically justified:

Generator model A
→ Critic model B

Benchmark against self-review.

Keep only if measurable value.

============================================================
PART 72 — CURRICULUM CRITIC
============================================================

Search aggressively for:

factual errors
wrong solutions
weak pedagogy
missing prerequisite
bad misconception mapping
duplicate questions
rubric false positives
rubric false negatives
ambiguous tasks
bad difficulty
missing transfer
premature mastery
bad visuals
invalid templates
dead ends

============================================================
PART 73 — ADMIN UI: CATALOG VIEW
============================================================

Provide:

Curriculum
School type
Grade
Subject

Then:

current approved topics
staged topics
missing catalog
source freshness

Actions:

RESEARCH / UPDATE CATALOG
REVIEW CHANGES
MANUAL ADD
EDIT
DEACTIVATE

============================================================
PART 74 — ADMIN UI: FACTORY VIEW
============================================================

For selected scope show:

Topics total
READY_COMPLETE
READY_CORE
PARTIAL
MISSING
OUTDATED
FAILED
BLOCKED

============================================================
PART 75 — ADMIN UI: CLASS VIEW
============================================================

Example:

GRADE 7

Deutsch       18/23 complete
Mathematik    21/24
Englisch      17/20
Biologie       8/12
Physik         6/10
Chemie         4/9

Overall package coverage.

Buttons:

COMPLETE MISSING
COMPLETE MISSING + OUTDATED

============================================================
PART 76 — ADMIN UI: TOPIC DETAIL
============================================================

Show:

curriculum source
competencies
prerequisite graph
levels
misconceptions
teaching strategies
task coverage
rubric coverage
template capacity
visuals
journey policy
simulation results
completeness manifest
quality findings
provider/model provenance
versions

============================================================
PART 77 — ADMIN UI: BULK PREVIEW
============================================================

Before bulk generation:

Selected:
Grade 7

Subjects:
6

Topics:
...

Complete:
...

Missing:
...

Partial:
...

Outdated:
...

Estimated role calls:
...

Estimated provider tokens:
...

Estimated cost:
...

Then require confirmation.

============================================================
PART 78 — BULK JOB ORCHESTRATION
============================================================

Grade generation becomes:

bulk_job
→ subject/topic jobs
→ role-stage jobs

Do NOT send whole grade to one LLM.

============================================================
PART 79 — BOUNDED CONCURRENCY
============================================================

Respect:

OpenRouter quota
provider failures
cost budgets
daily budgets
role-specific concurrency

============================================================
PART 80 — RESUMABILITY
============================================================

Restart must resume incomplete stage.

Do not rerun approved completed stages unless invalidated.

============================================================
PART 81 — DEPENDENCY INVALIDATION
============================================================

If concept graph changes:

only invalidate affected:

journey policy
prerequisite tasks
dependent content

not unrelated images.

============================================================
PART 82 — CONTENT VERSIONING
============================================================

Every artifact stores:

topic_version
content_version
contract_version
prompt_version
agent_role
provider
model
git_sha
created_at
supersedes

============================================================
PART 83 — ADMIN REGENERATE MODES
============================================================

Support:

GENERATE MISSING
REPAIR INCOMPLETE
REGENERATE OUTDATED
REGENERATE SELECTED COMPONENT
FULL REBUILD

Default:
do not rebuild good content.

============================================================
PART 84 — OPENROUTER PROVIDER
============================================================

Implement as provider adapter.

Core remains provider-neutral.

Support:

structured output
reasoning effort
usage metadata
tokens
cost
timeouts
fallback
provider routing
classified failures

============================================================
PART 85 — DEVIN COEXISTENCE
============================================================

Do not remove Devin unless evidence supports removal.

Allow:

role → provider capability

Example:

normal curriculum generation:
OpenRouter

special long-running repair/research:
Devin

or vice versa.

Config controls it.

============================================================
PART 86 — IMAGE PROVIDER
============================================================

Use OpenRouter image API behind image abstraction.

Do not expose provider details in domain code.

============================================================
PART 87 — MODEL BENCHMARK HARNESS
============================================================

Create representative benchmark set.

Subjects:

Mathematik
Deutsch
Englisch
Biologie
Physik
Chemie

School ranges:

primary
lower secondary
upper secondary

Cases:

simple
complex
misconception-heavy
free text
numeric
visual
template
transfer
prerequisite chain

============================================================
PART 88 — BENCHMARK EACH ROLE
============================================================

Measure:

schema success
factual correctness
didactic quality
validator correctness
misconception usefulness
completeness
repair rate
latency
input tokens
output tokens
cost

============================================================
PART 89 — DO NOT CHOOSE MODEL BY BRAND
============================================================

Initial model routing above is a starting hypothesis.

After benchmark:

upgrade weak roles
downgrade overpowered roles
use Luna where quality equal
use Terra where balanced
reserve Sol / Pro for high-value reasoning.

============================================================
PART 90 — PROMPT CACHING / SHARED CONTEXT
============================================================

Where provider supports it:

reuse stable:

contract
subject rules
component registry
curriculum schema

Do not resend giant duplicated blocks.

The previous Devin prompt-limit incident must never recur in another form.

============================================================
PART 91 — CONTEXT MINIMIZATION
============================================================

Agent sees only what it needs.

Example:

Image Inspector does not need entire prerequisite graph.

Rubric Engineer does not need every illustration.

Catalog Researcher does not need generated tasks.

============================================================
PART 92 — COST REPORT
============================================================

Admin and logs should support:

cost per role
cost per topic
cost per subject
cost per grade bulk job

No secrets.

============================================================
PART 93 — PRIMARY VERTICAL SLICE
============================================================

FIRST implement ONE full real slice.

Recommended:

Grade 7
Biology
one curriculum-researched topic

Flow:

catalog research
→ staged topic
→ admin approve
→ competency architecture
→ journey architecture
→ subject validation
→ misconception model
→ didactic design
→ explanations
→ assessments
→ templates
→ rubrics
→ visuals
→ retention/exam
→ journey compile
→ static dead-end checker
→ simulations
→ completeness controller
→ READY_COMPLETE
→ import to Karo
→ real child-flow simulation

============================================================
PART 94 — REAL CHILD FLOW TEST
============================================================

Run scenarios:

strong child

average child

large gap

misconception

repeated wrong

partial free text

unknown

contradictory answer

============================================================
PART 95 — LARGE GAP TEST
============================================================

Prove:

target concept
→ prerequisite
→ prerequisite of prerequisite
→ meaningful foundation
→ teach
→ mastery prerequisite
→ return
→ target
→ mastery

No AI calls.

============================================================
PART 96 — STRONG CHILD TEST
============================================================

Strong learner:

diagnostic
→ fast advancement
→ independent
→ transfer
→ mastery

Do not force unnecessary content.

============================================================
PART 97 — MISCONCEPTION TEST
============================================================

Known misconception:

detect
→ targeted explanation
→ guided repair
→ independent repair
→ return to target

============================================================
PART 98 — UNKNOWN TEST
============================================================

Free-text ambiguity:

UNKNOWN
→ deterministic clarification
→ classification
→ appropriate next step

============================================================
PART 99 — CONTENT EXHAUSTION TEST
============================================================

Simulate repeated failure attempts.

Ensure Karo does not:

run out of tasks
repeat exact same question constantly
request AI immediately

Use:

validated task templates
variant pools
alternative explanations
prerequisite path.

============================================================
PART 100 — SIX-SUBJECT EXPANSION
============================================================

After first complete slice works:

repeat loop for:

Mathematik
Deutsch
Englisch
Biologie
Physik
Chemie

Each requires a REAL vertical slice.

============================================================
PART 101 — SUBJECT-SPECIFIC CRITIQUE
============================================================

For every subject ask:

Does our generic schema distort this subject?

Do language tasks need different machinery?

Does science need diagrams?

Does Math need stronger generators?

Does Biology need richer concept rubrics?

Adapt without fragmenting architecture unnecessarily.

============================================================
PART 102 — FULL SUBJECT CANARY
============================================================

Then choose one grade+subject:

catalog all topics
→ approve
→ generate all missing COMPLETE packages

Validate:

fan-out
cost
resumability
coverage
quality.

============================================================
PART 103 — FULL GRADE DRY RUN
============================================================

Before generating entire grade:

Grade only

→ catalog scope
→ topic count
→ missing packages
→ estimated calls
→ estimated tokens
→ estimated cost

Do NOT immediately execute.

Admin confirms.

============================================================
PART 104 — FULL GRADE GENERATION
============================================================

Only after previous acceptance:

generate all missing/outdated topics for one controlled grade.

Bound concurrency.

Monitor.

============================================================
PART 105 — KARO RUNTIME HARD RULE
============================================================

After imported curriculum:

the following MUST produce ZERO external AI calls:

grading
partial classification where local rubric supports it
misconception routing
next action
level selection
mastery
prerequisite routing
repetition
clarification routing

============================================================
PART 106 — CURRICULUM REQUESTS AFTER COMPLETE PACKAGE
============================================================

A READY_COMPLETE package should drastically reduce runtime curriculum requests.

Measure:

content_request rate before
vs
after complete package.

============================================================
PART 107 — ALLOWED FUTURE REQUESTS
============================================================

Even complete curriculum may eventually need requests due to:

new curriculum version
uncovered rare edge
quality repair
new visual
new language
new subject
new accessibility need

But normal child mistakes should NOT trigger provider generation.

============================================================
PART 108 — COMPLETENESS METRIC
============================================================

For every topic calculate coverage, but do not reduce quality to one misleading percentage.

Show dimensions:

concept coverage
level coverage
misconception coverage
task-role coverage
validator coverage
visual coverage
journey coverage
exam coverage
review coverage

============================================================
PART 109 — STATIC QUALITY GATES
============================================================

READY_COMPLETE requires:

subject correctness PASS

validator PASS

template PASS

dead-end PASS

prerequisite cycles PASS

return paths PASS

rubric adversarial PASS

visual QA PASS where applicable

learner simulation PASS

completeness manifest PASS

============================================================
PART 110 — TRIPLE REVIEW
============================================================

Every COMPLETE package undergoes three independent review layers:

REVIEW 1:
domain / factual

REVIEW 2:
pedagogy / learning journey

REVIEW 3:
deterministic completeness / runtime coverage

Failures go into local repair loops.

============================================================
PART 111 — CRITIQUE AFTER EVERY ITERATION
============================================================

Explicitly answer:

What did we miss?

Where can a child still reach a dead end?

Where could runtime ask curriculum unnecessarily?

Which level lacks enough material?

Which misconception lacks repair content?

Which rubric is too strict?

Which rubric is too broad?

Which task generator produces bad variants?

Which visual adds no learning value?

Which agent duplicated another?

Which model is too expensive for its gain?

Which cheap model performed equally well?

Which role needs stronger reasoning?

============================================================
PART 112 — GAP ANALYSIS
============================================================

Every critique finding becomes:

FIX NOW
BACKLOG
NOT A PROBLEM

Relevant learning/runtime gaps cannot be left as documentation only.

============================================================
PART 113 — FULL TEST LOOP
============================================================

After every relevant change:

role unit tests
contract tests
validator tests
template tests
state-graph tests
dead-end tests
agent integration
provider integration
Karo import
Karo actual teaching journey
browser admin E2E
kcteam full suite
Karo full suite

============================================================
PART 114 — DO-NOT-STOP CONDITIONS
============================================================

Do NOT declare this phase complete while:

- catalog agent cannot research arbitrary grade+subject
- source provenance missing
- admin cannot review catalog diff
- topics cannot be manually added/edited
- complete package schema missing
- competency levels incomplete
- prerequisite descent incomplete
- return path incomplete
- misconception repair incomplete
- deterministic validators missing
- UNKNOWN has no clarification
- PARTIAL has no targeted remediation
- repeated wrong can exhaust material
- deterministic task templates not validated
- important visuals unvalidated
- dead-end checker finds reachable dead end
- simulator finds unresolved critical child profile
- one of six primary subject families lacks vertical slice
- Karo runtime invokes LLM
- complete package still frequently requests curriculum for normal mistakes
- bulk generation cannot resume safely
- admin can accidentally trigger huge generation without preview
- model/token/cost metrics unavailable

============================================================
PART 115 — FINAL ACCEPTANCE
============================================================

This phase is complete only when:

✓ Admin selects curriculum / grade / subject / topic

✓ Grade-only selection expands correctly

✓ Catalog Research Agent works

✓ authoritative sources/provenance retained

✓ staged diff works

✓ admin approve/reject/edit works

✓ manual topic add works

✓ COMPLETE_TOPIC_PACKAGE implemented

✓ Concept hierarchy works

✓ Level 0..N works

✓ recursive prerequisites work

✓ return-to-target works

✓ diagnostic system complete

✓ misconception system complete

✓ multiple explanation strategies complete

✓ worked/guided/independent/transfer complete

✓ deterministic task template system complete

✓ mastery assets complete

✓ review assets complete

✓ exam assets complete

✓ concept rubrics complete

✓ clarification assets complete

✓ deterministic visuals complete

✓ image generation + image QA works

✓ data charts structured

✓ learning journey compiled

✓ static dead-end checker passes

✓ strong learner passes

✓ average learner passes

✓ large-gap learner passes

✓ misconception learner passes

✓ repeated-error learner passes

✓ PARTIAL passes

✓ UNKNOWN passes

✓ contradiction passes

✓ six primary subjects have real vertical slice

✓ single-topic generation works

✓ full-subject generation works

✓ full-grade dry-run works

✓ generation resumable

✓ provenance complete

✓ cost/token accounting complete

✓ provider-neutral architecture

✓ OpenRouter adapter production-ready

✓ runtime AI calls = 0

✓ Karo full suite green

✓ kcteam full suite green

✓ browser E2E green

============================================================
FINAL PRODUCT PRINCIPLE
============================================================

The Curriculum Factory is not a question generator.

It is not a lesson writer.

It is not an LLM proxy.

It is the compiler that transforms:

official curriculum
+
subject knowledge
+
pedagogy
+
misconceptions
+
assessment
+
visual learning
+
deterministic validation
+
learning-state logic

into a COMPLETE DETERMINISTIC LEARNING PROGRAM.

The desired child experience is:

“I don't understand.”

→ Karo already has another explanation.

“I still don't understand.”

→ Karo already has a smaller guided step.

“I made a typical mistake.”

→ Karo already knows that misconception.

“I cannot do the prerequisite.”

→ Karo already has that prerequisite path.

“I answer strangely.”

→ Karo already has a deterministic clarification.

“I need an easier level.”

→ Karo already has it.

“I understand now.”

→ Karo already has independent and transfer evidence.

“I need to review later.”

→ Karo already has review material.

“I have a class exam.”

→ Karo already has exam-practice assets.

The external LLM should have done the expensive thinking BEFORE
the child arrives.

The child-facing runtime should mainly execute a validated,
deterministic learning program.

============================================================
FINAL LOOP
============================================================

AUDIT
→ BUILD
→ GENERATE
→ COMPILE
→ VALIDATE
→ SIMULATE
→ ACTUALLY USE
→ CRITIQUE
→ FIND GAPS
→ REPAIR
→ RETEST
→ REPEAT

Never stop while a meaningful learning path remains incomplete.