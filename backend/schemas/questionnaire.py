"""Pydantic v2 schemas for the EPDS questionnaire and scoring service.

Models strictly reflect the verified instrument schema in data/questions.json.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResponseOptionSchema(BaseModel):
    label: str = Field(..., description="Exact verified option label wording")
    score: int = Field(..., ge=0, le=3, description="Score assigned to this option (0-3)")


class QuestionSourceSchema(BaseModel):
    title: str = Field(..., description="Title of the source organization/document")
    url: str = Field(..., description="URL of the source document")


class QuestionItemSchema(BaseModel):
    id: str = Field(..., description="Stable question identifier (e.g., EPDS_Q01)")
    question_number: int = Field(..., ge=1, le=10, description="1-based question number")
    question: str = Field(..., description="Exact verified question wording")
    response_options: List[ResponseOptionSchema] = Field(..., min_length=4, max_length=4)
    reverse_scored: bool = Field(..., description="Whether the question is scored in reverse")
    safety_critical: bool = Field(..., description="Whether this is the self-harm safety item (Item 10)")
    source: QuestionSourceSchema


class InstrumentMetadataSchema(BaseModel):
    name: str = Field(..., description="Instrument name")
    abbreviation: str = Field(..., description="Instrument abbreviation (EPDS)")
    version: str = Field(..., description="Instrument version")
    question_count: int = Field(..., description="Total items (10)")
    reference_period: str = Field(..., description="Time window evaluated (past 7 days)")
    maximum_score: int = Field(..., description="Maximum possible cumulative score (30)")
    is_diagnostic: bool = Field(default=False, description="Explicit flag declaring non-diagnostic status")
    purpose: str
    authors: str
    publication_year: int
    original_citation: str
    reproduction_permission: str


class ScoringThresholdSchema(BaseModel):
    score_min: int = Field(..., ge=0)
    score_max: int = Field(..., le=30)
    classification: str
    clinical_significance: str
    recommended_action: str


class SafetyRuleSchema(BaseModel):
    rule_id: str
    question_id: str
    condition: str
    trigger: str
    priority: str
    clinical_mandate: str
    override_protection: str
    escalation_protocol: List[str]


class ScoringGuidanceSchema(BaseModel):
    interpretation: str
    scoring_method: str
    total_score_range: Dict[str, int]
    thresholds: List[ScoringThresholdSchema]
    safety_rules: List[SafetyRuleSchema]


class EPDSQuestionnaireResponse(BaseModel):
    instrument: InstrumentMetadataSchema
    instructions: Dict[str, Any]
    questions: List[QuestionItemSchema]
    scoring_guidance: ScoringGuidanceSchema
    references: List[Dict[str, Any]]


# --- Submission Request & Response Schemas ---


class AnswerSubmissionItem(BaseModel):
    question_id: str = Field(..., description="Question ID matching EPDS_Q01 through EPDS_Q10")
    selected_index: int = Field(..., ge=0, le=3, description="0-based index of selected response option (0-3)")


class EPDSSubmissionRequest(BaseModel):
    answers: List[AnswerSubmissionItem] = Field(
        ...,
        min_length=10,
        max_length=10,
        description="List of exactly 10 answers corresponding to EPDS_Q01 through EPDS_Q10",
    )


class ItemScoreResult(BaseModel):
    question_id: str
    question_number: int
    question_text: str
    selected_option_index: int
    selected_option_label: str
    score: int
    reverse_scored: bool
    safety_critical: bool


class SafetyAlertResult(BaseModel):
    triggered: bool = Field(..., description="True if Question 10 score is non-zero")
    question_id: str = "EPDS_Q10"
    question_10_score: int = Field(..., ge=0, le=3)
    severity: str = Field(..., description="'URGENT_SAFETY_ASSESSMENT' if triggered, else 'NONE'")
    message: str = Field(..., description="Safety and escalation warning message")
    override_protection: str = Field(
        default="A positive Question 10 response must NEVER be overridden by a low total score or ML prediction."
    )
    escalation_protocol: List[str]


class EPDSSubmissionResponse(BaseModel):
    total_score: int = Field(..., ge=0, le=30, description="Sum of all 10 item scores")
    maximum_score: int = Field(default=30)
    classification: str = Field(..., description="Clinical risk tier based on validated cutoff")
    clinical_significance: str
    recommended_action: str
    is_diagnostic: bool = Field(default=False)
    screening_disclaimer: str = Field(
        default=(
            "The Edinburgh Postnatal Depression Scale (EPDS) is a screening support instrument, "
            "NOT a medical or psychiatric diagnosis. An EPDS score should never override comprehensive clinical assessment."
        )
    )
    item_scores: List[ItemScoreResult]
    safety_alert: SafetyAlertResult
