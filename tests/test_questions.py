"""Validation test suite for data/questions.json (EPDS Question Bank).

Enforces strict compliance with the clinical instrument specification:
1. Exactly 10 questions.
2. Unique stable IDs (EPDS_Q01 - EPDS_Q10).
3. Exactly four response options per question.
4. Valid integer scores from 0 to 3 per option, covering {0, 1, 2, 3}.
5. Canonical reverse-scoring flags (Q1, Q2, Q4 direct; Q3, Q5-Q10 reverse).
6. Maximum possible cumulative score equals exactly 30.
7. Verifiable source attribution on every question.
8. Independent safety-critical flag on Question 10.
9. JSON syntax and schema completeness.
10. Complete question and response wording without empty strings or omissions.
"""

import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_JSON_PATH = PROJECT_ROOT / "data" / "questions.json"


@pytest.fixture(scope="module")
def questions_data() -> dict:
    """Load and parse data/questions.json."""
    assert QUESTIONS_JSON_PATH.exists(), f"Missing file at {QUESTIONS_JSON_PATH}"
    with open(QUESTIONS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def test_1_json_syntax_and_top_level_schema(questions_data):
    """Test 1: JSON parses cleanly and contains required top-level sections."""
    required_keys = {"instrument", "instructions", "questions", "scoring_guidance", "references"}
    assert required_keys.issubset(questions_data.keys()), f"Missing top-level keys: {required_keys - set(questions_data.keys())}"

    inst = questions_data["instrument"]
    assert inst["name"] == "Edinburgh Postnatal Depression Scale"
    assert inst["abbreviation"] == "EPDS"
    assert inst["question_count"] == 10
    assert inst["maximum_score"] == 30
    assert inst["is_diagnostic"] is False
    assert "past 7 days" in inst["reference_period"].lower()


def test_2_exactly_ten_questions_exist(questions_data):
    """Test 2: Exactly 10 questions are present."""
    questions = questions_data["questions"]
    assert len(questions) == 10, f"Expected exactly 10 questions, found {len(questions)}"


def test_3_unique_stable_ids(questions_data):
    """Test 3: All question IDs are unique and follow EPDS_Q01 - EPDS_Q10 pattern."""
    expected_ids = [f"EPDS_Q{i:02d}" for i in range(1, 11)]
    actual_ids = [q["id"] for q in questions_data["questions"]]

    assert actual_ids == expected_ids, f"Mismatch in IDs. Expected: {expected_ids}, Got: {actual_ids}"
    assert len(set(actual_ids)) == 10, "Duplicate question IDs detected"


def test_4_four_response_options_per_question(questions_data):
    """Test 4: Every question contains exactly four non-empty response options."""
    for q in questions_data["questions"]:
        options = q.get("response_options", [])
        assert len(options) == 4, f"Question {q['id']} does not have 4 options (has {len(options)})"
        for opt in options:
            assert "label" in opt and isinstance(opt["label"], str)
            assert len(opt["label"].strip()) > 0, f"Empty response label found in {q['id']}"


def test_5_valid_integer_scores_zero_to_three(questions_data):
    """Test 5: Every option score is an integer in {0, 1, 2, 3}, covering all 4 values per question."""
    for q in questions_data["questions"]:
        scores = [opt.get("score") for opt in q["response_options"]]
        # Must be valid integers
        for s in scores:
            assert isinstance(s, int), f"Score {s} in {q['id']} is not an integer"
            assert 0 <= s <= 3, f"Score {s} in {q['id']} is outside [0, 3] range"
        # Must cover exactly {0, 1, 2, 3}
        assert set(scores) == {0, 1, 2, 3}, f"Question {q['id']} scores do not cover {{0, 1, 2, 3}}: {scores}"


def test_6_canonical_reverse_scoring_flags(questions_data):
    """Test 6: Reverse-scoring flags strictly follow the EPDS specification:
    - Questions 1, 2, 4 are standard (reverse_scored = False; scores 0, 1, 2, 3).
    - Questions 3, 5, 6, 7, 8, 9, 10 are reverse-scored (reverse_scored = True; scores 3, 2, 1, 0).
    """
    direct_scored_ids = {"EPDS_Q01", "EPDS_Q02", "EPDS_Q04"}
    reverse_scored_ids = {
        "EPDS_Q03", "EPDS_Q05", "EPDS_Q06", "EPDS_Q07",
        "EPDS_Q08", "EPDS_Q09", "EPDS_Q10"
    }

    for q in questions_data["questions"]:
        qid = q["id"]
        is_reverse = q.get("reverse_scored")
        scores = [opt["score"] for opt in q["response_options"]]

        if qid in direct_scored_ids:
            assert is_reverse is False, f"Question {qid} should be direct scored (reverse_scored=False)"
            assert scores == [0, 1, 2, 3], f"Question {qid} scores should be [0, 1, 2, 3], got {scores}"
        elif qid in reverse_scored_ids:
            assert is_reverse is True, f"Question {qid} should be reverse scored (reverse_scored=True)"
            assert scores == [3, 2, 1, 0], f"Question {qid} scores should be [3, 2, 1, 0], got {scores}"
        else:
            pytest.fail(f"Unrecognized question ID: {qid}")


def test_7_maximum_possible_score_is_thirty(questions_data):
    """Test 7: The theoretical maximum possible score across all questions is exactly 30."""
    max_total = sum(max(opt["score"] for opt in q["response_options"]) for q in questions_data["questions"])
    min_total = sum(min(opt["score"] for opt in q["response_options"]) for q in questions_data["questions"])

    assert max_total == 30, f"Max score sum is {max_total}, expected 30"
    assert min_total == 0, f"Min score sum is {min_total}, expected 0"
    assert questions_data["instrument"]["maximum_score"] == 30


def test_8_source_citation_present_on_every_question(questions_data):
    """Test 8: Every question includes source attribution title and URL."""
    for q in questions_data["questions"]:
        src = q.get("source")
        assert isinstance(src, dict), f"Missing source dict on {q['id']}"
        assert "title" in src and len(src["title"].strip()) > 0, f"Missing source title on {q['id']}"
        assert "url" in src and src["url"].startswith("http"), f"Missing or invalid source URL on {q['id']}"


def test_9_question_ten_safety_critical_flag(questions_data):
    """Test 9: Question 10 has safety_critical = True; all others have safety_critical = False."""
    for q in questions_data["questions"]:
        qid = q["id"]
        flag = q.get("safety_critical")
        if qid == "EPDS_Q10":
            assert flag is True, "EPDS_Q10 MUST have safety_critical=True"
        else:
            assert flag is False, f"Question {qid} should have safety_critical=False"


def test_10_no_missing_question_or_response_wording(questions_data):
    """Test 10: Complete question wording and response labels exist without placeholders or omissions."""
    for q in questions_data["questions"]:
        assert len(q.get("question", "").strip()) > 10, f"Question text too short or empty in {q['id']}"
        assert q.get("question_number") in range(1, 11)
        for opt in q["response_options"]:
            assert len(opt["label"].strip()) > 0


def test_11_safety_guidance_and_override_protection(questions_data):
    """Test 11: Scoring guidance contains explicit safety escalation and override protection rules."""
    guidance = questions_data.get("scoring_guidance", {})
    safety_rules = guidance.get("safety_rules", [])

    assert len(safety_rules) >= 1, "Missing safety rules in scoring guidance"
    q10_rule = next((r for r in safety_rules if r.get("question_id") == "EPDS_Q10"), None)
    assert q10_rule is not None, "Missing safety rule for EPDS_Q10"
    assert "score > 0" in q10_rule["condition"]
    assert "override_protection" in q10_rule
    assert "NEVER override" in q10_rule["override_protection"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
