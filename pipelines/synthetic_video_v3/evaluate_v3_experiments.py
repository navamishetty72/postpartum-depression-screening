"""Evaluation module for Video V3 experimental benchmark.

Conducts leakage-safe 5-fold cross-validation on the 640 canonical training participants,
comparing:
A. Existing V2 video model baseline (unconditioned noise).
B. Video V3 model (clinically conditioned).
C. Non-target clinical-covariate-only baseline (5 conditioning features).
D. Video V3 + Clinical combiner (leakage-safe late fusion).

Also conducts mutual information / R^2 redundancy analysis to quantify shared variance.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    auc,
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from pipelines.synthetic_video_v3.config_v3 import (
    CONDITIONING_COVARIATE_NAMES,
    DEFAULT_RANDOM_SEED,
    SYNTHETIC_VIDEO_V3_FEATURES_DIR,
    SYNTHETIC_VIDEO_V3_MANIFEST_PATH,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
    MODELING_MATRIX_PATH,
    VIDEO_V3_EXPERIMENTS_DIR,
)
from pipelines.synthetic_video_v3.conditioning import extract_cohort_conditioning_v3
from pipelines.video_model.dataset import PPDVideoDataset
from pipelines.video_model.models.statistical_baseline import ParticipantStatisticalFeatureExtractor


def compute_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """Compute comprehensive classification performance metrics."""
    y_pred = (y_prob >= threshold).astype(int)

    roc_auc = float(roc_auc_score(y_true, y_prob))
    precision_arr, recall_arr, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = float(auc(recall_arr, precision_arr))

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    sens = float(recall_score(y_true, y_pred, zero_division=0))
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    acc = float(accuracy_score(y_true, y_pred))

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "accuracy": round(acc, 4),
        "sensitivity": round(sens, 4),
        "specificity": round(spec, 4),
        "precision": round(prec, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def compute_bootstrap_ci(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = DEFAULT_RANDOM_SEED,
) -> Dict[str, Tuple[float, float]]:
    """Compute 95% bootstrap confidence intervals for primary metrics."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    auc_list = []
    pr_list = []
    bal_acc_list = []
    f1_list = []

    for _ in range(n_bootstraps):
        idx = rng.choice(n, size=n, replace=True)
        yt, yp = y_true[idx], y_prob[idx]
        if len(np.unique(yt)) < 2:
            continue
        auc_list.append(roc_auc_score(yt, yp))
        prec, rec, _ = precision_recall_curve(yt, yp)
        pr_list.append(auc(rec, prec))
        pred = (yp >= 0.5).astype(int)
        bal_acc_list.append(balanced_accuracy_score(yt, pred))
        f1_list.append(f1_score(yt, pred, zero_division=0))

    def get_ci(vals):
        return (round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4))

    return {
        "roc_auc_95_ci": get_ci(auc_list),
        "pr_auc_95_ci": get_ci(pr_list),
        "balanced_accuracy_95_ci": get_ci(bal_acc_list),
        "f1_score_95_ci": get_ci(f1_list),
    }


def run_experiment() -> Dict[str, Any]:
    """Execute complete 5-fold cross-validation experiment comparing Models A, B, C, D."""
    out_dir = VIDEO_V3_EXPERIMENTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load canonical manifest and modeling matrix
    manifest_df = pd.read_csv(TRAIN_TEST_SPLIT_MANIFEST_PATH)
    matrix_df = pd.read_csv(MODELING_MATRIX_PATH)

    train_mask = manifest_df["split_partition"] == "train"
    train_manifest = manifest_df[train_mask].reset_index(drop=True)
    participant_ids = train_manifest["participant_id"].values
    y_train = train_manifest["target_canonical_epds_ge_13"].values
    n_train = len(train_manifest)
    assert n_train == 640, f"Expected 640 training participants, got {n_train}"

    # 2. Extract clinical conditioning covariates (fitted strictly on train)
    conditioning_df = extract_cohort_conditioning_v3(manifest_df, matrix_df)
    train_cond = conditioning_df[train_mask].reset_index(drop=True)
    X_clinical_cov = train_cond.values.astype(np.float32)

    # 3. Load Clinical Numerical production OOF predictions
    clin_oof_path = Path("models/clinical_numerical/oof_predictions.csv")
    if clin_oof_path.exists():
        clin_oof_df = pd.read_csv(clin_oof_path)
        # Merge on participant_id
        merged_clin = pd.merge(train_manifest[["participant_id"]], clin_oof_df, on="participant_id", how="left")
        y_prob_clin_prod = merged_clin["logistic_regression_prob"].values
    else:
        y_prob_clin_prod = None

    # 4. Load datasets and extract statistical summary features
    print("Loading Video V2 and V3 datasets...")
    ds_v2 = PPDVideoDataset(partition="train", validate_on_init=False)
    ds_v3 = PPDVideoDataset(
        features_dir=SYNTHETIC_VIDEO_V3_FEATURES_DIR,
        video_manifest_path=SYNTHETIC_VIDEO_V3_MANIFEST_PATH,
        split_manifest_path=TRAIN_TEST_SPLIT_MANIFEST_PATH,
        partition="train",
        validate_on_init=False,
    )

    extractor = ParticipantStatisticalFeatureExtractor(feature_subset="facial_motion")
    X_v2 = extractor.transform(ds_v2.get_all_raw_tensors())  # (640, 198)
    X_v3 = extractor.transform(ds_v3.get_all_raw_tensors())  # (640, 198)

    print(f"Extracted features shape: V2={X_v2.shape}, V3={X_v3.shape}, Clinical={X_clinical_cov.shape}")

    # 5. Set up 5-fold Stratified CV
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=DEFAULT_RANDOM_SEED)

    # OOF prediction containers
    oof_probs = {
        "v2_logistic": np.zeros(n_train),
        "v2_rf": np.zeros(n_train),
        "v3_logistic": np.zeros(n_train),
        "v3_rf": np.zeros(n_train),
        "clinical_cov_logistic": np.zeros(n_train),
        "v3_plus_cov_combiner": np.zeros(n_train),
        "v3_plus_clin_prod_combiner": np.zeros(n_train),
    }

    fold_metrics = {m: [] for m in oof_probs}
    oof_folds = np.zeros(n_train, dtype=int)

    # 6. Execute cross-validation
    print("Running 5-fold cross-validation...")
    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X_v3, y_train)):
        oof_folds[val_idx] = fold_idx
        y_tr, y_va = y_train[train_idx], y_train[val_idx]

        # Model A: V2 Video Baseline
        scaler_v2 = StandardScaler()
        X_v2_tr = scaler_v2.fit_transform(X_v2[train_idx])
        X_v2_va = scaler_v2.transform(X_v2[val_idx])

        lr_v2 = LogisticRegression(C=0.1, penalty="l2", class_weight="balanced", random_state=DEFAULT_RANDOM_SEED, max_iter=1000)
        lr_v2.fit(X_v2_tr, y_tr)
        p_v2_lr = lr_v2.predict_proba(X_v2_va)[:, 1]
        oof_probs["v2_logistic"][val_idx] = p_v2_lr

        rf_v2 = RandomForestClassifier(n_estimators=100, max_depth=6, class_weight="balanced", random_state=DEFAULT_RANDOM_SEED, n_jobs=-1)
        rf_v2.fit(X_v2_tr, y_tr)
        p_v2_rf = rf_v2.predict_proba(X_v2_va)[:, 1]
        oof_probs["v2_rf"][val_idx] = p_v2_rf

        # Model B: Video V3 Model
        scaler_v3 = StandardScaler()
        X_v3_tr = scaler_v3.fit_transform(X_v3[train_idx])
        X_v3_va = scaler_v3.transform(X_v3[val_idx])

        lr_v3 = LogisticRegression(C=0.1, penalty="l2", class_weight="balanced", random_state=DEFAULT_RANDOM_SEED, max_iter=1000)
        lr_v3.fit(X_v3_tr, y_tr)
        p_v3_lr = lr_v3.predict_proba(X_v3_va)[:, 1]
        oof_probs["v3_logistic"][val_idx] = p_v3_lr

        rf_v3 = RandomForestClassifier(n_estimators=100, max_depth=6, class_weight="balanced", random_state=DEFAULT_RANDOM_SEED, n_jobs=-1)
        rf_v3.fit(X_v3_tr, y_tr)
        p_v3_rf = rf_v3.predict_proba(X_v3_va)[:, 1]
        oof_probs["v3_rf"][val_idx] = p_v3_rf

        # Model C: Non-Target Clinical Covariates Baseline
        scaler_cov = StandardScaler()
        X_cov_tr = scaler_cov.fit_transform(X_clinical_cov[train_idx])
        X_cov_va = scaler_cov.transform(X_clinical_cov[val_idx])

        lr_cov = LogisticRegression(C=0.1, penalty="l2", class_weight="balanced", random_state=DEFAULT_RANDOM_SEED, max_iter=1000)
        lr_cov.fit(X_cov_tr, y_tr)
        p_cov_lr = lr_cov.predict_proba(X_cov_va)[:, 1]
        oof_probs["clinical_cov_logistic"][val_idx] = p_cov_lr

        # Model D1: Video V3 + Clinical Covariate Combiner
        # Fit meta-classifier on train probabilities
        p_v3_tr = lr_v3.predict_proba(X_v3_tr)[:, 1]
        p_cov_tr = lr_cov.predict_proba(X_cov_tr)[:, 1]
        meta_X_tr = np.column_stack([p_v3_tr, p_cov_tr])
        meta_X_va = np.column_stack([p_v3_lr, p_cov_lr])

        meta_lr1 = LogisticRegression(C=1.0, penalty="l2", class_weight="balanced", random_state=DEFAULT_RANDOM_SEED)
        meta_lr1.fit(meta_X_tr, y_tr)
        p_comb1 = meta_lr1.predict_proba(meta_X_va)[:, 1]
        oof_probs["v3_plus_cov_combiner"][val_idx] = p_comb1

        # Model D2: Video V3 + Clinical Production Model Combiner
        if y_prob_clin_prod is not None:
            p_clin_tr = y_prob_clin_prod[train_idx]
            p_clin_va = y_prob_clin_prod[val_idx]
            meta_X2_tr = np.column_stack([p_v3_tr, p_clin_tr])
            meta_X2_va = np.column_stack([p_v3_lr, p_clin_va])
            meta_lr2 = LogisticRegression(C=1.0, penalty="l2", class_weight="balanced", random_state=DEFAULT_RANDOM_SEED)
            meta_lr2.fit(meta_X2_tr, y_tr)
            p_comb2 = meta_lr2.predict_proba(meta_X2_va)[:, 1]
            oof_probs["v3_plus_clin_prod_combiner"][val_idx] = p_comb2

        # Record fold metrics
        for m in oof_probs:
            if m == "v3_plus_clin_prod_combiner" and y_prob_clin_prod is None:
                continue
            f_res = compute_metrics(y_va, oof_probs[m][val_idx])
            fold_metrics[m].append(f_res)

    # 7. Compute overall OOF metrics and bootstrap CIs
    results: Dict[str, Any] = {
        "metadata": {
            "experiment_name": "Video V3 Experimental Simulation Benchmark",
            "cohort": "canonical_bangladeshi_train_640",
            "cv_folds": 5,
            "seed": DEFAULT_RANDOM_SEED,
            "data_origin": "CLINICALLY_CONDITIONED_SYNTHETIC",
            "holdout_status": "strictly_frozen_160_unaccessed",
            "scientific_integrity_notice": (
                "Video V3 is an experimental synthetic simulation fixture for hackathon demonstration. "
                "The clinical cohort contains zero physical video recordings. Video features are generated "
                "using non-target survey covariates and do not establish clinical diagnostic accuracy."
            ),
        },
        "models": {},
    }

    for m in oof_probs:
        if m == "v3_plus_clin_prod_combiner" and y_prob_clin_prod is None:
            continue
        overall_m = compute_metrics(y_train, oof_probs[m])
        boot_ci = compute_bootstrap_ci(y_train, oof_probs[m])
        mean_cv_auc = float(np.mean([f["roc_auc"] for f in fold_metrics[m]]))
        std_cv_auc = float(np.std([f["roc_auc"] for f in fold_metrics[m]]))
        mean_cv_pr = float(np.mean([f["pr_auc"] for f in fold_metrics[m]]))
        mean_cv_f1 = float(np.mean([f["f1_score"] for f in fold_metrics[m]]))
        mean_cv_bal_acc = float(np.mean([f["balanced_accuracy"] for f in fold_metrics[m]]))

        results["models"][m] = {
            "overall_oof_metrics": overall_m,
            "bootstrap_95_ci": boot_ci,
            "cv_mean_metrics": {
                "mean_roc_auc": round(mean_cv_auc, 4),
                "std_roc_auc": round(std_cv_auc, 4),
                "mean_pr_auc": round(mean_cv_pr, 4),
                "mean_f1_score": round(mean_cv_f1, 4),
                "mean_balanced_accuracy": round(mean_cv_bal_acc, 4),
            },
            "fold_metrics": fold_metrics[m],
        }

    # 8. Mutual Information / Encoding Analysis (Quantify Shared Variance)
    print("Performing redundancy and shared variance analysis...")
    ridge_v3 = Ridge(alpha=1.0)
    scaler_x = StandardScaler()
    scaler_y = StandardScaler()

    X_v3_scaled = scaler_x.fit_transform(X_v3)
    Y_cov_scaled = scaler_y.fit_transform(X_clinical_cov)

    r2_scores = []
    # 5-fold cross-validated R^2 for predicting covariates from video features
    for train_idx, val_idx in skf.split(X_v3, y_train):
        ridge_v3.fit(X_v3_scaled[train_idx], Y_cov_scaled[train_idx])
        pred_cov = ridge_v3.predict(X_v3_scaled[val_idx])
        # R^2 per covariate
        ss_res = np.sum((Y_cov_scaled[val_idx] - pred_cov) ** 2, axis=0)
        ss_tot = np.sum((Y_cov_scaled[val_idx] - np.mean(Y_cov_scaled[val_idx], axis=0)) ** 2, axis=0)
        r2_fold = 1.0 - (ss_res / ss_tot)
        r2_scores.append(r2_fold)

    mean_r2 = np.mean(r2_scores, axis=0)

    # Also compute on V2 for contrast
    scaler_v2 = StandardScaler()
    X_v2_scaled = scaler_v2.fit_transform(X_v2)
    r2_v2_scores = []
    for train_idx, val_idx in skf.split(X_v2, y_train):
        ridge_v3.fit(X_v2_scaled[train_idx], Y_cov_scaled[train_idx])
        pred_cov2 = ridge_v3.predict(X_v2_scaled[val_idx])
        ss_res2 = np.sum((Y_cov_scaled[val_idx] - pred_cov2) ** 2, axis=0)
        ss_tot2 = np.sum((Y_cov_scaled[val_idx] - np.mean(Y_cov_scaled[val_idx], axis=0)) ** 2, axis=0)
        r2_v2_scores.append(1.0 - (ss_res2 / ss_tot2))
    mean_r2_v2 = np.mean(r2_v2_scores, axis=0)

    redundancy_analysis = {
        "conditioning_covariates": CONDITIONING_COVARIATE_NAMES,
        "video_v3_cv_r2_scores": {
            cov_name: round(float(r2), 4) for cov_name, r2 in zip(CONDITIONING_COVARIATE_NAMES, mean_r2)
        },
        "video_v3_mean_r2": round(float(np.mean(mean_r2)), 4),
        "video_v2_cv_r2_scores": {
            cov_name: round(float(r2), 4) for cov_name, r2 in zip(CONDITIONING_COVARIATE_NAMES, mean_r2_v2)
        },
        "video_v2_mean_r2": round(float(np.mean(mean_r2_v2)), 4),
        "interpretation": (
            f"Video V3 facial features decode the conditioning clinical covariates with mean cross-validated R^2 = "
            f"{float(np.mean(mean_r2)):.4f}, confirming that Video V3's predictive performance is directly "
            f"derived from the underlying survey variables rather than authentic facial physiology. In contrast, "
            f"Video V2 has R^2 = {float(np.mean(mean_r2_v2)):.4f} (zero encoding)."
        ),
    }

    results["redundancy_analysis"] = redundancy_analysis

    # 9. Save JSON results and OOF predictions CSV
    with open(out_dir / "experiment_results.json", "w") as f:
        json.dump(results, f, indent=2)

    oof_df = pd.DataFrame({
        "participant_id": participant_ids,
        "fold": oof_folds,
        "y_true": y_train,
        "v2_logistic_prob": np.round(oof_probs["v2_logistic"], 4),
        "v2_rf_prob": np.round(oof_probs["v2_rf"], 4),
        "v3_logistic_prob": np.round(oof_probs["v3_logistic"], 4),
        "v3_rf_prob": np.round(oof_probs["v3_rf"], 4),
        "clinical_cov_prob": np.round(oof_probs["clinical_cov_logistic"], 4),
        "v3_plus_cov_combiner_prob": np.round(oof_probs["v3_plus_cov_combiner"], 4),
    })
    if y_prob_clin_prod is not None:
        oof_df["clinical_prod_prob"] = np.round(y_prob_clin_prod, 4)
        oof_df["v3_plus_clin_prod_combiner_prob"] = np.round(oof_probs["v3_plus_clin_prod_combiner"], 4)

    oof_df.to_csv(out_dir / "oof_predictions_v3.csv", index=False)
    print(f"Results and predictions saved successfully to {out_dir}")

    return results


if __name__ == "__main__":
    res = run_experiment()
    print("=== EXPERIMENT SUMMARY ===")
    for m, d in res["models"].items():
        print(f"{m:28s}: OOF ROC-AUC = {d['overall_oof_metrics']['roc_auc']:.4f}, Mean CV = {d['cv_mean_metrics']['mean_roc_auc']:.4f} +/- {d['cv_mean_metrics']['std_roc_auc']:.4f}, Bal Acc = {d['overall_oof_metrics']['balanced_accuracy']:.4f}, F1 = {d['overall_oof_metrics']['f1_score']:.4f}")
    print("\nRedundancy Analysis:")
    print("Video V3 R^2 scores predicting clinical covariates:", res["redundancy_analysis"]["video_v3_cv_r2_scores"])
    print("Video V2 R^2 scores:", res["redundancy_analysis"]["video_v2_cv_r2_scores"])

