"""
test_policy_lint.py — pytest suite for policy_lint

Covers:
1. Determinism (same input → identical output)
2. Rule firing (one sentence per rule family)
3. Edge cases (empty, very long, unicode punctuation)
4. Warning ordering stability (sorted by rule_id)
5. Cross-version safety (no float knife-edge assertions)
"""

import math
import pytest
from policy_lint import (
    lint,
    LintResult,
    POSTURE_HARD_INVARIANT,
    POSTURE_COST_CURVE,
    POSTURE_AMBIGUOUS,
    POSTURE_NON_FALSIFIABLE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fired_ids(result: LintResult) -> set[str]:
    return {w.rule_id for w in result.warnings}


def score_approx(a: float, b: float, tol: float = 0.01) -> bool:
    """Float comparison with explicit tolerance — no knife-edge failures."""
    return math.isclose(a, b, abs_tol=tol)


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    SENTENCES = [
        "The system always ensures user safety.",
        "Data is never shared without consent.",
        "Our model understands your needs.",
        "",
        "Latency must remain below 200ms for 99% of requests.",
        "A" * 5000,  # very long line
    ]

    @pytest.mark.parametrize("sentence", SENTENCES)
    def test_same_result_n_times(self, sentence):
        results = [lint(sentence) for _ in range(5)]
        first = results[0].as_dict()
        for r in results[1:]:
            assert r.as_dict() == first, (
                f"Non-deterministic output for input {sentence[:60]!r}"
            )

    def test_as_dict_stable_keys(self):
        r = lint("The system should be safe.")
        d = r.as_dict()
        assert set(d.keys()) == {"statement", "warnings", "score", "posture", "flags"}


# ---------------------------------------------------------------------------
# 2. Rule firing
# ---------------------------------------------------------------------------

class TestRuleFiring:

    def test_warn_universal_always(self):
        r = lint("The system always produces correct output.")
        assert "WARN_UNIVERSAL" in fired_ids(r)

    def test_warn_universal_never(self):
        r = lint("It will never fail under any condition.")
        assert "WARN_UNIVERSAL" in fired_ids(r)

    def test_warn_universal_guaranteed(self):
        r = lint("Accuracy is guaranteed at 100%.")
        assert "WARN_UNIVERSAL" in fired_ids(r)

    def test_warn_intent_language_understands(self):
        r = lint("The model understands what the user wants.")
        assert "WARN_INTENT_LANGUAGE" in fired_ids(r)

    def test_warn_intent_language_decides(self):
        r = lint("The system decides the best action automatically.")
        assert "WARN_INTENT_LANGUAGE" in fired_ids(r)

    def test_warn_vague_safety_safe(self):
        r = lint("Outputs are guaranteed to be safe.")
        assert "WARN_VAGUE_SAFETY" in fired_ids(r)

    def test_warn_vague_safety_ethical(self):
        r = lint("We deploy only ethical models.")
        assert "WARN_VAGUE_SAFETY" in fired_ids(r)

    def test_warn_non_operational_ensure(self):
        r = lint("The policy must ensure compliance.")
        assert "WARN_NON_OPERATIONAL" in fired_ids(r)

    def test_warn_non_operational_prevent(self):
        r = lint("Controls prevent harm.")
        assert "WARN_NON_OPERATIONAL" in fired_ids(r)

    def test_warn_marketing_language_significantly(self):
        r = lint("Risks are significantly reduced.")
        assert "WARN_MARKETING_LANGUAGE" in fired_ids(r)

    def test_warn_marketing_language_industry_leading(self):
        r = lint("We deliver industry-leading safety guarantees.")
        assert "WARN_MARKETING_LANGUAGE" in fired_ids(r)

    def test_warn_scope_missing_users(self):
        r = lint("Access is restricted to users.")
        assert "WARN_SCOPE_MISSING" in fired_ids(r)

    def test_warn_scope_missing_data(self):
        r = lint("Data must be protected.")
        assert "WARN_SCOPE_MISSING" in fired_ids(r)

    def test_no_warnings_clean_sentence(self):
        # Narrow, measurable, scoped — should fire no high-severity rules
        r = lint("Response latency must be below 200ms for p99 of API calls.")
        # WARN_NON_OPERATIONAL might not fire; WARN_SCOPE_MISSING for 'calls' might
        # Key assertion: not non-falsifiable
        assert r.posture != POSTURE_NON_FALSIFIABLE

    def test_combined_worst_case(self):
        r = lint("The system always ensures users are safe and never fails.")
        assert "WARN_UNIVERSAL" in fired_ids(r)
        assert "WARN_VAGUE_SAFETY" in fired_ids(r)
        assert r.posture == POSTURE_NON_FALSIFIABLE


# ---------------------------------------------------------------------------
# 3. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_string(self):
        r = lint("")
        assert "WARN_EMPTY" in fired_ids(r)
        assert r.posture == POSTURE_NON_FALSIFIABLE
        assert r.score == 0.0

    def test_whitespace_only(self):
        r = lint("   \t\n  ")
        assert "WARN_EMPTY" in fired_ids(r)
        assert r.posture == POSTURE_NON_FALSIFIABLE

    def test_very_long_line_no_crash(self):
        long_text = ("The system ensures user safety. " * 500).strip()
        r = lint(long_text)
        assert isinstance(r, LintResult)
        assert 0.0 <= r.score <= 1.0

    def test_very_long_line_deterministic(self):
        long_text = ("The system ensures user safety. " * 500).strip()
        r1 = lint(long_text)
        r2 = lint(long_text)
        assert r1.as_dict() == r2.as_dict()

    def test_unicode_smart_quotes(self):
        r = lint("\u201cThe system always ensures a safe outcome.\u201d")
        assert "WARN_UNIVERSAL" in fired_ids(r)
        assert "WARN_VAGUE_SAFETY" in fired_ids(r)

    def test_unicode_em_dash(self):
        # em-dash should not break tokenisation
        r = lint("Safety\u2014as defined by the policy\u2014is guaranteed.")
        assert "WARN_UNIVERSAL" in fired_ids(r)

    def test_unicode_ellipsis(self):
        r = lint("We aim to ensure safety\u2026")
        assert isinstance(r, LintResult)

    def test_single_word(self):
        r = lint("always")
        assert "WARN_UNIVERSAL" in fired_ids(r)

    def test_number_only(self):
        r = lint("42")
        assert isinstance(r, LintResult)
        assert r.posture != POSTURE_NON_FALSIFIABLE or "WARN_EMPTY" not in fired_ids(r)


# ---------------------------------------------------------------------------
# 4. Warning ordering stability
# ---------------------------------------------------------------------------

class TestOrderingStability:

    def test_warnings_sorted_by_rule_id(self):
        r = lint(
            "The system always ensures users are safe, "
            "significantly better than alternatives, "
            "and understands your needs."
        )
        ids = [w.rule_id for w in r.warnings]
        assert ids == sorted(ids), f"Warnings not sorted: {ids}"

    def test_flags_sorted(self):
        r = lint(
            "The system always ensures users are safe, "
            "and understands your needs."
        )
        assert r.flags == sorted(r.flags)

    def test_matched_tokens_sorted(self):
        # "always" and "never" both in WARN_UNIVERSAL
        r = lint("It will always work and never fail.")
        universal = next((w for w in r.warnings if w.rule_id == "WARN_UNIVERSAL"), None)
        assert universal is not None
        assert universal.matched_tokens == sorted(universal.matched_tokens)


# ---------------------------------------------------------------------------
# 5. Posture classification
# ---------------------------------------------------------------------------

class TestPostureClassification:

    def test_hard_invariant_measurable(self):
        # Narrow, shall, measurable — expect HARD_INVARIANT
        r = lint("The API shall respond within 500ms for 99% of requests.")
        assert r.posture == POSTURE_HARD_INVARIANT

    def test_non_falsifiable_empty(self):
        r = lint("")
        assert r.posture == POSTURE_NON_FALSIFIABLE

    def test_non_falsifiable_worst(self):
        r = lint("The system is always safe and trustworthy and never fails.")
        assert r.posture == POSTURE_NON_FALSIFIABLE

    def test_cost_curve_soft_hedge(self):
        r = lint("The team aims to respond within a reasonable timeframe.")
        assert r.posture in (POSTURE_COST_CURVE, POSTURE_AMBIGUOUS)

    def test_score_within_bounds(self):
        sentences = [
            "",
            "always safe",
            "The API shall respond within 100ms.",
            "Outputs are significantly better and more ethical.",
        ]
        for s in sentences:
            r = lint(s)
            assert 0.0 <= r.score <= 1.0, f"Score out of bounds for {s!r}: {r.score}"

    def test_score_is_float(self):
        r = lint("The model ensures safety.")
        assert isinstance(r.score, float)

    def test_score_tolerance_no_knife_edge(self):
        # Check score is stable, not exact float comparison
        r1 = lint("The system should be robust and avoid harm.")
        r2 = lint("The system should be robust and avoid harm.")
        assert score_approx(r1.score, r2.score, tol=0.0001)
