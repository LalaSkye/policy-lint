![CI](https://github.com/LalaSkye/policy-lint/actions/workflows/ci.yml/badge.svg)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
![stdlib only](https://img.shields.io/badge/stdlib-only-green)
![< 200 LOC](https://img.shields.io/badge/LOC-%3C200-lightgrey)

# policy-lint

Deterministic linter for governance statements — surfaces unfalsifiable claims, vague safety language, and scope gaps. No AI, no ML, no opinions.

---

## Why This Exists

Policy documents are full of sentences that sound like commitments but contain no testable claims. Words like "always safe", "ensures responsible behaviour", or "significantly reduces risk" are grammatically valid but operationally empty. `policy-lint` makes that visible, cheaply and reproducibly, so that reviewers, auditors, and engineers can ask: *can this sentence be falsified?* It produces no recommendations and rewrites nothing. It only surfaces the structural properties of what is there. Governance statements themselves need governance — this is the admissibility check for policy language before it enters a decision surface.

---

## Architecture

```
  Input (string / --file / stdin)
         |
         v
  ┌──────────────────────────────────────────────────────┐
  │                   policy_lint.py                      │
  │                                                       │
  │  Rule engine (named regex patterns, stdlib re only)   │
  │                                                       │
  │  WARN_UNIVERSAL      ──┐                              │
  │  WARN_VAGUE_SAFETY   ──┤                              │
  │  WARN_INTENT_LANGUAGE──┤──> sorted typed warnings     │
  │  WARN_MARKETING      ──┤                              │
  │  WARN_NON_OPERATIONAL──┤                              │
  │  WARN_SCOPE_MISSING  ──┤                              │
  │  WARN_EMPTY          ──┘                              │
  │         |                                             │
  │         v                                             │
  │  Posture classification + 0–1 score                   │
  └──────────────────────────────────────────────────────┘
         |
         v
  Plain text output  OR  --json (deterministic key ordering)
```

---

## Quickstart

```bash
git clone https://github.com/LalaSkye/policy-lint.git
cd policy-lint
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

## Example Output

```
STATEMENT : 'The system is always safe and trustworthy.'
  [ERROR  ] WARN_UNIVERSAL    -->  always
  [WARNING] WARN_VAGUE_SAFETY -->  safe, trustworthy
  POSTURE   : NON_FALSIFIABLE
  SCORE     : 0.2857
  FLAGS     : WARN_UNIVERSAL, WARN_VAGUE_SAFETY
---
STATEMENT : 'The API shall respond within 500ms for 99% of requests.'
  (no warnings)
  POSTURE   : HARD_INVARIANT
  SCORE     : 1.0000
  FLAGS     : --
---
STATEMENT : 'The system ensures responsible behaviour for all users.'
  [WARNING] WARN_NON_OPERATIONAL   -->  ensures
  [WARNING] WARN_VAGUE_SAFETY      -->  responsible
  [WARNING] WARN_SCOPE_MISSING     -->  users
  POSTURE   : COST_CURVE
  SCORE     : 0.4286
  FLAGS     : WARN_NON_OPERATIONAL, WARN_VAGUE_SAFETY, WARN_SCOPE_MISSING
```

JSON output:

```json
{
  "statement": "The API shall respond within 500ms for 99% of requests.",
  "posture": "HARD_INVARIANT",
  "score": 1.0,
  "flags": [],
  "warnings": []
}
```

---

## Posture Classifications

| Posture | Meaning |
|---|---|
| `HARD_INVARIANT` | Measurable, scoped, no universal claims — structurally falsifiable |
| `COST_CURVE` | Soft commitment (`aims`/`seeks`/`should`) or moderate warning load |
| `AMBIGUOUS` | Insufficient signal to classify firmly |
| `NON_FALSIFIABLE` | High warning load, universal claims, or vague safety without conditions |

---

## Rule Families

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

## Design Constraints

- **Deterministic:** same input produces same output across Python 3.10 / 3.11 / 3.12; no randomness, no locale dependence
- **Auditable:** all rules are named regex patterns in a single file; no hidden logic
- **Small:** core module < 200 LOC; zero non-stdlib dependencies
- **Tested:** pytest suite covers determinism, rule firing, edge cases, and ordering stability

---

## Testing

```bash
pip install pytest
pytest -v
```

---

## Non-Goals

No web UI. No GitHub Action templates. No LLM integration. No recommendations engine. No automatic rewriting. No dataset collection. Not AI. Not legal advice. Not a policy engine.

---

## Part of the Execution Boundary Series

| Repo | Layer | What It Does |
|---|---|---|
| [interpretation-boundary-lab](https://github.com/LalaSkye/interpretation-boundary-lab) | Upstream boundary | 10-rule admissibility gate for interpretations |
| [dual-boundary-admissibility-lab](https://github.com/LalaSkye/dual-boundary-admissibility-lab) | Full corridor | Dual-boundary model with pressure monitoring and C-sector rotation |
| [execution-boundary-lab](https://github.com/LalaSkye/execution-boundary-lab) | Execution boundary | Demonstrates cascading failures without upstream governance |
| [stop-machine](https://github.com/LalaSkye/stop-machine) | Control primitive | Deterministic three-state stop controller |
| [constraint-workshop](https://github.com/LalaSkye/constraint-workshop) | Control primitives | Authority gate, invariant litmus, stop machine |
| [csgr-lab](https://github.com/LalaSkye/csgr-lab) | Measurement | Contracted stability and drift measurement |
| [invariant-lock](https://github.com/LalaSkye/invariant-lock) | Drift prevention | Refuse execution unless version increments |
| [policy-lint](https://github.com/LalaSkye/policy-lint) | Policy validation | Deterministic linter for governance statements |
| [deterministic-lexicon](https://github.com/LalaSkye/deterministic-lexicon) | Vocabulary | Fixed terms, exact matches, no inference |

---

## Work With Me

Does your AI policy language hold up under scrutiny? I consult on governance statement design, policy auditing, and EU AI Act compliance tooling.

→ **ricky.mcjones@gmail.com**
→ [LinkedIn](https://linkedin.com/in/ricky-jones-1b745474)
→ [GitHub Sponsors](https://github.com/sponsors/LalaSkye)

---

## License

Apache 2.0. See `LICENSE`.
