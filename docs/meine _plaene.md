# KARO — FINAL CANONICAL IMPLEMENTATION PROMPT
## Ziele, Planung, Zeiterfassung, Fokus, Nachholen, Statistik und Schatzkiste

You are working inside the existing **Karo** repository.

This document is the **single source of truth** for the planning/goals feature.
It supersedes all earlier conversations, mockups, variants, and partially conflicting screenshots.

Use the attached Karo screenshots as **visual references** for:
- layout,
- spacing,
- navigation,
- cards,
- progress bars,
- typography,
- the fox mascot,
- child-friendly wording,
- the pages **Heute / Woche / Monat / Ziele**,
- the goal wizard,
- goal detail/history,
- and the archive concept.

If any screenshot conflicts with this specification, **this specification wins**.

---

# 1. NON-NEGOTIABLE PRODUCT DECISIONS

## 1.1 Time is the only progress unit

Do **not** calculate progress from:
- words learned,
- exercises solved,
- pages read,
- grades,
- repetitions,
- content counts,
- or subject-specific units.

A goal may have a descriptive sentence such as:

> „Ich möchte besser in Englisch werden.“

But all measurable progress is based on **time**.

The system measures:
1. planned minutes,
2. actual minutes,
3. plan fulfilment in percent,
4. total goal progress in percent,
5. concentration/focus in percent,
6. focused minutes derived from actual minutes × focus,
7. daily, weekly, monthly, and whole-goal statistics.

---

# 2. CORE UX PRINCIPLE

Keep the child experience extremely simple.

The child should never have to understand the underlying formulas.

The main flow is:

```text
Goal created
    ↓
Karo schedules planned sessions
    ↓
Child sees today's planned session
    ↓
Child works on it
    ↓
Child presses "Erledigt"
    ↓
One small completion panel opens
    ↓
Child adjusts ACTUAL TIME with a 0–60 minute slider
    ↓
Child records concentration/focus
    ↓
Save
    ↓
All statistics update automatically
```

The child must be allowed to enter **less or more time than planned**.

Example:

```text
Planned: 20 min
Actual: 14 min  → 70 %
Actual: 20 min  → 100 %
Actual: 26 min  → 130 %
```

Do not force actual time to equal planned time.

---

# 3. NAVIGATION

The child navigation must contain:

```text
Heute | Woche | Monat | Ziele | Schatzkiste
```

Keep the existing Karo header, user avatar, fox mascot, visual language, and child-friendly style.

Do not redesign unrelated parts of Karo.

---

# 4. GOAL CREATION — FINAL FLOW

The old content-based target step such as:

```text
60 Wörter
100 Aufgaben
10 Stunden lesen
```

must NOT be used as the progress basis.

Use a short goal wizard.

## Step 1 — Goal sentence

Question:

```text
Was möchtest du schaffen?
```

Example:

```text
Ich möchte besser in Englisch werden.
```

Store this as descriptive text only.

Required:
- short text field,
- child-friendly helper text,
- Continue button.

---

## Step 2 — Duration

Question:

```text
Wie lange möchtest du daran arbeiten?
```

Options:

```text
1 Woche
2 Wochen
1 Monat
3 Monate
Eigenes Datum
```

The child can change this later.

---

## Step 3 — Days

Question:

```text
An welchen Tagen möchtest du daran arbeiten?
```

Show seven simple weekday buttons:

```text
Mo  Di  Mi  Do  Fr  Sa  So
```

Multiple selection is allowed.

Immediately show a simple confirmation such as:

```text
Du hast 3 Tage pro Woche ausgewählt.
```

---

## Step 4 — Planned minutes per session

Question:

```text
Wie lange möchtest du an einem Lerntag daran arbeiten?
```

Quick options:

```text
10 Minuten
15 Minuten
20 Minuten
30 Minuten
Eigene Zeit
```

Custom time:
- minimum 1 minute,
- maximum 60 minutes.

This value is the **planned time**, not the actual time.

---

## Step 5 — Plan summary

Show:

```text
Dein Plan ist fertig!
```

Display only the important information:

```text
Ziel
Zeitraum
Lerntage
Geplante Zeit pro Lerntag
Anzahl geplanter Einheiten
Geplante Gesamtzeit
```

Example:

```text
Ziel: Ich möchte besser in Englisch werden.
Dauer: 4 Wochen
Lerntage: Mo · Mi · Fr
Zeit pro Lerntag: 20 Minuten
Einheiten: 12
Geplante Gesamtzeit: 240 Minuten
```

Primary CTA:

```text
Plan starten
```

Do not add another measurable target such as “60 Wörter”.

---

# 5. DATA MODEL

First inspect the existing repository and reuse existing user, child, authentication, role, and database structures.

Do not create duplicate user/child models.

Implement or adapt the domain so that the following concepts exist.

## Goal

Required logical fields:

```text
id
child_id / learner_id
title or goal_statement
start_date
end_date
planned_minutes_per_session
selected_weekdays
status
created_at
updated_at
completed_at
archived_at
```

Statuses:

```text
active
paused
completed
archived
```

Do not erase historical statistics when a goal is edited.

---

## PlannedSession

Each planned occurrence must be traceable.

Logical fields:

```text
id
goal_id
scheduled_date
planned_minutes
status
created_at
```

Statuses should cover:

```text
planned
completed
missed
made_up
cancelled
```

Use the repository's conventions and naming if equivalent models already exist.

---

## SessionCompletion

Logical fields:

```text
id
planned_session_id
actual_minutes
focus_percent
completed_at
is_makeup
```

Validation:

```text
actual_minutes: 0..60
focus_percent: 0..100
```

Store raw values.

Do not store only calculated percentages.

---

# 6. IMPORTANT RULE FOR PLAN CHANGES

Editing a goal must **not rewrite history**.

Example:

```text
Weeks 1–2:
Mo / Mi / Fr
20 min

From week 3:
Tue / Thu
30 min
```

Past planned sessions and past completion data must remain unchanged.

Apply edits only to future sessions.

Use either:
- immutable planned-session rows,
- plan versions with effective dates,
- or another clean repository-consistent solution.

But historical reports must remain reproducible.

---

# 7. COMPLETING A SESSION — MOST IMPORTANT INTERACTION

When the child presses:

```text
Erledigt
```

open a compact completion panel/modal.

## 7.1 Actual-time slider

Show:

```text
Wie lange hast du heute wirklich daran gearbeitet?
```

Slider:

```text
0 ───────────────────────── 60 Minuten
```

Requirements:
- draggable left/right,
- value visible continuously,
- integer minutes,
- initial value = planned minutes,
- child can choose less or more than planned,
- maximum 60.

Example:

```text
Geplant: 20 Min
Tatsächlich: 27 Min
Heute: 135 %
```

---

## 7.2 Focus input

On the same completion panel, ask:

```text
Wie konzentriert warst du?
```

Keep it simple.

Use one child-friendly slider:

```text
0 % ───────────────────────── 100 %
```

Recommended:
- increments of 10%,
- default may be the last used value or 80%,
- show the exact selected percentage,
- optional helper labels such as:
  `wenig` / `okay` / `sehr konzentriert`.

Do not turn this into a questionnaire.

---

## 7.3 Save

Button:

```text
Speichern
```

After saving:
- mark session completed,
- persist actual minutes,
- persist focus percent,
- recalculate all aggregates,
- update Heute,
- update Woche,
- update Monat,
- update Ziele,
- update goal detail/history.

No LLM call is required for these calculations.

---

# 8. CALCULATION RULES

Create one centralized calculation/statistics service.

Do not duplicate formulas in templates or routers.

## 8.1 Daily plan fulfilment

For a planned session:

```text
daily_percent = actual_minutes / planned_minutes × 100
```

Examples:

```text
20 planned / 10 actual = 50 %
20 planned / 20 actual = 100 %
20 planned / 24 actual = 120 %
```

Values above 100% are valid.

---

## 8.2 “Bis heute” / plan adherence

For a goal:

```text
planned_to_date =
sum(planned_minutes of sessions due up to the selected date)

actual_for_due_sessions =
sum(actual_minutes credited to those due sessions)

plan_adherence_percent =
actual_for_due_sessions / planned_to_date × 100
```

This value may exceed 100%.

Example:

```text
80 min planned so far
85 min actually done
= 106 %
```

UI wording:

```text
Bis heute
106 %
Du bist 6 % vor deinem Plan.
```

---

## 8.3 Whole-goal progress

```text
planned_goal_minutes =
sum(planned_minutes of all sessions in the goal)

actual_goal_minutes =
sum(actual_minutes of completed/made-up sessions)

goal_progress_percent =
actual_goal_minutes / planned_goal_minutes × 100
```

For the visual “Bis zum Ziel” bar:
- display maximum fill at 100%,
- numerical logic may retain the raw value,
- reaching >= 100% means the time target has been reached.

Do not mix this with “Bis heute”.

---

## 8.4 Focus

Use a time-weighted average:

```text
weighted_focus =
sum(actual_minutes × focus_percent)
/
sum(actual_minutes)
```

Example:

A 30-minute session should influence the average more than a 5-minute session.

Also calculate:

```text
focused_minutes =
actual_minutes × focus_percent / 100
```

For aggregates:

```text
total_focused_minutes =
sum(focused_minutes)
```

Display examples:

```text
Gearbeitet: 268 Min
Fokuszeit: 233 Min
Ø Konzentration: 87 %
```

---

## 8.5 Day / week / month

All reporting levels use the same base values:

```text
planned minutes
actual minutes
focused minutes
average focus
plan fulfilment percent
```

Aggregate by:
- day,
- ISO week,
- calendar month,
- complete goal.

Avoid separate contradictory formulas for each screen.

---

# 9. “HEUTE” PAGE

Use the attached “Heute” screenshot as visual inspiration.

Show:

## Header summary

Keep it simple:
- greeting,
- one small fox motivation card,
- “Bis heute” average across active goals,
- “Gesamt” average across active goals.

## Today's sessions

Each row/card should show:

```text
Goal name
planned minutes
status
Starten
Erledigt
```

After completion, show a clear completed state.

## Missed sessions

Add a small section:

```text
Noch offen
```

or:

```text
Von gestern noch offen
```

with:

```text
Jetzt nachholen
```

Do not make the screen visually busy.

---

# 10. NACHHOLEN

Nachholen is required.

A planned session that passes without completion becomes:

```text
missed
```

The child must be able to:

```text
Jetzt nachholen
```

or schedule it for another allowed day if the existing Karo UX supports this cleanly.

When a missed session is completed later:

```text
status = made_up
is_makeup = true
completed_at = real completion timestamp
```

Important:

- It must count only once.
- It must satisfy the original planned session.
- It must remain visible in history as “nachgeholt”.
- Never duplicate the planned minutes.

For reporting:
- plan adherence is tied to the original planned session,
- activity time can still be shown on the real day the work happened.

Keep the child-facing wording simple even if the backend keeps both dates.

---

# 11. “WOCHE” PAGE

Use the attached week screenshots as visual reference.

Show:

```text
Diese Woche
date range
weekday timeline
Wochenfortschritt
```

For each active goal show:
- planned minutes this week,
- actual minutes this week,
- fulfilment percent,
- average focus.

Also show:

```text
Erledigt
Offen
Nachholen
```

A missed session must be reachable directly from this page.

Do not show content-unit progress such as words or exercises.

---

# 12. “MONAT” PAGE

Use the attached month screenshots as visual reference.

Show:

```text
Mein Monat
month selector
Monatsfortschritt
```

For each active goal:
- actual / planned minutes,
- percent,
- average focus.

Show a weekly breakdown:

```text
Woche 1
Woche 2
Woche 3
Woche 4 / 5
```

Each week should use the same time-based formula.

The child must be able to understand:

```text
Bin ich im Plan?
Wie viel habe ich gearbeitet?
Wie konzentriert war ich?
```

without opening a complex report.

---

# 13. “ZIELE” PAGE

Use the attached “Alle Ziele – dein Fortschritt” screenshots as visual reference.

Each active goal card should contain:

```text
Goal title
Bis heute %
Bis zum Ziel %
planned-to-date minutes
actual-to-date minutes
total actual minutes
Ø concentration
next planned session
Starten
```

Keep only the most important values visible.

Do not overload the cards.

A goal detail page can contain the deeper history.

---

# 14. GOAL DETAIL PAGE

Use the attached detailed goal screenshots as visual reference.

The detail page should contain:

## Overview

```text
Goal title
period
schedule
planned minutes/session
Bis heute %
Bis zum Ziel %
total planned minutes
total actual minutes
focused minutes
Ø concentration
```

## Tabs

```text
Verlauf
Diagramm
Kalender
```

### Verlauf

Table columns:

```text
Datum
Geplant
Gemacht
Konzentration
Fortschritt
Status
```

Example:

```text
24.09. | 20 Min | 18 Min | 80 % | 90 % | Erledigt
```

### Diagramm

Keep the chart simple.

Show:
- planned minutes,
- actual minutes,
- focus percentage.

Do not introduce unrelated metrics.

### Kalender

Use simple status colors/icons:

```text
green  = reached / completed
yellow = partially completed
red    = missed
neutral = no plan
```

Also distinguish a made-up session clearly but gently.

---

# 15. GOAL OPTIONS

Goal menu:

```text
Ziel bearbeiten
Pausieren
Als erledigt markieren
In die Schatzkiste
Ziel löschen
```

Rules:

### Pause
- no new planned sessions while paused,
- history remains.

### Complete
- sets completed state,
- do not automatically delete or archive.

### Delete
- use confirmation,
- respect existing Karo deletion/data-retention conventions.

---

# 16. SCHATZKISTE

Add the new top-level tab:

```text
Schatzkiste
```

Purpose:

A child can archive a reached/completed goal and still see what was achieved.

A goal should not disappear when completed.

## Archive action

When a goal is completed or reaches the target, show:

```text
In die Schatzkiste
```

The child explicitly chooses to archive it.

Do not auto-archive immediately.

## Schatzkiste card

Show:

```text
Goal title
Abgeschlossen
Zeitraum
Gesamt gearbeitet
Geplante Gesamtzeit
Ø Konzentration
final plan adherence
completion date
```

Optional CTA:

```text
Noch einmal als neues Ziel
```

This creates a new goal from the old settings.

Do not reactivate the archived record itself.

Archived goals are read-only historical records.

---

# 17. EMPTY STATES

Provide simple empty states.

Examples:

## No goals

```text
Noch keine Ziele.
Starte jetzt dein erstes Ziel.
```

CTA:

```text
+ Neues Ziel
```

## No completed goals in Schatzkiste

```text
Deine Schatzkiste ist noch leer.
Erreichte Ziele findest du später hier.
```

Keep the fox illustration if the asset already exists.

---

# 18. VISUAL DESIGN RULES

Match the provided Karo references:

- white/light background,
- dark teal top navigation,
- green as primary success/action color,
- large rounded cards,
- clear spacing,
- simple progress bars,
- large readable numbers,
- minimal text,
- child-friendly language,
- fox mascot used for encouragement,
- no dense admin-dashboard feeling.

Do not blindly reproduce every screenshot.

The screenshots contain older content-unit ideas.
Use their **visual system**, not their outdated progress logic.

Responsive behavior must work at least for:
- desktop,
- tablet,
- reasonable mobile width.

---

# 19. MOTIVATIONAL COPY

Use short, non-judgmental copy.

Good examples:

```text
Weiter so!
Du bist gut im Plan.
Heute ein bisschen besser als gestern.
Jede Minute zählt.
Du hast heute schon 24 Minuten geschafft.
```

For missed work, avoid shame.

Use:

```text
Noch offen
Möchtest du es nachholen?
```

Do not use punishment language.

---

# 20. BACKEND ARCHITECTURE

Follow the architecture already used in Karo.

Keep:

```text
router/controller → service/domain logic → repository/database
```

Do not place calculation logic in templates.

Recommended service responsibilities:

```text
GoalService
ScheduleService
SessionCompletionService
ProgressCalculationService
StatisticsService
ArchiveService
```

Names may differ if the repository already has established patterns.

Prefer small functions that do one thing.

Add short comments/docstrings for non-obvious logic.

---

# 21. MIGRATIONS

If schema changes are required:

1. inspect the current database layer,
2. create proper migration(s),
3. preserve existing data,
4. make migrations reversible where the project convention supports it,
5. do not silently recreate the database.

If old goal records use content-based units, migrate them carefully or keep a backward-compatible read path.
Do not fabricate historical minute values that never existed.

---

# 22. ROUTES / ENDPOINTS

Use existing route conventions.

The implementation needs equivalent capabilities for:

```text
list active goals
create goal
goal wizard state
view goal
edit goal
pause goal
complete goal
archive goal
list Schatzkiste
start/open a planned session
mark session completed
save actual minutes + focus
list today
list week
list month
list missed sessions
make up missed session
```

Do not add an API framework if Karo already has one.

---

# 23. STEP-BY-STEP IMPLEMENTATION ORDER

Implement in this exact order and keep the app runnable after every step.

## Phase 0 — Repository audit

Before changing code:

1. inspect current auth and child/parent roles,
2. inspect existing goal/planning models,
3. inspect routes/templates,
4. inspect database/migrations,
5. inspect existing navigation,
6. inspect test patterns,
7. identify existing fox/image assets,
8. write a short implementation plan.

Do not start by rewriting the application.

---

## Phase 1 — Domain + database

Implement:
- goal time planning,
- planned sessions,
- session completions,
- focus,
- statuses,
- archive fields,
- safe migrations.

Add model/repository tests.

Stop and run tests.

---

## Phase 2 — Central progress calculations

Implement pure functions/services for:
- daily percent,
- planned-to-date,
- actual-to-date,
- whole-goal progress,
- focused minutes,
- weighted focus,
- week aggregates,
- month aggregates,
- overall averages.

These functions must be testable without HTTP.

Stop and run tests.

---

## Phase 3 — Goal creation wizard

Implement:
1. goal sentence,
2. duration,
3. weekdays,
4. planned minutes,
5. summary/start.

Generate future planned sessions.

Do not add content-unit targets.

Stop and run tests.

---

## Phase 4 — Heute page

Implement:
- today sessions,
- completed/open states,
- start action,
- “Erledigt” action,
- missed items,
- “Jetzt nachholen”.

Stop and test.

---

## Phase 5 — Completion panel

Implement:
- 0–60 minute slider,
- focus slider,
- save action,
- validation,
- recalculation,
- refresh-safe persistence.

This is a critical phase.

Stop and test thoroughly.

---

## Phase 6 — Woche

Implement:
- weekday timeline,
- planned vs actual minutes,
- progress percent,
- focus,
- completed/open/missed/made-up states,
- catch-up action.

Stop and test.

---

## Phase 7 — Monat

Implement:
- month navigation,
- monthly aggregates,
- per-goal summaries,
- weekly breakdown,
- focus.

Stop and test.

---

## Phase 8 — Ziele

Implement:
- active goal cards,
- “Bis heute”,
- “Bis zum Ziel”,
- worked time,
- average concentration,
- next session,
- goal options.

Stop and test.

---

## Phase 9 — Goal detail/history

Implement:
- overview,
- history table,
- simple chart,
- calendar,
- edit flow.

Stop and test.

---

## Phase 10 — Schatzkiste

Implement:
- archive action,
- Schatzkiste nav tab,
- archived goal list/detail,
- read-only historical stats,
- optional “Noch einmal als neues Ziel”.

Stop and test.

---

## Phase 11 — Full integration + regression

Run:
- unit tests,
- service tests,
- route tests,
- template/UI tests if present,
- migration tests,
- full existing Karo test suite.

Fix regressions before finalizing.

---

# 24. REQUIRED TEST CASES

At minimum test:

1. actual < planned,
2. actual = planned,
3. actual > planned,
4. 0 actual minutes,
5. 60 actual minutes,
6. focus = 0%,
7. focus = 100%,
8. weighted focus across multiple sessions,
9. several goals on one day,
10. missed session,
11. made-up session,
12. make-up does not double-count,
13. week boundary,
14. month boundary,
15. editing future schedule does not alter history,
16. pause/resume,
17. goal reaches 100% early,
18. plan adherence >100%,
19. archive keeps all history,
20. archived goal disappears from active goals,
21. empty states,
22. unauthorized child cannot access another child's goal,
23. existing parent/child authorization rules remain intact,
24. refresh does not lose entered/saved state.

---

# 25. DETERMINISTIC ACCEPTANCE EXAMPLE

Use this scenario in tests.

Goal:

```text
Ich möchte besser in Englisch werden.
Duration: 4 weeks
Days: Mo / Mi / Fr
Planned: 20 min per session
Total sessions: 12
Planned total: 240 min
```

Four completed sessions:

```text
Session 1: 24 min, focus 95%
Session 2: 18 min, focus 80%
Session 3: 23 min, focus 90%
Session 4: 20 min, focus 85%
```

Expected actual total:

```text
85 min
```

Expected weighted focus:

```text
(24×95 + 18×80 + 23×90 + 20×85) / 85
≈ 88.1 %
```

If 80 minutes were planned up to that point:

```text
Bis heute = 85 / 80 = 106.25 %
```

Rounded UI value:

```text
106 %
```

Whole-goal progress:

```text
85 / 240 ≈ 35.4 %
```

Rounded UI value:

```text
35 %
```

This example must pass through the same calculation service used by the UI.

---

# 26. DO NOT DO THESE THINGS

Do not:
- calculate progress from words/tasks/pages,
- create separate contradictory formulas per screen,
- overwrite past plan history after editing,
- auto-archive completed goals,
- shame the child for missed sessions,
- add unnecessary AI calls,
- add a complex questionnaire after each session,
- rebuild unrelated Karo modules,
- replace existing auth,
- duplicate child/user models,
- hide missed sessions,
- double-count catch-up work,
- hardcode screenshot example data into production,
- weaken existing security boundaries.

---

# 27. DEFINITION OF DONE

The feature is done only when the following complete loop works:

```text
Create time-based goal
        ↓
planned sessions appear
        ↓
today's session appears
        ↓
child completes it
        ↓
child chooses 0–60 actual minutes
        ↓
child records focus %
        ↓
data persists
        ↓
Heute updates
        ↓
Woche updates
        ↓
Monat updates
        ↓
Ziele updates
        ↓
goal detail/history updates
        ↓
missed sessions can be made up
        ↓
completed goal can be moved manually to Schatzkiste
        ↓
archived statistics remain available
```

All progress calculations must be derived from persisted time/focus data and must remain consistent across every view.

---

# 28. HOW TO WORK

Do not implement everything in one huge uncontrolled patch.

For each phase:

1. inspect the relevant existing code,
2. explain briefly what you will change,
3. implement only that phase,
4. run focused tests,
5. run relevant regression tests,
6. report:
   - files changed,
   - migrations,
   - tests run,
   - test results,
   - remaining work,
7. then continue to the next phase.

Prefer minimal, maintainable changes over rewrites.

Use short comments/docstrings for non-obvious functions and calculations.

At the end, provide:
- final architecture summary,
- route/page map,
- database changes,
- exact formulas,
- full test result,
- manual browser test steps,
- any remaining risks.
