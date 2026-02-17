# policy-lint

A deterministic, auditable linter for governance statements. Paste in a policy sentence; get back structured warnings about unfalsifiable claims, vague safety language, intent attribution, and missing scope — with no AI, no ML, no orchestration layer. Just a brick.

---

## Why this exists

Policy documents are full of sentences that *sound* like commitments but contain no testable claims. Words like "always safe", "ensures responsible behaviour", or "significantly reduces risk" are grammatically valid but operationally empty. `policy-lint` makes that visible, cheaply and reproducibly, so that reviewers, auditors, and engineers can ask: *can this sentence be falsified?* It produces no recommendations and rewrites nothing. It only surfaces the structural properties of what's there.

---

## What it does / what it does not do

**Does:**
- Classify governance statements by structural posture: `HARD_INVARIANT`, `COST_CURVE`, `AMBIGUOUS`, or `NON_FALSIFIABLE`
- Emit sorted, typed warnings per rule family (universal claims, intent language, vague safety, non-operational verbs, scope gaps, marketing language)
- Produce a 0–1 score where higher = more structurally sound
- Accept inline strings, files, or stdin
- Output plain text or `--json` (deterministic key ordering)

**Does not:**
- Use AI or ML at any layer
- Provide legal advice or policy recommendations
- Rewrite or fix statements
- Connect to external services
- Depend on anything outside the Python standard library

---

## Quickstart

```bash
pip install -e .

# Inline statement
policy-lint "The system is always safe and trustworthy."

# File of statements
policy-lint --file examples/sample_statements.txt

# Stdin
echo "Data is never shared without consent." | policy-lint

# JSON output
policy-lint --json "The API shall respond within 500ms for 99% of requests."
```

---

## Example output

```
STATEMENT : 'The system is always safe and trustworthy.'
  [ERROR  ] WARN_UNIVERSAL  →  always
  [WARNING] WARN_VAGUE_SAFETY  →  safe, trustworthy
  POSTURE   : NON_FALSIFIABLE
  SCORE     : 0.2857
  FLAGS     : WARN_UNIVERSAL, WARN_VAGUE_SAFETY
---
STATEMENT : 'The API shall respond within 500ms for 99% of requests.'
  (no warnings)
  POSTURE   : HARD_INVARIANT
  SCORE     : 1.0000
  FLAGS     : —
```

---

## Posture classifications

| Posture | Meaning |
|---|---|
| `HARD_INVARIANT` | Measurable, scoped, no universal claims — structurally falsifiable |
| `COST_CURVE` | Soft commitment (aims/seeks/should) or moderate warning load |
| `AMBIGUOUS` | Insufficient signal to classify firmly |
| `NON_FALSIFIABLE` | High warning load, universal claims, or vague safety without conditions |

---

## Rule families

| Rule ID | Triggers |
|---|---|
| `WARN_EMPTY` | Empty or whitespace-only input |
| `WARN_INTENT_LANGUAGE` | `understands`, `wants`, `decides`, `knows`, `believes`, `intends` |
| `WARN_MARKETING_LANGUAGE` | `significantly`, `substantially`, `industry-leading`, `best-in-class` |
| `WARN_NON_OPERATIONAL` | `ensure`, `prevent`, `avoid`, `mitigate`, `promote` without defined scope |
| `WARN_SCOPE_MISSING` | `users`, `data`, `harm`, `system`, `model` without modifiers |
| `WARN_UNIVERSAL` | `always`, `never`, `guaranteed`, `cannot fail`, `impossible`, `100%`, `zero risk` |
| `WARN_VAGUE_SAFETY` | `safe`, `secure`, `robust`, `ethical`, `responsible`, `trustworthy`, `fair`, `aligned` |

---

## Design constraints

- **Deterministic:** same input → same output across Python 3.10 / 3.11 / 3.12; no randomness, no locale dependence
- **Auditable:** all rules are named regex patterns in a single file; no hidden logic
- **Small:** core module ≤ 200 LOC; zero non-stdlib dependencies
- **Tested:** `pytest` suite covers determinism, rule firing, edge cases, and ordering stability

```bash
pip install pytest
pytest
```

---

## Non-goals

No web UI. No GitHub Action templates. No LLM integration. No recommendations engine. No automatic rewriting. No dataset scraping.

---

*Not AI. Not legal advice. Not a policy engine.*
