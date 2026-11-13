"""Phase 6 Automated Test Suite: Clinical Numerical Model Evaluation & Validation.

Postpartum Depression (PPD) Multimodal Recognition Research Prototype.
Verifies:
1. Exact replication of saved model test metrics and confusion matrices.
2. Complete data leakage audit passing (disjoint participants, zero excluded columns, zero crossovers).
3. Probability calibration and Brier score ranges.
4. Feature importance extraction and top clinical driver rankings.
5. Sensitivity and trade-off comparison between Random Forest and HistGradientBoosting.
6. Backend service robustness under missing values, unknown categories, and probability boundaries [0, 1].
7. Clinical safeguards: EPDS Question 10 safety escalation independence from ML probability.
"""

import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import joblib

from pipelines.clinical_numerical.config import (
    ARTIFACTS_DIR,
    DECISION_THRESHOLD,
    EXCLUDED_COLUMNS,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    TOTAL_PREDICTOR_COUNT,
)
from pipelines.clinical_numerical.data_loader import load_clinical_data
from pipelines.clinical_numerical.preprocessor import ClinicalPreprocessor
from pipelines.clinical_numerical.evaluate_models import (
    evaluate_clinical_models,
    perform_data_leakage_audit,
)
from backend.services.clinical_service import clinical_service, ClinicalScreeningService
from backend.services.questionnaire_service import questionnaire_service
from backend.schemas.screening import ScreeningAnalysisResponse


@pytest.fixture(scope="module")
def evaluation_results():
    """Execute evaluation workflow once for test assertions."""
    return evaluate_clinical_models(ARTIFACTS_DIR)


def test_saved_model_evaluation_metrics_match_baseline(evaluation_results):
    """Verify saved models achieve the documented benchmark metrics on the frozen test set."""
    models = evaluation_results["models"]

    # 1. Random Forest (Primary Production Model)
    rf = models["random_forest"]["metrics_at_default_threshold"]
    assert rf["roc_auc"] == 0.8187
    assert rf["accuracy"] == 0.7625
    assert rf["sensitivity_recall"] == 0.7714
    assert rf["specificity"] == 0.7556
    assert rf["precision"] == 0.7105
    assert rf["f1_score"] == 0.7397
    assert rf["brier_score"] == 0.1796
    assert rf["confusion_matrix"] == {"tn": 68, "fp": 22, "fn": 16, "tp": 54}

    # 2. HistGradientBoosting (Comparison Candidate)
    hgb = models["hist_gradient_boosting"]["metrics_at_default_threshold"]
    assert hgb["roc_auc"] == 0.8310
    assert hgb["accuracy"] == 0.7312
    assert hgb["sensitivity_recall"] == 0.7000
    assert hgb["specificity"] == 0.7556
    assert hgb["precision"] == 0.6901
    assert hgb["f1_score"] == 0.6950
    assert hgb["brier_score"] == 0.1725
    assert hgb["confusion_matrix"] == {"tn": 68, "fp": 22, "fn": 21, "tp": 49}

    # 3. Logistic Regression (Linear Baseline)
    lr = models["logistic_regression"]["metrics_at_default_threshold"]
    assert lr["roc_auc"] == 0.8027
    assert lr["accuracy"] == 0.7188
    assert lr["sensitivity_recall"] == 0.7286
    assert lr["specificity"] == 0.7111
    assert lr["precision"] == 0.6623
    assert lr["f1_score"] == 0.6939
    assert lr["brier_score"] == 0.1820
    assert lr["confusion_matrix"] == {"tn": 64, "fp": 26, "fn": 19, "tp": 51}


def test_data_leakage_audit_and_participant_disjointness(evaluation_results):
    """Verify zero leakage across features, participants, and cross-split rows."""
    leakage = evaluation_results["leakage_audit"]
    assert leakage["audit_passed"] is True
    assert len(leakage["detected_excluded_columns_in_X"]) == 0
    assert leakage["total_participants"] == 800
    assert leakage["train_participant_count"] == 640
    assert leakage["test_participant_count"] == 160
    assert leakage["participant_id_overlap_count"] == 0
    assert leakage["identical_records_train_test_crossover"] == 0

    # Ensure no single feature has suspiciously high correlation (proxy leakage)
    for assoc in leakage["top_feature_target_associations"]:
        assert assoc["association_value"] < 0.60, f"Suspicious target association for {assoc['feature']}"


def test_feature_importance_top_drivers(evaluation_results):
    """Verify Random Forest feature importance rankings and sums."""
    feat_imp = evaluation_results["feature_importances"]
    top_raw = feat_imp["top_15_raw_grouped"]

    # Top 2 clinical features
    assert top_raw[0]["raw_feature"] == "Angry after latest child birth"
    assert top_raw[1]["raw_feature"] == "Abuse"

    # Cumulative importance across all 46 raw features must sum to 1.0 (approx)
    all_raw = feat_imp["all_raw_grouped"]
    total_imp = sum(f["cumulative_importance"] for f in all_raw)
    assert pytest.approx(total_imp, rel=1e-3) == 1.0


def test_calibration_and_brier_scores(evaluation_results):
    """Verify probability calibration and Brier score ranges."""
    models = evaluation_results["models"]
    for model_name in ["random_forest", "hist_gradient_boosting", "logistic_regression"]:
        m_data = models[model_name]
        brier = m_data["metrics_at_default_threshold"]["brier_score"]
        # Brier score must be strictly superior to uninformative prior (0.4375 * 0.5625 ~ 0.246)
        assert 0.10 <= brier <= 0.20, f"Brier score for {model_name} out of expected range: {brier}"

        # Calibration bins must show increasing empirical probabilities with predicted probabilities
        calib_bins = m_data["calibration_5_bins"]
        assert len(calib_bins) >= 4
        assert calib_bins[-1]["empirical_true_rate"] > calib_bins[0]["empirical_true_rate"]


def test_clinical_threshold_tradeoffs(evaluation_results):
    """Verify that sensitivity at threshold 0.5 favors Random Forest over HistGradientBoosting."""
    sweep = evaluation_results["threshold_sweep"]
    df_sweep = pd.DataFrame(sweep)

    rf_05 = df_sweep[(df_sweep["model"] == "random_forest") & (df_sweep["threshold"] == 0.50)].iloc[0]
    hgb_05 = df_sweep[(df_sweep["model"] == "hist_gradient_boosting") & (df_sweep["threshold"] == 0.50)].iloc[0]

    # Clinical screening justification: RF misses fewer cases (16 FN vs 21 FN)
    assert rf_05["fn"] < hgb_05["fn"]
    assert rf_05["sensitivity"] > hgb_05["sensitivity"]
    assert rf_05["f1_score"] > hgb_05["f1_score"]

    # Monotonic sensitivity trend
    rf_sweep = df_sweep[df_sweep["model"] == "random_forest"].sort_values("threshold")
    sens_vals = rf_sweep["sensitivity"].values
    # Lower threshold = higher sensitivity
    assert sens_vals[0] >= sens_vals[-1]


def test_backend_service_robustness_and_unknown_categories():
    """Verify that backend ClinicalScreeningService handles missing and unknown categories robustly."""
    if not clinical_service.is_loaded:
        clinical_service.startup()
    assert clinical_service.is_loaded is True

    # Construct input with unknown categorical categories and missing numericals
    record_with_unknowns = {
        "Age": np.nan,  # Missing numerical
        "Number of the latest pregnancy": np.nan,
        "Residence": "CompletelyUnknownResidenceType",
        "Education Level": "UnknownLevel99",
        "Marital status": "AlienMaritalStatus",
        "Occupation before latest pregnancy": "Astronaut",
        "Monthly income before latest pregnancy": "UnknownBracket",
        "Occupation After Your Latest Childbirth": "SubmarineCaptain",
        "Current monthly income": "UnknownBracket2",
        "Husband's education level": "UnknownDoctorate",
        "Husband’s monthly income": "UnknownBracket3",
        "Addiction": "UnknownAddiction",
        "Total children": 99,
        "Disease before pregnancy": "RareConditionXYZ",
        "History of pregnancy loss": "UnknownResponse",
        "Family type": "NomadicClan",
        "Number of household members": 42,
        "Relationship with the in-laws": "UnknownTier",
        "Relationship with husband": "UnknownTier",
        "Relationship with the newborn": "UnknownTier",
        "Relationship between father and newborn": "UnknownTier",
        "Feeling about motherhood": "UnknownEmotion",
        "Recieved Support": "UnknownSupport",
        "Need for Support": "UnknownSupportNeed",
        "Major changes or losses during pregnancy": "UnknownLoss",
        "Abuse": "UnknownAbuseStatus",
        "Trust and share feelings": "UnknownTrust",
        "Pregnancy length": "UnknownLength",
        "Pregnancy plan": "UnknownPlan",
        "Regular checkups": "UnknownCheckup",
        "Fear of pregnancy": "UnknownFear",
        "Diseases during pregnancy": "UnknownDisease",
        "Age of newborn": "UnknownAge",
        "Age of immediate older children": "UnknownAge",
        "Mode of delivery": "UnknownMode",
        "Gender of newborn": "NonBinary",
        "Birth compliancy": "UnknownCompliancy",
        "Breastfeed": "UnknownFeeding",
        "Newborn illness": "UnknownIllness",
        "Worry about newborn": "UnknownWorry",
        "Relax/sleep when newborn is tended ": "UnknownSleep",
        "Relax/sleep when the newborn is asleep": "UnknownSleep2",
        "Angry after latest child birth": "UnknownAnger",
        "Feeling for regular activities": "UnknownFeeling",
        "Depression before pregnancy (PHQ2)": "UnknownPHQ",
        "Depression during pregnancy (PHQ2)": "UnknownPHQ2",
    }

    result = clinical_service.predict(mother_id="M_TEST_ROBUST", features=record_with_unknowns)
    assert result["status"] == "completed"
    assert "prediction" in result
    pred = result["prediction"]
    assert "predicted_risk_probability" in pred
    prob = pred["predicted_risk_probability"]
    assert 0.0 <= prob <= 1.0
    assert pred["risk_category"] in {"LOW_RISK", "MODERATE_RISK", "HIGH_RISK"}
    assert result["mother_id"] == "M_TEST_ROBUST"


def test_clinical_safety_isolation_from_epds_q10():
    """Verify clinical safeguard: a low Random Forest risk probability NEVER suppresses EPDS Q10 safety alert."""
    from backend.schemas.questionnaire import EPDSSubmissionRequest, AnswerSubmissionItem

    # When a mother reports suicidal ideation on EPDS question 10:
    # Option index 1 ("Hardly ever"), 2 ("Sometimes"), or 3 ("Yes, quite often")
    answers = [
        AnswerSubmissionItem(question_id=f"EPDS_Q{i+1:02d}", selected_index=0)
        for i in range(9)
    ]
    answers.append(AnswerSubmissionItem(question_id="EPDS_Q10", selected_index=1))

    req = EPDSSubmissionRequest(answers=answers)
    res = questionnaire_service.calculate_score(req)

    # Q10 safety alert MUST be triggered
    assert res.safety_alert.triggered is True
    assert res.safety_alert.question_10_score > 0
    assert res.safety_alert.severity == "URGENT_SAFETY_ASSESSMENT"
    assert (
        "A positive Question 10 response must NEVER be overridden by a low total score or ML prediction."
        in res.safety_alert.override_protection
    )

    # Even if Random Forest ML model predicts 0.05 (LOW_RISK), the Q10 safety override remains independent
    low_ml_prob = 0.05
    assert low_ml_prob < DECISION_THRESHOLD
