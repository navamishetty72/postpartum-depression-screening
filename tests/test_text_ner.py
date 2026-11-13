"""Unit and integration test suite for the Text Named Entity Recognition (NER) branch.

Validates annotation parsing, offset checks, thread-isolated dataset splitting,
overlap resolution, model training, persistence, and defensive inference interfaces.
"""

from pathlib import Path
import pytest

from pipelines.text_ner.config import PreprocessingConfig, SplitConfig
from pipelines.text_ner.features import (
    align_spans_to_bio,
    bio_to_spans,
    extract_document_features,
    tokenize_with_offsets,
)
from pipelines.text_ner.inference import TextEntitySpan, TextNEROutput, TextNERPredictor
from pipelines.text_ner.models import TextNERModel
from pipelines.text_ner.parser import Document, EntitySpan, parse_ann_content
from pipelines.text_ner.splitter import ThreadDatasetSplitter
from pipelines.text_ner.validator import DatasetValidator, resolve_overlaps


class TestAnnotationParsing:
    """Tests for parsing Brat standoff format (.ann) text."""

    def test_parse_valid_t_and_n_lines(self):
        sample_ann = (
            "T1\tMMLite 10 31\tpostpartum depression\n"
            "N1\tReference T1 SemanticType:mobd\tmobd\n"
            "N2\tReference T1 ConceptId:C0221074\tDepression, Postpartum\n"
            "T2\tMMLite 40 50\tmedication\n"
            "N3\tReference T2 SemanticType:phsu\tphsu\n"
        )
        spans = parse_ann_content(sample_ann)
        assert len(spans) == 2

        s1 = next(s for s in spans if s.id == "T1")
        assert s1.label == "MMLite"
        assert s1.start == 10
        assert s1.end == 31
        assert s1.text == "postpartum depression"
        assert "mobd" in s1.semantic_types
        assert "C0221074" in s1.concept_ids

        s2 = next(s for s in spans if s.id == "T2")
        assert s2.label == "MMLite"
        assert s2.start == 40
        assert s2.end == 50
        assert s2.text == "medication"
        assert "phsu" in s2.semantic_types

    def test_parse_ignores_comments_and_empty_lines(self):
        sample_ann = "\n# Just a comment\n\nT1\tMMLite 0 7\tanxiety\n\n"
        spans = parse_ann_content(sample_ann)
        assert len(spans) == 1
        assert spans[0].text == "anxiety"


class TestOffsetValidationAndPreprocessing:
    """Tests for character-offset integrity, bounds verification, and label checks."""

    def test_valid_annotation_passes(self):
        text = "Patient experiences severe anxiety and fatigue daily."
        # "anxiety" is at index 27..34
        start = text.index("anxiety")
        end = start + len("anxiety")
        span = EntitySpan(id="T1", label="MMLite", start=start, end=end, text="anxiety")
        doc = Document(id="doc_1", group="G1", text=text, spans=[span])

        validator = DatasetValidator(PreprocessingConfig())
        cleaned, issues = validator.validate_document(doc)
        assert len(cleaned) == 1
        assert cleaned[0].text == "anxiety"
        assert len(issues) == 0

    def test_invalid_start_ge_end_rejected(self):
        text = "Hello world"
        span = EntitySpan(id="T1", label="MMLite", start=5, end=4, text="bad")
        doc = Document(id="doc_2", group="G1", text=text, spans=[span])

        validator = DatasetValidator(PreprocessingConfig())
        cleaned, issues = validator.validate_document(doc)
        assert len(cleaned) == 0
        assert "INVALID_START_GE_END" in issues

    def test_out_of_bounds_rejected(self):
        text = "Short text"
        span = EntitySpan(id="T1", label="MMLite", start=5, end=50, text="overflow")
        doc = Document(id="doc_3", group="G1", text=text, spans=[span])

        validator = DatasetValidator(PreprocessingConfig())
        cleaned, issues = validator.validate_document(doc)
        assert len(cleaned) == 0
        assert "OUT_OF_BOUNDS" in issues

    def test_unknown_label_rejected(self):
        text = "Patient was given medication."
        start = text.index("medication")
        end = start + len("medication")
        span = EntitySpan(id="T1", label="UNKNOWN_LABEL", start=start, end=end, text="medication")
        doc = Document(id="doc_4", group="G1", text=text, spans=[span])

        validator = DatasetValidator(PreprocessingConfig(allowed_labels=("MMLite",)))
        cleaned, issues = validator.validate_document(doc)
        assert len(cleaned) == 0
        assert any(i.startswith("UNKNOWN_LABEL") for i in issues)

    def test_unicode_text_offset_alignment(self):
        # Text with multi-byte characters and accents
        text = "Clinique médicale rapportée: dépression post-partum sévère."
        target = "dépression"
        start = text.index(target)
        end = start + len(target)
        span = EntitySpan(id="T1", label="MMLite", start=start, end=end, text=target)
        doc = Document(id="doc_unicode", group="G1", text=text, spans=[span])

        validator = DatasetValidator(PreprocessingConfig())
        cleaned, issues = validator.validate_document(doc)
        assert len(cleaned) == 1
        assert cleaned[0].start == start
        assert cleaned[0].end == end
        assert text[cleaned[0].start : cleaned[0].end] == target

    def test_overlapping_spans_explicit_resolution(self):
        # Two overlapping spans: "anti anxiety medication" (0..23) and "anxiety" (5..12)
        s1 = EntitySpan(id="T1", label="MMLite", start=0, end=23, text="anti anxiety medication")
        s2 = EntitySpan(id="T2", label="MMLite", start=5, end=12, text="anxiety")

        # Longest strategy should keep the longer entity
        retained, discarded = resolve_overlaps([s1, s2], strategy="longest")
        assert len(retained) == 1
        assert retained[0].id == "T1"
        assert discarded == 1

        # First strategy with earlier start
        retained_first, discarded_first = resolve_overlaps([s1, s2], strategy="first")
        assert len(retained_first) == 1
        assert retained_first[0].id == "T1"
        assert discarded_first == 1


class TestDatasetSplittingAndIsolation:
    """Tests for thread-isolated splitting and zero partition leakage."""

    def test_thread_level_splitting_isolation(self, tmp_path):
        docs = [
            Document(id=f"thread_{i:03d}", group="Group1", text=f"Post text {i}", spans=[])
            for i in range(100)
        ]

        splitter = ThreadDatasetSplitter(SplitConfig(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42))
        manifest_file = tmp_path / "splits.json"
        train, val, test, report = splitter.split(docs, output_manifest_path=manifest_file)

        assert len(train) == 70
        assert len(val) == 15
        assert len(test) == 15

        train_ids = {d.id for d in train}
        val_ids = {d.id for d in val}
        test_ids = {d.id for d in test}

        # Strict set disjointness: ZERO thread leakage
        assert len(train_ids & val_ids) == 0
        assert len(train_ids & test_ids) == 0
        assert len(val_ids & test_ids) == 0
        assert manifest_file.exists()


class TestModelTrainingAndInference:
    """Smoke tests for token classification, model serialization, and inference schemas."""

    @pytest.fixture
    def tiny_corpus(self):
        texts = [
            "I have been struggling with anxiety and depression every day.",
            "Doctor prescribed zoloft and recommended therapy for mood swings.",
            "Today felt happy and calm without symptoms.",
            "Experiences of panic attacks and fatigue after delivery.",
        ]
        docs = []
        for i, t in enumerate(texts):
            spans = []
            for kw in ["anxiety", "depression", "zoloft", "panic attacks", "fatigue"]:
                if kw in t:
                    s = t.index(kw)
                    e = s + len(kw)
                    spans.append(EntitySpan(id=f"T{i}_{s}", label="MMLite", start=s, end=e, text=kw))
            docs.append(Document(id=f"doc_{i}", group="G", text=t, spans=spans))
        return docs

    def test_model_training_smoke_test(self, tiny_corpus, tmp_path):
        X_dicts = []
        y_tags = []
        for doc in tiny_corpus:
            toks = tokenize_with_offsets(doc.text)
            tags = align_spans_to_bio(toks, doc.spans)
            feats = extract_document_features(toks)
            X_dicts.extend(feats)
            y_tags.extend(tags)

        model = TextNERModel(classifier_type="sgd", max_iter=200, random_state=42)
        model.fit(X_dicts, y_tags)
        assert model.is_fitted

        # Model serialization test
        model_file = tmp_path / "test_model.joblib"
        model.save(model_file)
        assert model_file.exists()

        # Model loading test
        loaded_model = TextNERModel.load(model_file)
        assert loaded_model.is_fitted

        # Predict structured spans
        test_text = "I feel severe anxiety tonight."
        spans = loaded_model.predict_text(test_text)
        assert isinstance(spans, list)
        for s in spans:
            assert "text" in s
            assert "label" in s
            assert "start" in s
            assert "end" in s
            assert "confidence" in s
            assert test_text[s["start"] : s["end"]] == s["text"]

    def test_inference_predictor_defensive_inputs(self, tmp_path, tiny_corpus):
        # Create small trained model artifact
        X_dicts, y_tags = [], []
        for doc in tiny_corpus:
            toks = tokenize_with_offsets(doc.text)
            tags = align_spans_to_bio(toks, doc.spans)
            X_dicts.extend(extract_document_features(toks))
            y_tags.extend(tags)

        model = TextNERModel(classifier_type="sgd", max_iter=100, random_state=42)
        model.fit(X_dicts, y_tags)
        model_path = tmp_path / "inference_model.joblib"
        model.save(model_path)

        predictor = TextNERPredictor(model_path=model_path, max_characters=100)

        # 1. Empty string input
        out_empty = predictor.predict("")
        assert isinstance(out_empty, TextNEROutput)
        assert out_empty.total_entities_detected == 0
        assert out_empty.processed_character_count == 0

        # 2. Whitespace-only input
        out_ws = predictor.predict("   \n\t  ")
        assert out_ws.total_entities_detected == 0

        # 3. None input
        out_none = predictor.predict(None)
        assert out_none.total_entities_detected == 0

        # 4. Long input safely truncated
        long_text = "anxiety " * 50  # 400 chars, limit is 100
        out_long = predictor.predict(long_text)
        assert out_long.processed_character_count == 100

    def test_missing_model_raises_file_not_found(self):
        missing_path = Path("non_existent_model_dir/model.joblib")
        with pytest.raises(FileNotFoundError) as exc_info:
            TextNERPredictor(model_path=missing_path)
        assert "Text NER model checkpoint missing" in str(exc_info.value)


class TestRegressionSuite:
    """Specific regression test cases required for the Text NER alignment audit."""

    def test_repeated_entity_text_local_isolation(self):
        """Verify that local reconciliation does not jump across distant repeated occurrences."""
        # 'depression' appears twice: at index 23 and at index 128
        text = (
            "Patient was diagnosed with depression after delivery. "
            "After several months of treatment and support, the depression subsided."
        )
        first_idx = text.find("depression")
        second_idx = text.rfind("depression")
        assert first_idx != second_idx

        # Span with 2-char drift near first occurrence
        span1 = EntitySpan(id="T1", label="MMLite", start=first_idx + 2, end=first_idx + 2 + len("depression"), text="depression")
        # Span with 2-char drift near second occurrence
        span2 = EntitySpan(id="T2", label="MMLite", start=second_idx - 2, end=second_idx - 2 + len("depression"), text="depression")

        doc = Document(id="doc_repeat", group="G1", text=text, spans=[span1, span2])
        validator = DatasetValidator(PreprocessingConfig(reconcile_window=10))
        cleaned, issues = validator.validate_document(doc)

        assert len(cleaned) == 2
        assert cleaned[0].start == first_idx
        assert cleaned[0].end == first_idx + len("depression")
        assert text[cleaned[0].start : cleaned[0].end] == "depression"

        assert cleaned[1].start == second_idx
        assert cleaned[1].end == second_idx + len("depression")
        assert text[cleaned[1].start : cleaned[1].end] == "depression"

    def test_ambiguous_offset_reconciliation_detected(self):
        """Verify that multiple occurrences within the local window are detected as ambiguous and dropped."""
        # 'anxiety' appears twice closely: at index 7 and at index 19
        text = "Severe anxiety and anxiety symptoms reported."
        # Window around offset 10 with reconcile_window=15 spans [0, 32], containing BOTH 'anxiety' occurrences
        span = EntitySpan(id="T1", label="MMLite", start=10, end=17, text="anxiety")
        doc = Document(id="doc_ambig", group="G1", text=text, spans=[span])

        validator = DatasetValidator(PreprocessingConfig(reconcile_window=15))
        cleaned, issues = validator.validate_document(doc)

        assert len(cleaned) == 0
        assert "AMBIGUOUS_LOCAL_MATCH" in issues
        assert "TEXT_MISMATCH" in issues

    def test_crlf_text_offset_alignment(self):
        """Verify that CRLF (\\r\\n) line breaks maintain exact character indexing."""
        text = "Line one: anxiety\r\nLine two: insomnia\r\nLine three: postpartum depression"
        target = "postpartum depression"
        start = text.index(target)
        end = start + len(target)
        span = EntitySpan(id="T1", label="MMLite", start=start, end=end, text=target)

        doc = Document(id="doc_crlf", group="G1", text=text, spans=[span])
        validator = DatasetValidator(PreprocessingConfig())
        cleaned, issues = validator.validate_document(doc)

        assert len(cleaned) == 1
        assert cleaned[0].start == start
        assert cleaned[0].end == end
        assert text[cleaned[0].start : cleaned[0].end] == target
        assert len(issues) == 0

    def test_unicode_multi_byte_character_alignment(self):
        """Verify that multi-byte unicode, accented characters and non-breaking spaces preserve offsets."""
        text = "Symptômes: dépression sévère\u00a0— humeur instable \u2764"
        target = "dépression sévère"
        start = text.index(target)
        end = start + len(target)
        span = EntitySpan(id="T1", label="MMLite", start=start, end=end, text=target)

        doc = Document(id="doc_uni", group="G1", text=text, spans=[span])
        validator = DatasetValidator(PreprocessingConfig())
        cleaned, issues = validator.validate_document(doc)

        assert len(cleaned) == 1
        assert cleaned[0].start == start
        assert cleaned[0].end == end
        assert text[cleaned[0].start : cleaned[0].end] == target

    def test_overlapping_annotations_resolution(self):
        """Verify that overlapping annotations are resolved according to longest and first strategies."""
        # Spans: "major depression" [0..16], "depression" [6..16]
        s1 = EntitySpan(id="T1", label="MMLite", start=0, end=16, text="major depression")
        s2 = EntitySpan(id="T2", label="MMLite", start=6, end=16, text="depression")

        # Longest strategy keeps s1
        retained_longest, dropped_longest = resolve_overlaps([s1, s2], strategy="longest")
        assert len(retained_longest) == 1
        assert retained_longest[0].id == "T1"
        assert dropped_longest == 1

        # First strategy with earlier start also keeps s1
        retained_first, dropped_first = resolve_overlaps([s1, s2], strategy="first")
        assert len(retained_first) == 1
        assert retained_first[0].id == "T1"
        assert dropped_first == 1

    def test_exact_entity_reconstruction_from_bio(self):
        """Verify bio_to_spans faithfully reconstructs character spans matching document text."""
        text = "She took zoloft for postpartum depression and panic attacks."
        tokens = tokenize_with_offsets(text)

        # Build ground truth tags
        tags = ["O"] * len(tokens)
        for i, (tok_str, tok_s, tok_e) in enumerate(tokens):
            if tok_str == "zoloft":
                tags[i] = "B-MMLite"
            elif tok_str == "postpartum":
                tags[i] = "B-MMLite"
            elif tok_str == "depression":
                tags[i] = "I-MMLite"
            elif tok_str == "panic":
                tags[i] = "B-MMLite"
            elif tok_str == "attacks":
                tags[i] = "I-MMLite"

        reconstructed_spans = bio_to_spans(text, tokens, tags)
        assert len(reconstructed_spans) == 3

        zoloft_span = reconstructed_spans[0]
        assert zoloft_span["text"] == "zoloft"
        assert text[zoloft_span["start"] : zoloft_span["end"]] == "zoloft"

        ppd_span = reconstructed_spans[1]
        assert ppd_span["text"] == "postpartum depression"
        assert text[ppd_span["start"] : ppd_span["end"]] == "postpartum depression"

        panic_span = reconstructed_spans[2]
        assert panic_span["text"] == "panic attacks"
        assert text[panic_span["start"] : panic_span["end"]] == "panic attacks"

    def test_thread_level_split_isolation(self, tmp_path):
        """Verify that ThreadDatasetSplitter produces strictly disjoint thread sets across train/val/test."""
        docs = [
            Document(id=f"thread_{i:04d}", group="GroupA", text=f"Post content {i}", spans=[])
            for i in range(120)
        ]
        manifest_path = tmp_path / "thread_split_manifest.json"
        splitter = ThreadDatasetSplitter(SplitConfig(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42))
        train, val, test, report = splitter.split(docs, output_manifest_path=manifest_path)

        train_ids = {d.id for d in train}
        val_ids = {d.id for d in val}
        test_ids = {d.id for d in test}

        assert len(train_ids & val_ids) == 0
        assert len(train_ids & test_ids) == 0
        assert len(val_ids & test_ids) == 0
        assert len(train_ids) + len(val_ids) + len(test_ids) == 120

    def test_model_inference_pipeline_guardrails(self, tmp_path):
        """Verify TextNERPredictor defensive bounds, truncation, and output contracts."""
        text = "I felt depression and anxiety."
        tokens = tokenize_with_offsets(text)
        tags = ["O", "O", "B-MMLite", "O", "B-MMLite", "O"]
        features = extract_document_features(tokens)

        model = TextNERModel(classifier_type="sgd", max_iter=100, random_state=42)
        model.fit(features, tags)
        model_file = tmp_path / "guardrail_model.joblib"
        model.save(model_file)

        predictor = TextNERPredictor(model_path=model_file, max_characters=200)

        # 1. Standard prediction
        output = predictor.predict(text)
        assert isinstance(output, TextNEROutput)
        assert output.processed_character_count == len(text)
        assert output.total_entities_detected >= 0
        for ent in output.entities:
            assert isinstance(ent, TextEntitySpan)
            assert ent.start < ent.end
            assert text[ent.start : ent.end] == ent.text

        # 2. Empty string
        out_empty = predictor.predict("")
        assert out_empty.total_entities_detected == 0

        # 3. None
        out_none = predictor.predict(None)
        assert out_none.total_entities_detected == 0


class TestLeakFreeFinalEvaluation:
    """Tests for leak-free final split isolation, streaming fit, versioning, and eval contracts."""

    def test_leak_free_final_split_excludes_exposed_docs_and_urls(self, tmp_path):
        docs = [
            Document(
                id=f"doc_{i:04d}",
                group="Group1",
                text=f"# URL: https://forum.example/thread/{i}\nAnxiety and postpartum fatigue sample {i}.",
                spans=[EntitySpan(id=f"T{i}", label="MMLite", start=38, end=45, text="Anxiety")],
            )
            for i in range(100)
        ]
        excluded_from_test = [f"doc_{i:04d}" for i in range(25)]
        excluded_from_val = [f"doc_{i:04d}" for i in range(10)]

        splitter = ThreadDatasetSplitter(SplitConfig(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42))
        manifest_path = tmp_path / "final_splits.json"
        train, val, final_test, report = splitter.split_leak_free_final(
            docs,
            excluded_from_test_ids=excluded_from_test,
            exclude_from_val_ids=excluded_from_val,
            final_seed=2026,
            output_manifest_path=manifest_path,
        )

        assert len(train) == 70
        assert len(val) == 15
        assert len(final_test) == 15

        train_ids = {d.id for d in train}
        val_ids = {d.id for d in val}
        test_ids = {d.id for d in final_test}

        assert len(train_ids & val_ids) == 0
        assert len(train_ids & test_ids) == 0
        assert len(val_ids & test_ids) == 0
        assert len(test_ids & set(excluded_from_test)) == 0
        assert len(val_ids & set(excluded_from_val)) == 0
        assert report.overlap_verified_zero_doc_ids is True
        assert report.overlap_verified_zero_thread_urls is True
        assert report.final_test_zero_prior_exposure_verified is True
        assert manifest_path.exists()

    def test_fit_documents_streaming_and_model_version(self, tmp_path):
        import numpy as np

        docs = [
            Document(
                id="d1",
                group="G",
                text="Feeling severe anxiety and exhaustion today.",
                spans=[EntitySpan(id="T1", label="MMLite", start=15, end=22, text="anxiety")],
            ),
            Document(id="d_empty", group="G", text="", spans=[]),
            Document(
                id="d2",
                group="G",
                text="Prescribed zoloft for postpartum depression.",
                spans=[EntitySpan(id="T2", label="MMLite", start=11, end=17, text="zoloft")],
            ),
        ]
        model = TextNERModel(
            classifier_type="sgd",
            loss="modified_huber",
            max_iter=100,
            random_state=2026,
            model_version="1.2.0",
            dtype=np.float32,
        )
        stats = model.fit_documents(docs, chunk_size=2)
        assert stats["non_empty_documents"] == 2
        assert stats["total_tokens"] > 0
        assert model.is_fitted

        ckpt = tmp_path / "versioned_model.joblib"
        model.save(ckpt)

        predictor = TextNERPredictor(model_path=ckpt)
        assert predictor.get_model_metadata()["model_version"] == "1.2.0"
        out = predictor.predict("She feels severe anxiety.")
        assert out.model_version == "1.2.0"

    def test_summarize_semantic_types_counts_multilabel_ambiguity(self):
        from pipelines.text_ner.final_eval import summarize_semantic_types

        docs = [
            Document(
                id="s1",
                group="G",
                text="zoloft and anxiety",
                spans=[
                    EntitySpan(
                        id="T1",
                        label="MMLite",
                        start=0,
                        end=6,
                        text="zoloft",
                        semantic_types=["phsu", "orch"],
                    ),
                    EntitySpan(
                        id="T2",
                        label="MMLite",
                        start=11,
                        end=18,
                        text="anxiety",
                        semantic_types=["mobd"],
                    ),
                ],
            )
        ]
        summary = summarize_semantic_types(docs)
        assert summary["total_validated_spans"] == 2
        assert summary["distinct_semantic_types_observed"] == 3
        assert summary["spans_with_single_semantic_type"] == 1
        assert summary["spans_with_multiple_semantic_types"] == 1
        assert summary["multi_label_ambiguity_rate"] == 0.5
        assert summary["single_label_only_counts"] == {"mobd": 1}
        assert summary["top_multi_label_combinations"] == {"orch+phsu": 1}

    def test_final_evaluation_summary_contract(self):
        import json

        summary_path = Path(__file__).resolve().parent.parent / "docs" / "text_ner_final_evaluation_summary.json"
        assert summary_path.exists()
        data = json.loads(summary_path.read_text(encoding="utf-8"))

        split_meta = data["clean_split_metadata"]
        assert split_meta["total_documents"] == 10569
        assert split_meta["overlap_verified_zero_doc_ids"] is True
        assert split_meta["overlap_verified_zero_thread_urls"] is True
        assert split_meta["final_test_zero_prior_exposure_verified"] is True
        assert split_meta["partitions"]["final_test"]["num_documents"] == 1586

        eval_meta = data["final_test_metrics_complete"]
        assert eval_meta["documents_evaluated"] == 1586
        assert eval_meta["gold_entities_support"] == 34878
        assert 0.0 < eval_meta["strict_micro_f1"] < 1.0

        sem_meta = data["semantic_type_audit"]
        assert sem_meta["total_validated_spans"] == 227699
        assert sem_meta["distinct_semantic_types_observed"] == 28

    def test_v2_features_min_freq_and_viterbi_decoding(self, tmp_path):
        """Verify v2 contextual features, min_feature_freq=2 pruning, and BIO Viterbi decoding."""
        import numpy as np
        from pipelines.text_ner.models import viterbi_decode_bio

        # Viterbi must never allow an unpreceded O -> I-MMLite transition
        proba = np.array(
            [
                [0.05, 0.10, 0.85],  # O favored
                [0.20, 0.60, 0.20],  # I-MMLite illegally peaked right after O
                [0.65, 0.15, 0.20],  # B-MMLite favored
                [0.10, 0.70, 0.20],  # I-MMLite after B-MMLite favored
            ],
            dtype=np.float64,
        )
        tags, confs = viterbi_decode_bio(
            proba,
            classes=["B-MMLite", "I-MMLite", "O"],
            entity_bias=-0.15,
            b_to_i_bonus=0.3,
            i_to_i_bonus=0.3,
        )
        assert tags[0] == "O"
        assert tags[1] != "I-MMLite"
        assert tags[2] == "B-MMLite"
        assert tags[3] == "I-MMLite"
        assert len(confs) == 4

        docs = [
            Document(
                id=f"v2_doc_{i}",
                group="GroupA",
                text="url -https://example.org/p\nMother reports severe postpartum depression and Zoloft use.",
                spans=[
                    EntitySpan(id="T1", label="MMLite", start=49, end=70, text="postpartum depression"),
                    EntitySpan(id="T2", label="MMLite", start=75, end=81, text="Zoloft"),
                ],
            )
            for i in range(6)
        ]
        model = TextNERModel(
            classifier_type="sgd",
            loss="modified_huber",
            c_param=5.0,
            max_iter=50,
            random_state=2026,
            class_weight={"O": 1.0, "B-MMLite": 8.0, "I-MMLite": 10.0},
            window=2,
            model_version="1.3.0",
            dtype=np.float32,
            feature_version="v2",
            min_feature_freq=2,
            use_viterbi=True,
            decode_entity_bias=-0.15,
            decode_b_to_i_bonus=0.3,
            decode_i_to_i_bonus=0.3,
        )
        stats = model.fit_documents(docs, chunk_size=3)
        assert stats["num_features"] > 0
        ckpt = tmp_path / "v130_unit.joblib"
        model.save(ckpt)

        predictor = TextNERPredictor(model_path=ckpt)
        meta = predictor.get_model_metadata()
        assert meta["model_version"] == "1.3.0"
        assert meta["feature_version"] == "v2"
        assert meta["use_viterbi"] is True

        out = predictor.predict("Severe postpartum depression and Zoloft mentioned.")
        assert out.model_version == "1.3.0"
        assert out.total_entities_detected >= 1

    def test_predictor_version_resolution_and_dual_compatibility(self):
        """Verify v1.3.0 default resolution, explicit v1.2.0 compatibility, and live loading when present."""
        assert TextNERPredictor.resolve_model_path(model_version="v1.3.0").name == "text_ner_model.joblib"
        assert TextNERPredictor.resolve_model_path(model_version="v1.3.0").parent.name == "v1.3.0"
        assert TextNERPredictor.resolve_model_path(model_version="1.2.0").parent.name == "v1.2.0"

        with pytest.raises(ValueError):
            TextNERPredictor.resolve_model_path(model_version="v9.9.9")

        sample = "Feeling overwhelming anxiety and taking Zoloft after delivery."
        if TextNERPredictor.DEFAULT_MODEL_PATH.exists():
            p130 = TextNERPredictor(model_version="v1.3.0")
            res130 = p130.predict(sample)
            assert res130.model_version == "1.3.0"
            assert p130.get_model_metadata()["feature_version"] == "v2"
            assert p130.get_model_metadata()["use_viterbi"] is True
            assert res130.total_entities_detected >= 1

        if TextNERPredictor.LEGACY_V120_MODEL_PATH.exists():
            p120 = TextNERPredictor(model_version="v1.2.0")
            res120 = p120.predict(sample)
            assert res120.model_version == "1.2.0"
            assert p120.get_model_metadata()["feature_version"] == "v1"
            assert res120.total_entities_detected >= 1




