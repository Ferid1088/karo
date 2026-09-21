# Pilot lesson — adding unlike fractions

One instance of `01_ARCHITECTURE.md`. Everything here is content and UI for a
single concept; nothing here is a general rule. When a second lesson is built,
it gets its own file in this shape.

**Concept:** `mathematik/brueche/ungleichnamig-addieren`
**Grade:** 5–6
**Primary error type:** `zaehler-und-nenner-addiert` (1/2 + 1/3 = 2/5)

---

## 1. Phase sequence

```
HOOK → RULE → WORKED_EXAMPLE → GUIDED_TASK → INDEPENDENT_TASK → COMPLETE
                                           ↘ ADAPTATION ↗
```

| Phase | Purpose | Visual support |
|---|---|---|
| HOOK | the child notices their answer cannot be right | the two fractions |
| RULE | why equal pieces are needed | strips, cut |
| WORKED_EXAMPLE | one fully solved example, step by step | one picture per step |
| GUIDED_TASK | child solves, with the visual model present | its own fractions, from the start |
| INDEPENDENT_TASK | can the child do it without the picture? | **none, deliberately** |
| ADAPTATION | after a failed independent attempt, a different model | pizza or number line |

`INDEPENDENT_TASK` having no picture is a *hypothesis to test*, not an
invariant. If the data says children fail there for the wrong reason, change it.

---

## 2. RULE — explain the why, not only the what

The rule screen must connect back to what the child just saw, explain *why*
equal pieces are required, and define "gemeinsamer Nenner" in child language.
Maximum four short paragraphs — a learning step, not a lecture.

The causal chain the child should end up with:

```
different-sized pieces cannot be counted together
↓
make the pieces the same size
↓
now count how many equal pieces there are
```

Reference text:

> Du hast gerade gesehen: Eine Hälfte und ein Drittel bestehen aus
> unterschiedlich großen Stücken.
>
> Solange die Stücke unterschiedlich groß sind, können wir sie nicht einfach
> zusammenzählen — genauso wenig wie ein großes und ein kleines Pizzastück
> einfach „zwei gleich große Stücke" sind.
>
> Deshalb teilen wir beide Ganzen zuerst in gleich große Stücke. Die Zahl unten
> zeigt, in wie viele gleich große Stücke das Ganze geteilt ist.
>
> Wenn beide Brüche unten dieselbe Zahl haben, nennen wir diese Zahl den
> **gemeinsamen Nenner**.

CTA: `Zeig mir ein Beispiel`

---

## 3. WORKED_EXAMPLE

Exactly one fully solved example, before the child solves anything alone. It
must use **different numbers from the guided task** so the answer cannot be
copied.

```
1/3 + 1/6 = ?

Schritt 1 — gemeinsamen Nenner finden
Schritt 2 — beide Brüche auf Sechstel bringen
Schritt 3 — Zähler zusammenzählen
```

Each step gets its own labelled picture. The progression must make the reasoning
visible, not just show the final notation:

```
starting fractions → same-sized pieces → equivalent fractions
→ combine → result
```

CTA: `Jetzt versuche ich es selbst`

---

## 4. The fraction strip — rendering correctness

Every strip represents **one whole** and is therefore drawn at the **same total
width**. The pieces divide that fixed width.

```css
.strip { display: flex; width: 20rem; max-width: 100%; }
.piece { flex: 1 1 0; }
```

Never give individual pieces a fixed width. With fixed pieces, a strip in thirds
becomes physically wider than one in halves — which is mathematically wrong and
contradicts the exact idea being taught: *the whole stays the same, only the
partition changes.*

```
correct:  same whole → different number of equal parts → different piece sizes
wrong:    same piece width → different whole widths
```

All strips render through one reusable component:

```
streifen(gefuellt, gesamt)     # streifen(1,2)  streifen(3,6)
```

Validate `0 <= gefuellt <= gesamt` and `gesamt > 0`. Give every strip an
accessible label, e.g. `2 von 5 gleich großen Stücken`. Never duplicate strip
rendering logic across templates.

---

## 5. "Das habe ich nicht verstanden" — on every phase

Available in every phase except `COMPLETE`, including exercise screens. Opens a
second, fuller explanation of the *current* phase.

Rules:

1. **Different wording** from the screen. Repeating a sentence the child did not
   understand does not help.
2. **Always with pictures** — roughly 2–4 labelled strips. Never text-only.
3. On exercise screens it explains the task or concept but **does not reveal the
   answer**. Progressive disclosure is the hint system's job.
4. Opening or closing it changes nothing: not the phase, not attempts, not
   mastery, not hints, not the child's typed answer.
5. Content is stored and served as a lookup — **zero model calls**
   (`01_ARCHITECTURE.md` §11).

Storage shape, one entry per phase:

```python
EXPLAIN_MORE = {
    "RULE": {
        "text": (
            "Stell dir vor, beide Streifen sind gleich große Tafeln Schokolade. "
            "Wenn eine Tafel in 2 Stücke und die andere in 3 Stücke geteilt ist, "
            "sind die einzelnen Stücke nicht gleich groß. Erst wenn beide Tafeln "
            "in gleich große Stücke geteilt sind, können wir zählen, wie viele "
            "solcher Stücke wir zusammen haben."
        ),
        "bilder": [
            ("Eine Hälfte", 1, 2),
            ("Ein Drittel", 1, 3),
            ("Drei Sechstel", 3, 6),
            ("Zwei Sechstel", 2, 6),
        ],
    },
    # one entry per phase except COMPLETE
}
```

The storage format may follow existing Karo conventions; the behavior may not
change.

---

## 6. "Ich habe eine andere Frage" — static FAQ

Reachable from every phase except `COMPLETE`. Same state guarantees as §5: never
changes phase, attempts, mastery or hints, and never calls a model.

Initial entries:

```
Was ist der Zähler, was ist der Nenner?
Was heißt „gemeinsamer Nenner"?
Wie tippe ich meine Antwort?
Ich weiß gerade nicht, was ich tun soll.
```

**Zähler / Nenner** — with labelled strips: the bottom number says into how many
equal pieces the whole was divided; the top number says how many of those pieces
we have.

**Gemeinsamer Nenner** —
> Beide Brüche werden so dargestellt, dass ihre Stücke gleich groß sind. Dann
> steht unten bei beiden Brüchen dieselbe Zahl. Diese gemeinsame Zahl nennen wir
> den gemeinsamen Nenner.

**Wie tippe ich meine Antwort?** — explain the accepted format only; never the
current answer.

**Ich weiß nicht, was ich tun soll** —
> Schau dir zuerst die beiden Brüche an. Deine Aufgabe ist es jetzt, eine
> Antwort einzugeben. Wenn du einen kleinen Hinweis möchtest, nutze den Tipp.

---

## 7. Why help is never a free-text box to a model

Deliberate, and not a temporary limitation:

- **Instant.** Help arrives with no generation delay, at the moment of confusion.
- **Free at runtime.** The same content serves every child without a call.
- **Testable.** Every help path can be asserted in CI.
- **Controlled.** The team knows exactly what the child is told.
- **Safe.** No chance of an unsuitable answer, a wrong explanation, content above
  the child's level, a personal question, or an accidental spoiler of the task.

```
HELP → stored content → deterministic visuals → unchanged lesson state
```

Not:

```
HELP → free-text question → model → generated answer
```
