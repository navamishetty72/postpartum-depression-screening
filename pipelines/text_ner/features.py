"""Offset-preserving tokenization, BIO tag alignment, and orthographic feature extraction.

Ensures strict mathematical alignment between character-level spans and token sequence representations.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from pipelines.text_ner.parser import EntitySpan

# Tokenizer pattern matching alphanumeric words, hyphenated compounds, or individual symbols
TOKEN_REGEX = re.compile(r"\w+(?:-\w+)*|[^\w\s]")


def tokenize_with_offsets(text: str) -> List[Tuple[str, int, int]]:
    """Tokenize raw text while recording exact 0-based character offsets.

    Returns:
      List of (token_str, start_char, end_char) tuples.
    """
    tokens: List[Tuple[str, int, int]] = []
    for match in TOKEN_REGEX.finditer(text):
        tokens.append((match.group(), match.start(), match.end()))
    return tokens


def align_spans_to_bio(
    tokens: List[Tuple[str, int, int]],
    spans: List[EntitySpan],
) -> List[str]:
    """Map character-level entity spans to token-level BIO tags.

    Tokens overlapping the beginning of an entity span receive 'B-<label>'.
    Subsequent overlapping tokens receive 'I-<label>'.
    All other tokens receive 'O'.
    """
    bio_tags = ["O"] * len(tokens)
    if not tokens or not spans:
        return bio_tags

    for span in spans:
        span_s, span_e = span.start, span.end
        label = span.label

        first_token = True
        for i, (_, tok_s, tok_e) in enumerate(tokens):
            # Check overlap between token [tok_s, tok_e] and span [span_s, span_e]
            if max(tok_s, span_s) < min(tok_e, span_e):
                if first_token:
                    bio_tags[i] = f"B-{label}"
                    first_token = False
                else:
                    bio_tags[i] = f"I-{label}"

    return bio_tags


def bio_to_spans(
    text: str,
    tokens: List[Tuple[str, int, int]],
    tags: List[str],
    confidences: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Convert token-level BIO predictions back into strict character-level entity spans.

    Returns:
      List of dicts: {'text': ..., 'label': ..., 'start': ..., 'end': ..., 'confidence': ...}
    """
    spans: List[Dict[str, Any]] = []
    current_label: Optional[str] = None
    current_start: Optional[int] = None
    current_end: Optional[int] = None
    current_confs: List[float] = []

    for i, tag in enumerate(tags):
        tok_text, tok_s, tok_e = tokens[i]
        conf = confidences[i] if confidences is not None else 1.0

        if tag.startswith("B-"):
            if current_label is not None and current_start is not None and current_end is not None:
                # Flush previous span
                avg_conf = sum(current_confs) / max(1, len(current_confs))
                spans.append({
                    "text": text[current_start:current_end],
                    "label": current_label,
                    "start": current_start,
                    "end": current_end,
                    "confidence": round(avg_conf, 4),
                })
            current_label = tag[2:]
            current_start = tok_s
            current_end = tok_e
            current_confs = [conf]

        elif tag.startswith("I-"):
            label = tag[2:]
            if current_label == label and current_start is not None:
                # Continuation of current entity
                current_end = tok_e
                current_confs.append(conf)
            else:
                # Treat as new entity if no matching B- was active
                if current_label is not None and current_start is not None and current_end is not None:
                    avg_conf = sum(current_confs) / max(1, len(current_confs))
                    spans.append({
                        "text": text[current_start:current_end],
                        "label": current_label,
                        "start": current_start,
                        "end": current_end,
                        "confidence": round(avg_conf, 4),
                    })
                current_label = label
                current_start = tok_s
                current_end = tok_e
                current_confs = [conf]

        else:  # tag == 'O'
            if current_label is not None and current_start is not None and current_end is not None:
                avg_conf = sum(current_confs) / max(1, len(current_confs))
                spans.append({
                    "text": text[current_start:current_end],
                    "label": current_label,
                    "start": current_start,
                    "end": current_end,
                    "confidence": round(avg_conf, 4),
                })
                current_label = None
                current_start = None
                current_end = None
                current_confs = []

    # Final flush
    if current_label is not None and current_start is not None and current_end is not None:
        avg_conf = sum(current_confs) / max(1, len(current_confs))
        spans.append({
            "text": text[current_start:current_end],
            "label": current_label,
            "start": current_start,
            "end": current_end,
            "confidence": round(avg_conf, 4),
        })

    return spans


def extract_token_features(
    tokens: List[Tuple[str, int, int]],
    index: int,
    window: int = 2,
) -> Dict[str, Any]:
    """Extract orthographic, morphological, and contextual window features for a single token."""
    word = tokens[index][0]
    word_lower = word.lower()
    word_len = len(word)

    # Word shape classification
    if word.isupper():
        shape = "ALL_CAPS"
    elif word.istitle():
        shape = "Title"
    elif word.islower():
        shape = "lower"
    elif any(c.isdigit() for c in word):
        shape = "has_digit"
    else:
        shape = "mixed"

    features: Dict[str, Any] = {
        "bias": 1.0,
        "word.lower": word_lower,
        "word.shape": shape,
        "word[-4:]": word[-4:] if word_len >= 4 else word,
        "word[-3:]": word[-3:] if word_len >= 3 else word,
        "word[-2:]": word[-2:] if word_len >= 2 else word,
        "word[:4]": word[:4] if word_len >= 4 else word,
        "word[:3]": word[:3] if word_len >= 3 else word,
        "word[:2]": word[:2] if word_len >= 2 else word,
        "word.isupper": word.isupper(),
        "word.istitle": word.istitle(),
        "word.isdigit": word.isdigit(),
        "word.has_hyphen": "-" in word,
        "word.is_punct": not word.isalnum(),
        "word.length": min(word_len, 15),
        "word.length_bin": "short" if word_len <= 3 else "med" if word_len <= 8 else "long",
    }

    # Left context window
    for w in range(1, window + 1):
        if index - w >= 0:
            p_word = tokens[index - w][0]
            p_lower = p_word.lower()
            features[f"-{w}:word.lower"] = p_lower
            features[f"-{w}:word.istitle"] = p_word.istitle()
            features[f"-{w}:word.isupper"] = p_word.isupper()
            if w == 1:
                features["-1:bigram"] = f"{p_lower}_{word_lower}"
                features["-1:shape_trans"] = f"{p_word.istitle()}_{word.istitle()}"
        else:
            features[f"BOS_{w}"] = True

    # Right context window
    for w in range(1, window + 1):
        if index + w < len(tokens):
            n_word = tokens[index + w][0]
            n_lower = n_word.lower()
            features[f"+{w}:word.lower"] = n_lower
            features[f"+{w}:word.istitle"] = n_word.istitle()
            features[f"+{w}:word.isupper"] = n_word.isupper()
            if w == 1:
                features["+1:bigram"] = f"{word_lower}_{n_lower}"
        else:
            features[f"EOS_{w}"] = True

    return features


def _short_word_shape(word: str) -> str:
    """Compute collapsed character-class shape (e.g., 'Anxiety' -> 'Xx', '20mg' -> 'dx')."""
    if not word:
        return ""
    out: List[str] = []
    prev = ""
    for ch in word:
        if ch.isupper():
            cur = "X"
        elif ch.islower():
            cur = "x"
        elif ch.isdigit():
            cur = "d"
        else:
            cur = ch
        if cur != prev:
            out.append(cur)
            prev = cur
    return "".join(out[:6])


def _classify_line_section(line_text: str) -> str:
    """Classify a document line into structural section metadata without content filtering."""
    stripped = line_text.strip()
    lower = stripped.lower()
    if (
        lower.startswith("url -http")
        or lower.startswith("# url:")
        or lower.startswith("http://")
        or lower.startswith("https://")
    ):
        return "URL"
    if lower.startswith("title of post") or lower.startswith("# title:"):
        return "TITLE"
    if (
        lower.startswith("timestamp ")
        or lower.startswith("# timestamp:")
        or lower.startswith("# post_id:")
        or lower.startswith("# comment_id:")
        or lower.startswith("# author:")
        or lower.startswith("main post")
        or lower.startswith("comments (")
    ):
        return "META"
    return "BODY"


def _build_document_token_contexts(
    tokens: List[Tuple[str, int, int]],
    text: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Precompute O(N) line-section and sentence-context metadata for each token."""
    n = len(tokens)
    if n == 0:
        return []

    line_sections = ["BODY"] * n
    at_line_start = [False] * n
    at_line_end = [False] * n
    line_ids = [0] * n

    if text is not None:
        # Map character offset ranges of each line cleanly
        line_spans: List[Tuple[int, int, str]] = []
        pos = 0
        for raw_line in text.splitlines(keepends=True):
            l_len = len(raw_line)
            sec = _classify_line_section(raw_line)
            line_spans.append((pos, pos + l_len, sec))
            pos += l_len
        if not line_spans and text:
            line_spans.append((0, len(text), _classify_line_section(text)))

        l_idx = 0
        n_lines = len(line_spans)
        for i, (_, tok_s, _) in enumerate(tokens):
            while l_idx + 1 < n_lines and tok_s >= line_spans[l_idx][1]:
                l_idx += 1
            if l_idx < n_lines:
                line_sections[i] = line_spans[l_idx][2]
                line_ids[i] = l_idx
    else:
        cur_line = 0
        for i in range(1, n):
            if text is None and (tokens[i][1] - tokens[i - 1][2]) > 3:
                cur_line += 1
            line_ids[i] = cur_line

    for i in range(n):
        at_line_start[i] = i == 0 or line_ids[i] != line_ids[i - 1]
        at_line_end[i] = i == n - 1 or line_ids[i] != line_ids[i + 1]

    # Segment tokens into sentences via line breaks and terminal punctuation
    sent_bounds: List[Tuple[int, int]] = []
    sent_start_idx = 0
    for i, (tok_str, tok_s, tok_e) in enumerate(tokens):
        break_after = False
        if i == n - 1 or line_ids[i] != line_ids[i + 1]:
            break_after = True
        elif tok_str in {".", "!", "?"}:
            break_after = True
        if break_after:
            sent_bounds.append((sent_start_idx, i + 1))
            sent_start_idx = i + 1

    first_person_words = {"i", "im", "i'm", "ive", "my", "me", "we", "our"}
    negation_words = {"not", "no", "never", "without", "dont", "don't", "didnt", "didn't", "cant", "can't", "wont"}

    contexts: List[Dict[str, Any]] = [{} for _ in range(n)]
    for s_start, s_end in sent_bounds:
        s_len = s_end - s_start
        s_words = {tokens[j][0].lower() for j in range(s_start, s_end)}
        has_q = "?" in s_words
        has_fp = bool(s_words & first_person_words)
        has_neg = bool(s_words & negation_words)
        len_bin = "short" if s_len <= 5 else "med" if s_len <= 18 else "long"

        for j in range(s_start, s_end):
            rel = j - s_start
            pos_bin = (
                "start"
                if rel == 0
                else "early"
                if rel <= 2
                else "end"
                if j == s_end - 1
                else "mid"
            )
            contexts[j] = {
                "section": line_sections[j],
                "at_line_start": at_line_start[j],
                "at_line_end": at_line_end[j],
                "sent_at_start": rel == 0,
                "sent_pos_bin": pos_bin,
                "sent_len_bin": len_bin,
                "sent_has_question": has_q,
                "sent_has_first_person": has_fp,
                "sent_has_negation": has_neg,
            }

    return contexts


def extract_token_features_v2(
    tokens: List[Tuple[str, int, int]],
    index: int,
    window: int = 3,
    token_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Extract enhanced contextual, morphological, section, and sentence features."""
    word = tokens[index][0]
    word_lower = word.lower()
    word_len = len(word)
    short_shape = _short_word_shape(word)

    features = extract_token_features(tokens, index, window=window)
    features["word.shape_short"] = short_shape
    if word_len >= 5:
        features["word[-5:]"] = word_lower[-5:]
    features["word[-1:]"] = word_lower[-1:]

    # Structural line/section & sentence features
    if token_context is not None:
        sec = token_context["section"]
        features["sec"] = sec
        features["sec_word"] = f"{sec}:{word_lower}"
        features["line.start"] = token_context["at_line_start"]
        features["line.end"] = token_context["at_line_end"]
        features["sent.start"] = token_context["sent_at_start"]
        features["sent.pos_bin"] = token_context["sent_pos_bin"]
        features["sent.len_bin"] = token_context["sent_len_bin"]
        features["sent.has_q"] = token_context["sent_has_question"]
        features["sent.has_fp"] = token_context["sent_has_first_person"]
        features["sent.has_neg"] = token_context["sent_has_negation"]
        features["sent_start_title"] = token_context["sent_at_start"] and word.istitle()

    # Enhanced neighbor affixes, shapes, punctuation & multi-token brackets
    p1_lower = tokens[index - 1][0].lower() if index - 1 >= 0 else "<BOS>"
    n1_lower = tokens[index + 1][0].lower() if index + 1 < len(tokens) else "<EOS>"
    features["surround:-1_+1"] = f"{p1_lower}_{n1_lower}"
    features["trigram:-1_0_+1"] = f"{p1_lower}_{word_lower}_{n1_lower}"

    for offset in (-2, -1, 1, 2):
        nbr_idx = index + offset
        tag = f"{offset:+d}"
        if 0 <= nbr_idx < len(tokens):
            nw = tokens[nbr_idx][0]
            nl = nw.lower()
            features[f"{tag}:shape_short"] = _short_word_shape(nw)
            features[f"{tag}:is_punct"] = not nw.isalnum()
            if len(nw) >= 3:
                features[f"{tag}:suf3"] = nl[-3:]
                features[f"{tag}:pre3"] = nl[:3]

    if index - 2 >= 0:
        p2_lower = tokens[index - 2][0].lower()
        features["-2_-1:bigram"] = f"{p2_lower}_{p1_lower}"
    if index + 2 < len(tokens):
        n2_lower = tokens[index + 2][0].lower()
        features["+1_+2:bigram"] = f"{n1_lower}_{n2_lower}"
    if index + 1 < len(tokens):
        features["+1:shape_trans"] = f"{short_shape}_{_short_word_shape(tokens[index + 1][0])}"

    return features


def extract_document_features(
    tokens: List[Tuple[str, int, int]],
    window: int = 2,
    text: Optional[str] = None,
    feature_version: str = "v1",
) -> List[Dict[str, Any]]:
    """Extract token feature dictionaries for an entire token sequence."""
    if feature_version == "v2":
        contexts = _build_document_token_contexts(tokens, text=text)
        return [
            extract_token_features_v2(
                tokens,
                i,
                window=window,
                token_context=contexts[i],
            )
            for i in range(len(tokens))
        ]
    return [extract_token_features(tokens, i, window=window) for i in range(len(tokens))]

