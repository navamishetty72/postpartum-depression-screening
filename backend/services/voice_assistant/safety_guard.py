"""Deterministic Safety Guard for the Postpartum Voice Assistant.

Completely independent of Gemini, external networks, or third-party APIs.
Evaluates user messages for acute clinical emergencies:
- Suicidal ideation or self-harm intent
- Thoughts, impulses, or threats of harming the infant
- Immediate physical danger or acute crisis

When triggered, safety escalation BYPASSES Gemini entirely and immediately returns
predefined, vetted emergency crisis responses with 24/7 crisis hotlines.

LIMITATIONS OF DETERMINISTIC DETECTION:
----------------------------------------
1. Keyword/Pattern Rigidity: Rule-based regex pattern matching cannot reliably interpret
   deep conversational nuances, sarcasm, poetic or metaphorical expressions, or newly
   emerging colloquial slang.
2. Risk of False Negatives: Covert, passive, or indirectly phrased suicidal ideation or
   distress may not match explicit keyword patterns. This filter is a safeguard, NOT a
   diagnostic or predictive clinical guarantee.
3. Risk of False Positives: Quoted discussions, stories from third parties, or benign
   metaphors ("this chore is killing me") might trigger patterns if patterns are too broad.
   Patterns are strictly calibrated to require explicit personal intent or action.
4. Clinical Role: This safety guard is a defensive safety rail. It does not replace
   validated clinical instruments (such as the Edinburgh Postnatal Depression Scale / EPDS)
   or evaluation by a licensed mental health professional.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


# -----------------------------------------------------------------------------
# Predefined Urgent Crisis Escalation Responses (India Primary & International)
# -----------------------------------------------------------------------------

EMERGENCY_RESPONSE_SELF_HARM = (
    "I hear how much pain you are carrying right now, but please know that you are not alone "
    "and your life matters deeply. Please connect with immediate professional crisis support right now:\n"
    "• In India: Call Tele-MANAS toll-free at 14416 or 1800-891-4416 (24/7 free mental health support by Govt. of India), "
    "or call 112 for immediate emergency services. You can also reach the KIRAN helpline at 1800-599-0019.\n"
    "• In the US/Canada: Call or text 988 (Suicide & Crisis Lifeline) or call the National Maternal Mental Health Hotline at 1-833-852-6262.\n"
    "• If you are in immediate physical danger, please call 112 (India) or 911 (US) or go to the nearest emergency room immediately. "
    "Please reach out to someone who can be with you right now."
)

EMERGENCY_RESPONSE_INFANT_HARM = (
    "Thank you for sharing this. If you are having thoughts or impulses of hurting your baby, "
    "please gently place your baby in a safe place, like their crib on their back, step into "
    "another room, and reach out for immediate support right now:\n"
    "• In India: Call Tele-MANAS toll-free at 14416 or 1800-891-4416 (24/7 free support), "
    "or call 112 / 108 for emergency medical assistance.\n"
    "• In the US/Canada: Call or text the National Maternal Mental Health Hotline at 1-833-852-6262, "
    "call 988, or call Postpartum Support International at 1-800-944-4773.\n"
    "If you feel you or your baby are in immediate danger, call 112 (India) or 911 (US) or go to the nearest emergency room."
)

EMERGENCY_RESPONSE_IMMEDIATE_DANGER = (
    "If you or your baby are in immediate physical danger or experiencing a medical emergency, "
    "please call emergency services immediately: call 112 in India (or 102/108 for an ambulance) "
    "or 911 in the US. In India, for mental health crisis support, call Tele-MANAS at 14416 or 1800-891-4416."
)


# -----------------------------------------------------------------------------
# Pattern Definitions
# -----------------------------------------------------------------------------

# Patterns indicating explicit self-harm or suicidal intent
_SELF_HARM_PATTERNS = [
    re.compile(r"\b(?:kill|killing|end|ending|take|taking)\s+(?:my\s*own\s*life|my\s+life|myself)\b", re.IGNORECASE),
    re.compile(r"\b(?:want|wish|going)\s+to\s+(?:die|disappear\s+forever|be\s+dead)\b", re.IGNORECASE),
    re.compile(r"\b(?:thinking\s+of|thoughts\s+of)\s+(?:ending|taking|killing)\s+(?:my\s*own\s*life|my\s+life|myself)\b", re.IGNORECASE),
    re.compile(r"\b(?:better\s+off\s+dead|everyone\s+would\s+be\s+better\s+off\s+without\s+me)\b", re.IGNORECASE),
    re.compile(r"\b(?:commit(?:ting)?\s+suicide|suicidal(?:\s+thoughts|\s+feelings|\s+ideation)?)\b", re.IGNORECASE),
    re.compile(r"\b(?:hang|shoot|slit|overdose|cut)\s+myself\b", re.IGNORECASE),
    re.compile(r"\b(?:swallow(?:ing)?|take|taking)\s+(?:all\s+the\s+)?pills\s+to\s+(?:die|end\s+it)\b", re.IGNORECASE),
    re.compile(r"\b(?:end\s+it\s+all|can't\s+go\s+on\s+living|no\s+reason\s+to\s+live)\b", re.IGNORECASE),
    re.compile(r"\b(?:harm|harming|hurt|hurting|cut|cutting)\s+myself\b", re.IGNORECASE),
]

# Patterns indicating thoughts, urges, or threats of harming the infant
_INFANT_HARM_PATTERNS = [
    re.compile(
        r"\b(?:harm|hurt|kill|injure|smother|suffocate|shake|drop|throw|drown)\s+(?:my\s+)?(?:baby|newborn|infant|child|little\s+one)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bthoughts\s+of\s+(?:hurting|harming|killing|dropping|shaking|smothering|throwing|drowning)\s+(?:my\s+)?(?:baby|newborn|infant|child)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwant\s+to\s+(?:hurt|harm|kill|smother|shake|throw|drown)\s+(?:my\s+)?(?:baby|newborn|infant|child)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:afraid|scared)\s+I\s+(?:might|will)\s+(?:hurt|harm|kill|smother|shake|throw|drown)\s+(?:my\s+)?(?:baby|newborn|infant|child)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:feel\s+like|tempted\s+to)\s+(?:smothering|shaking|throwing|drowning|harming|killing|hurting)\s+(?:my\s+)?(?:baby|newborn|infant|child)\b",
        re.IGNORECASE,
    ),
]

# Patterns indicating immediate external violence or physical crisis
_IMMEDIATE_DANGER_PATTERNS = [
    re.compile(r"\b(?:in\s+immediate\s+danger|someone\s+is\s+attacking\s+me|being\s+abused\s+right\s+now)\b", re.IGNORECASE),
    re.compile(r"\b(?:severe\s+hemorrhage|uncontrolled\s+bleeding|can't\s+breathe|passing\s+out\s+repeatedly)\b", re.IGNORECASE),
]


@dataclass
class SafetyCheckResult:
    """Outcome of the deterministic safety evaluation."""

    is_safe: bool
    category: Optional[str] = None
    emergency_response: Optional[str] = None
    matched_rules: List[str] = field(default_factory=list)


class SafetyGuard:
    """Evaluates text messages deterministically for acute postpartum safety emergencies."""

    def __init__(self) -> None:
        """Initialize compiled patterns for zero-latency deterministic safety evaluation."""
        self._self_harm_rules = _SELF_HARM_PATTERNS
        self._infant_harm_rules = _INFANT_HARM_PATTERNS
        self._danger_rules = _IMMEDIATE_DANGER_PATTERNS

    def evaluate(self, text: str) -> SafetyCheckResult:
        """Scan input text for crisis triggers.

        Ordinary postpartum struggles (e.g. 'I am exhausted', 'I have been crying',
        'I feel anxious', 'I feel overwhelmed') MUST NOT be flagged as emergencies.

        Args:
            text: Raw input string from the user.

        Returns:
            SafetyCheckResult indicating safety status, category, and urgent response if triggered.
        """
        if not text or not text.strip():
            return SafetyCheckResult(is_safe=True)

        cleaned = text.strip()

        # 1. Check Infant Harm first (highest urgency in maternal mental health)
        for pattern in self._infant_harm_rules:
            if pattern.search(cleaned):
                return SafetyCheckResult(
                    is_safe=False,
                    category="infant_harm",
                    emergency_response=EMERGENCY_RESPONSE_INFANT_HARM,
                    matched_rules=["INFANT_HARM_INTENT"],
                )

        # 2. Check Self-Harm / Suicide
        for pattern in self._self_harm_rules:
            if pattern.search(cleaned):
                return SafetyCheckResult(
                    is_safe=False,
                    category="self_harm",
                    emergency_response=EMERGENCY_RESPONSE_SELF_HARM,
                    matched_rules=["SELF_HARM_OR_SUICIDAL_INTENT"],
                )

        # 3. Check Immediate Danger / Physical Emergency
        for pattern in self._danger_rules:
            if pattern.search(cleaned):
                return SafetyCheckResult(
                    is_safe=False,
                    category="immediate_danger",
                    emergency_response=EMERGENCY_RESPONSE_IMMEDIATE_DANGER,
                    matched_rules=["IMMEDIATE_PHYSICAL_DANGER"],
                )

        # Clean / Safe for supportive LLM engagement
        return SafetyCheckResult(is_safe=True)
