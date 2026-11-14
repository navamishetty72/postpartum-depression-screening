"""Service layer for loading EPDS questions and calculating clinical screening scores.

Uses data/questions.json as the single source of truth.
Ensures zero logging of identifiable patient responses.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import HTTPException

from backend.schemas.questionnaire import (
    EPDSQuestionnaireResponse,
    EPDSSubmissionRequest,
    EPDSSubmissionResponse,
    ItemScoreResult,
    SafetyAlertResult,
)

logger = logging.getLogger("ppd.questionnaire")

# Path to the single source of truth
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
QUESTIONS_JSON_PATH = PROJECT_ROOT / "data" / "questions.json"
TRANSLATIONS_JSON_PATH = PROJECT_ROOT / "data" / "epds_translations.json"


class EPDSQuestionnaireService:
    """Encapsulates verified EPDS instrument retrieval and clinical scoring logic."""

    def __init__(
        self,
        data_path: Optional[Path] = None,
        translations_path: Optional[Path] = None,
    ) -> None:
        self.data_path = data_path or QUESTIONS_JSON_PATH
        self.translations_path = translations_path or TRANSLATIONS_JSON_PATH
        self._raw_data: Optional[dict] = None
        self._questions_by_id: Optional[Dict[str, dict]] = None
        self._translations_data: Optional[dict] = None

    def _ensure_loaded(self) -> None:
        """Load and cache the question bank from data/questions.json and translations."""
        if self._raw_data is None:
            if not self.data_path.exists():
                raise FileNotFoundError(
                    f"EPDS question bank file missing at: {self.data_path}"
                )
            with open(self.data_path, "r", encoding="utf-8") as f:
                self._raw_data = json.load(f)

            self._questions_by_id = {
                q["id"]: q for q in self._raw_data.get("questions", [])
            }

        if self._translations_data is None and self.translations_path.exists():
            try:
                with open(self.translations_path, "r", encoding="utf-8") as tf:
                    self._translations_data = json.load(tf)
            except Exception as exc:
                logger.warning("Could not load EPDS translations: %s", exc)

    def get_questionnaire(self, language: str = "en") -> EPDSQuestionnaireResponse:
        """Return the complete EPDS questionnaire and guidance localized to the specified language."""
        self._ensure_loaded()
        assert self._raw_data is not None

        lang = (language or "en").lower().strip()
        supported = []
        if self._translations_data:
            supported = self._translations_data.get("supported_languages", [])

        # Copy top-level dictionary
        resp_data = dict(self._raw_data)
        resp_data["language"] = lang
        resp_data["supported_languages"] = supported

        # Localize participant instructions if translation exists
        instructions = dict(resp_data.get("instructions", {}))
        if self._translations_data and lang in self._translations_data.get("instructions", {}):
            instructions["participant"] = self._translations_data["instructions"][lang]
        resp_data["instructions"] = instructions

        # Localize question items and attach translations map
        localized_questions = []
        for q in self._raw_data.get("questions", []):
            qid = q["id"]
            q_copy = dict(q)
            q_trans = (
                self._translations_data.get("questions", {}).get(qid, {})
                if self._translations_data
                else {}
            )
            all_translations = q_trans.get("translations", {})
            q_copy["translations"] = all_translations

            if lang != "en" and lang in all_translations:
                target_trans = all_translations[lang]
                q_copy["question"] = target_trans.get("question", q["question"])
                translated_opts = target_trans.get("response_options", [])
                if len(translated_opts) == len(q["response_options"]):
                    q_copy["response_options"] = [
                        {"label": lbl, "score": orig["score"]}
                        for lbl, orig in zip(translated_opts, q["response_options"])
                    ]
            localized_questions.append(q_copy)

        resp_data["questions"] = localized_questions
        return EPDSQuestionnaireResponse.model_validate(resp_data)

    def calculate_score(
        self,
        submission: EPDSSubmissionRequest,
    ) -> EPDSSubmissionResponse:
        """Calculate EPDS scores, thresholds, and independent safety escalation.

        Enforces that all 10 questions are answered exactly once.
        Safely computes scores without persisting or logging individual patient answers.
        """
        self._ensure_loaded()
        assert self._questions_by_id is not None

        expected_ids = [f"EPDS_Q{i:02d}" for i in range(1, 11)]
        submitted_by_id = {ans.question_id: ans for ans in submission.answers}

        # Validate that all 10 questions are answered
        missing_ids = set(expected_ids) - set(submitted_by_id.keys())
        if missing_ids:
            raise HTTPException(
                status_code=422,
                detail=f"Incomplete submission: Missing answers for {sorted(missing_ids)}",
            )

        item_scores: List[ItemScoreResult] = []
        total_score = 0
        q10_score = 0

        for qid in expected_ids:
            q_def = self._questions_by_id.get(qid)
            if not q_def:
                raise HTTPException(
                    status_code=500,
                    detail=f"Configuration error: Question {qid} not found in question bank",
                )

            sub_item = submitted_by_id[qid]
            idx = sub_item.selected_index
            options = q_def["response_options"]

            if idx < 0 or idx >= len(options):
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid option index {idx} for question {qid} (must be 0-3)",
                )

            selected_opt = options[idx]
            opt_score = selected_opt["score"]
            total_score += opt_score

            if qid == "EPDS_Q10":
                q10_score = opt_score

            # Resolve question_text and option_label in requested language if available
            q_text = q_def["question"]
            opt_label = selected_opt["label"]
            sub_lang = (getattr(submission, "language", None) or "en").lower().strip()
            if self._translations_data and sub_lang != "en":
                q_trans = (
                    self._translations_data.get("questions", {})
                    .get(qid, {})
                    .get("translations", {})
                    .get(sub_lang)
                )
                if q_trans:
                    q_text = q_trans.get("question", q_text)
                    t_opts = q_trans.get("response_options", [])
                    if idx < len(t_opts):
                        opt_label = t_opts[idx]

            item_scores.append(
                ItemScoreResult(
                    question_id=qid,
                    question_number=q_def["question_number"],
                    question_text=q_text,
                    selected_option_index=idx,
                    selected_option_label=opt_label,
                    score=opt_score,
                    reverse_scored=q_def["reverse_scored"],
                    safety_critical=q_def["safety_critical"],
                )
            )

        # Match clinical threshold from verified scoring guidance
        guidance = self._raw_data.get("scoring_guidance", {})
        thresholds = guidance.get("thresholds", [])

        classification = "Undetermined"
        clinical_significance = "Undetermined"
        recommended_action = "Clinical review recommended."

        for t in thresholds:
            if t["score_min"] <= total_score <= t["score_max"]:
                classification = t["classification"]
                clinical_significance = t["clinical_significance"]
                recommended_action = t["recommended_action"]
                break

        # Independent Question 10 evaluation
        safety_rules = guidance.get("safety_rules", [])
        q10_rule = next((r for r in safety_rules if r["question_id"] == "EPDS_Q10"), None)

        safety_triggered = q10_score > 0
        if safety_triggered:
            severity = "URGENT_SAFETY_ASSESSMENT"
            message = (
                "SAFETY ALERT: Patient reported thoughts of self-harm on Question 10 "
                f"(score={q10_score}). Immediate human clinical safety evaluation required "
                "before the patient leaves the clinic or session."
            )
            protocol = q10_rule["escalation_protocol"] if q10_rule else [
                "1. Immediately notify the attending clinician or mental health specialist.",
                "2. Conduct structured crisis self-harm risk assessment.",
                "3. Ensure the patient is not left unattended.",
            ]
        else:
            severity = "NONE"
            message = "No self-harm thoughts reported on Question 10."
            protocol = []

        # Non-identifiable operational logging
        logger.info(
            "EPDS score calculated successfully: total_score=%d, risk_tier=%s, q10_safety_alert=%s",
            total_score,
            classification,
            safety_triggered,
        )

        return EPDSSubmissionResponse(
            total_score=total_score,
            maximum_score=30,
            classification=classification,
            clinical_significance=clinical_significance,
            recommended_action=recommended_action,
            is_diagnostic=False,
            item_scores=item_scores,
            safety_alert=SafetyAlertResult(
                triggered=safety_triggered,
                question_id="EPDS_Q10",
                question_10_score=q10_score,
                severity=severity,
                message=message,
                override_protection=(
                    "A positive Question 10 response must NEVER be overridden by a low total score or ML prediction."
                ),
                escalation_protocol=protocol,
            ),
        )


# Global singleton instance
questionnaire_service = EPDSQuestionnaireService()
