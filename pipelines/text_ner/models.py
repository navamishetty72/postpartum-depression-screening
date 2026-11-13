"""Model definition and persistence for Text Named Entity Recognition.

Implements a high-efficiency token-level sequence classifier using scikit-learn
vectorization and calibrated probability estimation.
"""

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.svm import LinearSVC

from pipelines.text_ner.features import (
    align_spans_to_bio,
    bio_to_spans,
    extract_document_features,
    tokenize_with_offsets,
)


def viterbi_decode_bio(
    proba: np.ndarray,
    classes: List[str],
    entity_bias: float = 0.0,
    b_to_i_bonus: float = 0.0,
    i_to_i_bonus: float = 0.0,
) -> Tuple[List[str], List[float]]:
    """Decode a BIO tag sequence via Viterbi while forbidding invalid O -> I transitions."""
    n_tok = int(proba.shape[0])
    if n_tok == 0:
        return [], []

    required = ("O", "B-MMLite", "I-MMLite")
    if not all(lbl in classes for lbl in required):
        best_idx = np.argmax(proba, axis=1)
        tags = [classes[int(idx)] for idx in best_idx]
        confs = [round(float(proba[t, int(best_idx[t])]), 4) for t in range(n_tok)]
        return tags, confs

    idx_o = classes.index("O")
    idx_b = classes.index("B-MMLite")
    idx_i = classes.index("I-MMLite")

    log_p = np.log(np.clip(proba, 1e-9, 1.0))
    s_o = log_p[:, idx_o].tolist()
    s_b = (log_p[:, idx_b] + entity_bias).tolist()
    s_i = (log_p[:, idx_i] + entity_bias).tolist()

    dp0 = s_o[0]
    dp1 = s_b[0]
    dp2 = -1e12  # A sequence cannot start with I-MMLite.
    back: List[Tuple[int, int, int]] = [(0, 0, 0)]

    for t in range(1, n_tok):
        if dp0 >= dp1 and dp0 >= dp2:
            best_ob_prev, best_ob_val = 0, dp0
        elif dp1 >= dp2:
            best_ob_prev, best_ob_val = 1, dp1
        else:
            best_ob_prev, best_ob_val = 2, dp2

        c1 = dp1 + b_to_i_bonus
        c2 = dp2 + i_to_i_bonus
        if c1 >= c2:
            best_i_prev, best_i_val = 1, c1
        else:
            best_i_prev, best_i_val = 2, c2

        dp0 = best_ob_val + s_o[t]
        dp1 = best_ob_val + s_b[t]
        dp2 = best_i_val + s_i[t]
        back.append((best_ob_prev, best_ob_prev, best_i_prev))

    states = [0] * n_tok
    if dp0 >= dp1 and dp0 >= dp2:
        states[-1] = 0
    elif dp1 >= dp2:
        states[-1] = 1
    else:
        states[-1] = 2

    for t in range(n_tok - 1, 0, -1):
        states[t - 1] = back[t][states[t]]

    state_names = ("O", "B-MMLite", "I-MMLite")
    state_cls_idx = (idx_o, idx_b, idx_i)
    tags = [state_names[s] for s in states]
    confs = [round(float(proba[t, state_cls_idx[states[t]]]), 4) for t in range(n_tok)]
    return tags, confs


class TextNERModel:
    """Token-level NER model wrapping DictVectorizer and a linear sequence classifier."""

    def __init__(
        self,
        classifier_type: str = "sgd",
        loss: str = "modified_huber",
        c_param: float = 1.0,
        max_iter: int = 500,
        random_state: int = 42,
        class_weight: Any = "balanced",
        window: int = 2,
        model_version: str = "1.1.0",
        dtype: Any = np.float64,
        feature_version: str = "v1",
        min_feature_freq: int = 1,
        average: bool = False,
        use_viterbi: bool = False,
        decode_entity_bias: float = 0.0,
        decode_b_to_i_bonus: float = 0.0,
        decode_i_to_i_bonus: float = 0.0,
    ) -> None:
        self.classifier_type = classifier_type
        self.loss = loss
        self.c_param = c_param
        self.max_iter = max_iter
        self.random_state = random_state
        self.class_weight = class_weight
        self.window = window
        self.model_version = model_version
        self.dtype = dtype
        self.feature_version = feature_version
        self.min_feature_freq = min_feature_freq
        self.average = average
        self.use_viterbi = use_viterbi
        self.decode_entity_bias = decode_entity_bias
        self.decode_b_to_i_bonus = decode_b_to_i_bonus
        self.decode_i_to_i_bonus = decode_i_to_i_bonus
        self.training_metadata: Dict[str, Any] = {}

        self.vectorizer = DictVectorizer(sparse=True, dtype=self.dtype)
        if classifier_type == "logistic":
            self.classifier = LogisticRegression(
                C=c_param,
                max_iter=max_iter,
                random_state=random_state,
                class_weight=class_weight,
                solver="liblinear",
            )
        elif classifier_type == "logistic_lbfgs":
            self.classifier = LogisticRegression(
                C=c_param,
                max_iter=max_iter,
                random_state=random_state,
                class_weight=class_weight,
                solver="lbfgs",
            )
        elif classifier_type == "linear_svc":
            self.classifier = LinearSVC(
                C=c_param,
                class_weight=class_weight,
                max_iter=max_iter,
                random_state=random_state,
                dual="auto",
            )
        else:
            self.classifier = SGDClassifier(
                loss=loss,
                alpha=1.0 / (c_param * 1000.0) if c_param > 0 else 1e-4,
                max_iter=max_iter,
                random_state=random_state,
                class_weight=class_weight,
                average=average,
            )
        self.is_fitted = False
        self.classes_: Optional[np.ndarray] = None

    def _ensure_32bit_indices(self, matrix: Any) -> Any:
        """Ensure sparse matrix indices are 32-bit integers for scikit-learn Cython compatibility."""
        if hasattr(matrix, "indices") and matrix.indices.dtype != np.int32:
            matrix.indices = matrix.indices.astype(np.int32)
        if hasattr(matrix, "indptr") and matrix.indptr.dtype != np.int32:
            matrix.indptr = matrix.indptr.astype(np.int32)
        return matrix

    def fit(self, X_dicts: List[Dict[str, Any]], y_tags: List[str]) -> "TextNERModel":
        """Fit vectorizer and sequence classifier on token feature dictionaries."""
        if not X_dicts or not y_tags:
            raise ValueError("Cannot fit model on empty feature or label sets.")

        X_matrix = self.vectorizer.fit_transform(X_dicts)
        X_matrix = self._ensure_32bit_indices(X_matrix)
        self.classifier.fit(X_matrix, y_tags)
        self.classes_ = self.classifier.classes_
        self.is_fitted = True
        return self

    def fit_documents(
        self,
        docs: List[Any],
        chunk_size: int = 250,
    ) -> Dict[str, int]:
        """Memory-safe streaming fit across Document objects using chunked sparse vectorization.

        Avoids holding all raw feature dictionaries in RAM at once while producing
        the exact same vocabulary and CSR sparse matrix as ``DictVectorizer.fit_transform``.
        """
        import gc
        import scipy.sparse as sp

        if not docs:
            raise ValueError("Cannot fit model on empty document list.")

        feature_version = getattr(self, "feature_version", "v1")
        min_freq = int(getattr(self, "min_feature_freq", 1))

        # Pass 1: discover exact union (and optional token frequency) of DictVectorizer features
        feature_vocab: set[str] = set()
        feature_counts: Optional[Counter[str]] = Counter() if min_freq > 1 else None
        total_tokens = 0
        non_empty_docs = 0

        for start in range(0, len(docs), chunk_size):
            batch_dicts: List[Dict[str, Any]] = []
            for doc in docs[start : start + chunk_size]:
                tokens = tokenize_with_offsets(doc.text)
                if not tokens:
                    continue
                non_empty_docs += 1
                total_tokens += len(tokens)
                batch_dicts.extend(
                    extract_document_features(
                        tokens,
                        window=self.window,
                        text=doc.text,
                        feature_version=feature_version,
                    )
                )
            if batch_dicts:
                temp_vec = DictVectorizer(sparse=True)
                if feature_counts is not None:
                    temp_csr = temp_vec.fit_transform(batch_dicts)
                    temp_csr.eliminate_zeros()
                    counts = temp_csr.getnnz(axis=0)
                    for name, cnt in zip(temp_vec.feature_names_, counts):
                        if cnt > 0:
                            feature_counts[name] += int(cnt)
                    del temp_csr, counts
                else:
                    temp_vec.fit(batch_dicts)
                    feature_vocab.update(temp_vec.feature_names_)
                del batch_dicts, temp_vec

        if total_tokens == 0:
            raise ValueError("No non-empty tokenized documents provided for training.")

        if feature_counts is not None:
            sorted_features = sorted(name for name, cnt in feature_counts.items() if cnt >= min_freq)
            del feature_counts
        else:
            sorted_features = sorted(feature_vocab)
        self.vectorizer = DictVectorizer(sparse=True, dtype=self.dtype)
        self.vectorizer.feature_names_ = sorted_features
        self.vectorizer.vocabulary_ = {feat: idx for idx, feat in enumerate(sorted_features)}
        del feature_vocab
        gc.collect()

        # Pass 2: stream chunks directly into contiguous bytearray buffers (zero chunk retention)
        data_buf = bytearray()
        indices_buf = bytearray()
        indptr_buf = bytearray(np.array([0], dtype=np.int32).tobytes())
        y_tags: List[str] = []
        nnz_cursor = 0
        row_cursor = 0

        for start in range(0, len(docs), chunk_size):
            batch_dicts = []
            for doc in docs[start : start + chunk_size]:
                tokens = tokenize_with_offsets(doc.text)
                if not tokens:
                    continue
                batch_dicts.extend(
                    extract_document_features(
                        tokens,
                        window=self.window,
                        text=doc.text,
                        feature_version=feature_version,
                    )
                )
                y_tags.extend(align_spans_to_bio(tokens, doc.spans))
            if batch_dicts:
                chunk_csr = self.vectorizer.transform(batch_dicts)
                chunk_csr.eliminate_zeros()
                chunk_csr = self._ensure_32bit_indices(chunk_csr)
                data_buf.extend(np.asarray(chunk_csr.data, dtype=self.dtype).tobytes())
                indices_buf.extend(np.asarray(chunk_csr.indices, dtype=np.int32).tobytes())
                shifted_indptr = np.asarray(chunk_csr.indptr[1:], dtype=np.int32) + nnz_cursor
                indptr_buf.extend(shifted_indptr.tobytes())
                nnz_cursor += int(chunk_csr.nnz)
                row_cursor += int(chunk_csr.shape[0])
                del batch_dicts, chunk_csr, shifted_indptr

        data = np.frombuffer(data_buf, dtype=self.dtype)
        indices = np.frombuffer(indices_buf, dtype=np.int32)
        indptr = np.frombuffer(indptr_buf, dtype=np.int32)
        n_cols = len(sorted_features)
        X_matrix = sp.csr_matrix((data, indices, indptr), shape=(row_cursor, n_cols), copy=False)
        X_matrix = self._ensure_32bit_indices(X_matrix)
        y_arr = np.asarray(y_tags)
        total_tokens_count = int(y_arr.shape[0])
        del y_tags
        gc.collect()

        self.classifier.fit(X_matrix, y_arr)
        self.classes_ = self.classifier.classes_
        self.is_fitted = True

        stats = {
            "non_empty_documents": non_empty_docs,
            "total_tokens": total_tokens_count,
            "num_features": len(sorted_features),
            "sparse_nnz": int(X_matrix.nnz),
        }
        del X_matrix, y_arr, data, indices, indptr, data_buf, indices_buf, indptr_buf
        gc.collect()
        self.training_metadata = dict(stats)
        return stats

    def _predict_proba_matrix(self, X_matrix: Any) -> np.ndarray:
        """Compute normalized per-class probabilities or softmax margin scores."""
        if hasattr(self.classifier, "predict_proba"):
            return np.asarray(self.classifier.predict_proba(X_matrix), dtype=np.float64)
        scores = np.asarray(self.classifier.decision_function(X_matrix), dtype=np.float64)
        if scores.ndim == 1:
            scores = np.column_stack([-scores, scores])
        shifted = scores - np.max(scores, axis=1, keepdims=True)
        exp_scores = np.exp(shifted)
        return exp_scores / np.sum(exp_scores, axis=1, keepdims=True)

    def predict_tokens(
        self,
        X_dicts: List[Dict[str, Any]],
    ) -> Tuple[List[str], List[float]]:
        """Predict BIO tags and confidence probabilities for a sequence of token feature dictionaries."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict_tokens.")
        if not X_dicts:
            return [], []

        X_matrix = self.vectorizer.transform(X_dicts)
        X_matrix = self._ensure_32bit_indices(X_matrix)
        proba = self._predict_proba_matrix(X_matrix)
        classes = list(self.classes_) if self.classes_ is not None else []

        if getattr(self, "use_viterbi", False) and classes:
            return viterbi_decode_bio(
                proba=proba,
                classes=classes,
                entity_bias=float(getattr(self, "decode_entity_bias", 0.0)),
                b_to_i_bonus=float(getattr(self, "decode_b_to_i_bonus", 0.0)),
                i_to_i_bonus=float(getattr(self, "decode_i_to_i_bonus", 0.0)),
            )

        predictions = self.classifier.predict(X_matrix)
        class_to_idx = {cls: idx for idx, cls in enumerate(classes)}
        confidences: List[float] = [
            round(float(proba[i, class_to_idx[pred]]), 4) if pred in class_to_idx else 1.0
            for i, pred in enumerate(predictions)
        ]

        return list(predictions), confidences

    def predict_document_proba(
        self,
        text: str,
    ) -> Tuple[List[Tuple[str, int, int]], List[str], np.ndarray]:
        """Tokenize text and return per-token class probabilities for decoding sweeps."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict_document_proba.")
        if not text or not text.strip():
            return [], list(self.classes_) if self.classes_ is not None else [], np.zeros((0, 0), dtype=np.float64)

        tokens = tokenize_with_offsets(text)
        if not tokens:
            return [], list(self.classes_) if self.classes_ is not None else [], np.zeros((0, 0), dtype=np.float64)

        feature_version = getattr(self, "feature_version", "v1")
        features = extract_document_features(
            tokens,
            window=self.window,
            text=text,
            feature_version=feature_version,
        )
        X_matrix = self.vectorizer.transform(features)
        X_matrix = self._ensure_32bit_indices(X_matrix)
        proba = self._predict_proba_matrix(X_matrix)
        classes = list(self.classes_) if self.classes_ is not None else []
        return tokens, classes, proba

    def predict_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract structured entity spans from raw text.

        Returns:
          List of dicts:
            {'text': str, 'label': str, 'start': int, 'end': int, 'confidence': float}
        """
        if not text or not text.strip():
            return []

        tokens = tokenize_with_offsets(text)
        if not tokens:
            return []

        feature_version = getattr(self, "feature_version", "v1")
        features = extract_document_features(
            tokens,
            window=self.window,
            text=text,
            feature_version=feature_version,
        )
        tags, confidences = self.predict_tokens(features)
        spans = bio_to_spans(text, tokens, tags, confidences=confidences)
        return spans

    def save(self, filepath: Path) -> None:
        """Persist fitted model pipeline to disk."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: Path) -> "TextNERModel":
        """Load persisted model pipeline from disk."""
        if not filepath.exists():
            raise FileNotFoundError(f"Model artifact not found at {filepath}")
        model = joblib.load(filepath)
        if not isinstance(model, cls):
            raise TypeError(f"Loaded object is not an instance of {cls.__name__}")
        return model
