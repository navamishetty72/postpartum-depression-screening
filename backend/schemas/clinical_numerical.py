"""Pydantic v2 schemas for the Clinical Numerical ML prediction service.

Validates the complete 46-feature clinical survey schema, enforces strict target leakage
isolation, and provides structured prediction outputs matching the trained pipeline.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from pipelines.clinical_numerical.config import (
    CATEGORICAL_FEATURES,
    EXCLUDED_COLUMNS,
    NUMERICAL_FEATURES,
    TOTAL_PREDICTOR_COUNT,
)


class ClinicalFeatures(BaseModel):
    """Schema validating all 46 clinical survey predictors.

    Preserves exact feature spelling, capitalization, and trailing whitespace.
    Allows None/null where existing preprocessing imputers support missing values.
    Disallows target leakage and unknown features via extra='forbid'.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # --- 2 Numerical Predictors ---
    age: Optional[float] = Field(..., alias="Age", description="Participant age in years")
    number_of_the_latest_pregnancy: Optional[float] = Field(
        ...,
        alias="Number of the latest pregnancy",
        description="Gravidity / pregnancy parity count",
    )

    # --- 44 Categorical Predictors ---
    residence: Optional[Union[str, int, float]] = Field(..., alias="Residence")
    education_level: Optional[Union[str, int, float]] = Field(..., alias="Education Level")
    marital_status: Optional[Union[str, int, float]] = Field(..., alias="Marital status")
    occupation_before_latest_pregnancy: Optional[Union[str, int, float]] = Field(
        ..., alias="Occupation before latest pregnancy"
    )
    monthly_income_before_latest_pregnancy: Optional[Union[str, int, float]] = Field(
        ..., alias="Monthly income before latest pregnancy"
    )
    occupation_after_your_latest_childbirth: Optional[Union[str, int, float]] = Field(
        ..., alias="Occupation After Your Latest Childbirth"
    )
    current_monthly_income: Optional[Union[str, int, float]] = Field(
        ..., alias="Current monthly income"
    )
    husband_s_education_level: Optional[Union[str, int, float]] = Field(
        ..., alias="Husband's education level"
    )
    husband_s_monthly_income: Optional[Union[str, int, float]] = Field(
        ..., alias="Husband’s monthly income"
    )
    addiction: Optional[Union[str, int, float]] = Field(..., alias="Addiction")
    total_children: Optional[Union[str, int, float]] = Field(..., alias="Total children")
    disease_before_pregnancy: Optional[Union[str, int, float]] = Field(
        ..., alias="Disease before pregnancy"
    )
    history_of_pregnancy_loss: Optional[Union[str, int, float]] = Field(
        ..., alias="History of pregnancy loss"
    )
    family_type: Optional[Union[str, int, float]] = Field(..., alias="Family type")
    number_of_household_members: Optional[Union[str, int, float]] = Field(
        ..., alias="Number of household members"
    )
    relationship_with_the_in_laws: Optional[Union[str, int, float]] = Field(
        ..., alias="Relationship with the in-laws"
    )
    relationship_with_husband: Optional[Union[str, int, float]] = Field(
        ..., alias="Relationship with husband"
    )
    relationship_with_the_newborn: Optional[Union[str, int, float]] = Field(
        ..., alias="Relationship with the newborn"
    )
    relationship_between_father_and_newborn: Optional[Union[str, int, float]] = Field(
        ..., alias="Relationship between father and newborn"
    )
    feeling_about_motherhood: Optional[Union[str, int, float]] = Field(
        ..., alias="Feeling about motherhood"
    )
    recieved_support: Optional[Union[str, int, float]] = Field(..., alias="Recieved Support")
    need_for_support: Optional[Union[str, int, float]] = Field(..., alias="Need for Support")
    major_changes_or_losses_during_pregnancy: Optional[Union[str, int, float]] = Field(
        ..., alias="Major changes or losses during pregnancy"
    )
    abuse: Optional[Union[str, int, float]] = Field(..., alias="Abuse")
    trust_and_share_feelings: Optional[Union[str, int, float]] = Field(
        ..., alias="Trust and share feelings"
    )
    pregnancy_length: Optional[Union[str, int, float]] = Field(..., alias="Pregnancy length")
    pregnancy_plan: Optional[Union[str, int, float]] = Field(..., alias="Pregnancy plan")
    regular_checkups: Optional[Union[str, int, float]] = Field(..., alias="Regular checkups")
    fear_of_pregnancy: Optional[Union[str, int, float]] = Field(..., alias="Fear of pregnancy")
    diseases_during_pregnancy: Optional[Union[str, int, float]] = Field(
        ..., alias="Diseases during pregnancy"
    )
    age_of_newborn: Optional[Union[str, int, float]] = Field(..., alias="Age of newborn")
    age_of_immediate_older_children: Optional[Union[str, int, float]] = Field(
        ..., alias="Age of immediate older children"
    )
    mode_of_delivery: Optional[Union[str, int, float]] = Field(..., alias="Mode of delivery")
    gender_of_newborn: Optional[Union[str, int, float]] = Field(..., alias="Gender of newborn")
    birth_compliancy: Optional[Union[str, int, float]] = Field(..., alias="Birth compliancy")
    breastfeed: Optional[Union[str, int, float]] = Field(..., alias="Breastfeed")
    newborn_illness: Optional[Union[str, int, float]] = Field(..., alias="Newborn illness")
    worry_about_newborn: Optional[Union[str, int, float]] = Field(..., alias="Worry about newborn")
    relax_sleep_when_newborn_is_tended: Optional[Union[str, int, float]] = Field(
        ..., alias="Relax/sleep when newborn is tended "
    )
    relax_sleep_when_the_newborn_is_asleep: Optional[Union[str, int, float]] = Field(
        ..., alias="Relax/sleep when the newborn is asleep"
    )
    angry_after_latest_child_birth: Optional[Union[str, int, float]] = Field(
        ..., alias="Angry after latest child birth"
    )
    feeling_for_regular_activities: Optional[Union[str, int, float]] = Field(
        ..., alias="Feeling for regular activities"
    )
    depression_before_pregnancy_phq2: Optional[Union[str, int, float]] = Field(
        ..., alias="Depression before pregnancy (PHQ2)"
    )
    depression_during_pregnancy_phq2: Optional[Union[str, int, float]] = Field(
        ..., alias="Depression during pregnancy (PHQ2)"
    )

    def to_feature_dict(self) -> Dict[str, Any]:
        """Convert validated schema into exact DataFrame column dictionary with correct aliases."""
        return self.model_dump(by_alias=True)


class ClinicalPredictionRequest(BaseModel):
    """Request payload for single-patient clinical numerical PPD screening."""

    model_config = ConfigDict(extra="forbid")

    mother_id: str = Field(
        ...,
        min_length=1,
        description="Patient or participant identifier (e.g., 'M-104', UUID, or anonymized ID)",
    )
    features: ClinicalFeatures = Field(
        ...,
        description="Dictionary containing all 46 clinical survey predictor features",
    )


class PredictionDetails(BaseModel):
    """Core prediction outputs computed by the clinical model."""

    predicted_risk_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Predicted probability of high risk for PPD (EPDS >= 13)",
    )
    predicted_class: int = Field(
        ...,
        ge=0,
        le=1,
        description="Binary screening classification (1 = High Risk, 0 = Low Risk)",
    )
    risk_category: str = Field(
        ...,
        description="Categorical risk tier: 'HIGH_RISK', 'MODERATE_RISK', or 'LOW_RISK'",
    )
    decision_threshold: float = Field(
        default=0.5,
        description="Operating threshold applied to predicted risk probability",
    )


class ClinicalPredictionResponse(BaseModel):
    """Structured response returned by POST /api/clinical/predict."""

    mother_id: str = Field(..., description="Patient or participant identifier")
    status: str = Field(default="completed", description="Inference pipeline execution status")
    prediction: PredictionDetails = Field(..., description="Model prediction output")
    model_utilized: str = Field(
        ...,
        description="Underlying baseline model name (e.g., 'random_forest')",
    )
    data_origin: str = Field(
        default="REAL_CLINICAL_SURVEY",
        description="Provenance classification tag for the input feature domain",
    )
    clinical_disclaimer: str = Field(
        default="Research Prototype Benchmark Only — Not Clinically Validated for Medical Diagnosis",
        description="Clinical safety and non-diagnostic research disclaimer",
    )


# --- Feature Information Endpoint Schemas ---


class FeatureItemSchema(BaseModel):
    """Metadata describing a single clinical survey feature."""

    name: str = Field(..., description="Exact column name matching survey matrix")
    feature_type: str = Field(..., description="'numerical' or 'categorical'")
    supports_missing_values: bool = Field(
        default=True,
        description="Whether missing values (null) are handled by median/constant imputation",
    )


class ClinicalFeaturesInfoResponse(BaseModel):
    """Response returned by GET /api/clinical/features."""

    total_features: int = Field(default=TOTAL_PREDICTOR_COUNT)
    numerical_count: int = Field(default=len(NUMERICAL_FEATURES))
    categorical_count: int = Field(default=len(CATEGORICAL_FEATURES))
    numerical_features: List[str] = Field(default_factory=lambda: list(NUMERICAL_FEATURES))
    categorical_features: List[str] = Field(default_factory=lambda: list(CATEGORICAL_FEATURES))
    features: List[FeatureItemSchema]
    prohibited_features: List[str] = Field(default_factory=lambda: list(EXCLUDED_COLUMNS))

