"""FastAPI router for Clinical Numerical ML screening inference.

Exposes:
- POST /api/clinical/predict: Clinical risk screening prediction from 46 survey features.
- GET /api/clinical/features: Metadata and typing for all required clinical predictors.

Research Prototype Benchmark Only — Not Clinically Validated for Medical Diagnosis.
Does NOT modify or override EPDS questionnaire scores or Item 10 crisis escalation.
"""

from fastapi import APIRouter, Depends

from backend.schemas.clinical_numerical import (
    ClinicalFeaturesInfoResponse,
    ClinicalPredictionRequest,
    ClinicalPredictionResponse,
    FeatureItemSchema,
)
from backend.services.clinical_service import (
    ClinicalScreeningService,
    get_clinical_service,
)
from pipelines.clinical_numerical.config import (
    CATEGORICAL_FEATURES,
    EXCLUDED_COLUMNS,
    NUMERICAL_FEATURES,
    TOTAL_PREDICTOR_COUNT,
)

router = APIRouter(
    prefix="/api/clinical",
    tags=["Clinical Numerical Screening"],
)


@router.post(
    "/predict",
    response_model=ClinicalPredictionResponse,
    summary="Predict postpartum depression risk from clinical survey predictors",
    description=(
        "Executes screening inference on pre-trained Random Forest model trained on clinical survey "
        "predictors. Evaluates risk associated with EPDS >= 13 threshold. "
        "Research Prototype Benchmark Only — Not Clinically Validated for Medical Diagnosis."
    ),
)
def predict_clinical_risk(
    payload: ClinicalPredictionRequest,
    service: ClinicalScreeningService = Depends(get_clinical_service),
) -> ClinicalPredictionResponse:
    """Execute clinical numerical risk prediction for a single mother record."""
    feature_dict = payload.features.to_feature_dict()
    result = service.predict(mother_id=payload.mother_id, features=feature_dict)
    return ClinicalPredictionResponse(**result)


@router.get(
    "/features",
    response_model=ClinicalFeaturesInfoResponse,
    summary="Retrieve required clinical predictor feature definitions",
    description=(
        "Returns the complete schema of 46 clinical survey predictors (2 numerical, 44 categorical), "
        "their expected types, imputation handling status, and strictly excluded target leakage columns. "
        "Derived directly from pipelines.clinical_numerical.config."
    ),
)
def get_clinical_features() -> ClinicalFeaturesInfoResponse:
    """Retrieve the authoritative feature configuration for clinical survey prediction."""
    feature_items = [
        FeatureItemSchema(
            name=feat,
            feature_type="numerical",
            supports_missing_values=True,
        )
        for feat in NUMERICAL_FEATURES
    ] + [
        FeatureItemSchema(
            name=feat,
            feature_type="categorical",
            supports_missing_values=True,
        )
        for feat in CATEGORICAL_FEATURES
    ]

    return ClinicalFeaturesInfoResponse(
        total_features=TOTAL_PREDICTOR_COUNT,
        numerical_count=len(NUMERICAL_FEATURES),
        categorical_count=len(CATEGORICAL_FEATURES),
        numerical_features=list(NUMERICAL_FEATURES),
        categorical_features=list(CATEGORICAL_FEATURES),
        features=feature_items,
        prohibited_features=list(EXCLUDED_COLUMNS),
    )

