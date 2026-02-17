"""policy_lint — deterministic governance statement linter. No AI. No ML."""
from __future__ import annotations
import re, sys, json, argparse
from dataclasses import dataclass
from typing import Sequence

VERSION = "0.1.0"
POSTURE_HARD_INVARIANT  = "HARD_INVARIANT"
POSTURE_COST_CURVE      = "COST_CURVE"
POSTURE_AMBIGUOUS       = "AMBIGUOUS"
POSTURE_NON_FALSIFIABLE = "NON_FALSIFIABLE"

@dataclass(frozen=True)
class Rule:
    rule_id: str; description: str; pattern: re.Pattern; weight: int; severity: str

def _p(s: str) -> re.Pattern:
    return re.compile(s, re.IGNORECASE)

RULES: tuple[Rule, ...] = (
    Rule("WARN_EMPTY",
         "Statement is empty or whitespace-only.",
         _p(r"(?!)"), 10, "error"),
    Rule("WARN_INTENT_LANGUAGE",
         "Anthropomorphic/intent language (understands, wants, decides, knows, believes, intends). "
         "Describe behaviour, not mental states.",
         _p(r"\b(understands?|wants?|decides?|knows?|believes?|intends?|intentions?)\b"), 3, "warning"),
    Rule("WARN_MARKETING_LANGUAGE",
         "Unquantified comparative claim (significantly, substantially, industry-leading, best-in-class). "
         "Add a baseline or metric.",
         _p(r"\b(significantly|substantially|industry[- ]leading|best[- ]in[- ]class"
            r"|state[- ]of[- ]the[- ]art|cutting[- ]edge|world[- ]class)\b"), 3, "warning"),
    Rule("WARN_NON_OPERATIONAL",
         "Operational verb (ensure, prevent, avoid, mitigate, promote) without defined scope/object.",
         _p(r"\b(ensures?|prevents?|avoids?|mitigates?|promotes?)\b"), 2, "warning"),
    Rule("WARN_SCOPE_MISSING",
         "Broad/unmodified entity reference (users, data, harm, system, model, people) "
         "without scope qualifiers.",
         _p(r"\b(users?|data|harms?|systems?|models?|people|individuals?|society)\b"), 1, "info"),
    Rule("WARN_UNIVERSAL",
         "Universal/absolute claim (always, never, guaranteed, cannot fail, impossible, 100%, zero risk). "
         "Absolute claims are rarely falsifiable.",
         _p(r"\b(always|never|guaranteed|cannot\s+fail|impossible|100\s*%"
            r"|zero\s+risk|infallible|foolproof)\b"), 5, "error"),
    Rule("WARN_VAGUE_SAFETY",
         "Vague safety/quality adjective (safe, secure, robust, ethical, responsible, trustworthy, "
         "fair, aligned) without an associated metric or condition.",
         _p(r"\b(safe|secure|robust|ethical|responsible|trustworthy|fair|aligned|harmless)\b"), 3, "warning"),
)

RULE_INDEX: dict[str, Rule] = {r.rule_id: r for r in RULES}
_WMAX: int = sum(r.weight for r in RULES if r.rule_id != "WARN_EMPTY") * 2

@dataclass
class Warning:
    rule_id: str; severity: str; description: str; matched_tokens: list[str]
    def as_dict(self) -> dict:
        return {"rule_id": self.rule_id, "severity": self.severity,
                "description": self.description, "matched_tokens": self.matched_tokens}

@dataclass
class LintResult:
    statement: str; warnings: list[Warning]; score: float; posture: str; flags: list[str]
    def as_dict(self) -> dict:
        return {"statement": self.statement, "warnings": [w.as_dict() for w in self.warnings],
                "score": round(self.score, 4), "posture": self.posture, "flags": self.flags}

_UNICODE_MAP = {"\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"',
                "\u2013":"-","\u2014":"-","\u2026":"..."}

def _normalise(text: str) -> str:
    for src, dst in _UNICODE_MAP.items():
        text = text.replace(src, dst)
    return text

def lint(statement: str) -> LintResult:
    """Lint a single governance statement. Pure; fully deterministic."""
    statement = _normalise(statement)
    stripped  = statement.strip()
    warnings: list[Warning] = []

    if not stripped:
        warnings.append(Warning("WARN_EMPTY", "error", RULE_INDEX["WARN_EMPTY"].description, []))
        return LintResult(statement, warnings, 0.0, POSTURE_NON_FALSIFIABLE, ["WARN_EMPTY"])

    fired_weights = 0
    for rule in RULES:
        if rule.rule_id == "WARN_EMPTY":
            continue
        matches = rule.pattern.findall(stripped)
        if matches:
            tokens = sorted({m.lower() for m in matches})
            warnings.append(Warning(rule.rule_id, rule.severity, rule.description, tokens))
            fired_weights += rule.weight

    warnings.sort(key=lambda w: w.rule_id)
    score     = max(0.0, min(1.0, 1.0 - (fired_weights / _WMAX)))
    fired_ids = {w.rule_id for w in warnings}
    flags     = sorted(fired_ids)

    hard_combo = "WARN_UNIVERSAL" in fired_ids and "WARN_VAGUE_SAFETY" in fired_ids
    has_anchor = bool(re.search(r"\b(must|shall)\b", stripped, re.IGNORECASE))
    has_metric = bool(re.search(r"\b\d+(\.\d+)?\s*(%|ms|seconds?|hours?|days?|tokens?|calls?)\b",
                                stripped, re.IGNORECASE))
    has_hedge  = bool(re.search(r"\b(aims?|seeks?|tries?|try|should|intend)\b", stripped, re.IGNORECASE))

    if score < 0.40 or hard_combo:
        posture = POSTURE_NON_FALSIFIABLE
    elif score < 0.60:
        posture = POSTURE_AMBIGUOUS
    elif score < 0.85 or has_hedge:
        posture = POSTURE_COST_CURVE
    elif "WARN_UNIVERSAL" not in fired_ids and (has_anchor or has_metric):
        posture = POSTURE_HARD_INVARIANT
    else:
        posture = POSTURE_AMBIGUOUS

    return LintResult(statement, warnings, score, posture, flags)

def format_result(r: LintResult, json_mode: bool = False) -> str:
    if json_mode:
        return json.dumps(r.as_dict(), sort_keys=True, ensure_ascii=False)
    lines = [f"STATEMENT : {r.statement!r}"]
    for w in r.warnings:
        tokens = ", ".join(w.matched_tokens) if w.matched_tokens else "-"
        lines.append(f"  [{w.severity.upper():7s}] {w.rule_id}  ->  {tokens}")
    if not r.warnings:
        lines.append("  (no warnings)")
    lines.append(f"  POSTURE   : {r.posture}")
    lines.append(f"  SCORE     : {r.score:.4f}")
    lines.append(f"  FLAGS     : {', '.join(r.flags) if r.flags else '-'}")
    return "\n".join(lines)

def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="policy-lint",
        description="Deterministic governance statement linter. No AI. No ML.")
    p.add_argument("statement", nargs="?", help="Inline statement.")
    p.add_argument("--file", "-f", metavar="PATH", help="File of statements (one per line).")
    p.add_argument("--json", action="store_true", help="JSON output.")
    p.add_argument("--version", action="version", version=f"policy-lint {VERSION}")
    args = p.parse_args(argv)

    statements: list[str] = []
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                statements = [line.rstrip("\n") for line in fh]
        except OSError as exc:
            print(f"policy-lint: {exc}", file=sys.stderr); return 1
    elif args.statement:
        statements = [args.statement]
    elif not sys.stdin.isatty():
        statements = [line.rstrip("\n") for line in sys.stdin]
    else:
        p.print_help(); return 0

    results = [lint(s) for s in statements]
    if args.json:
        print(json.dumps([r.as_dict() for r in results], sort_keys=True, ensure_ascii=False))
    else:
        for i, result in enumerate(results):
            if i: print("---")
            print(format_result(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
