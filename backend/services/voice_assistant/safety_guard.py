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
from typing import Dict, List, Optional

from backend.services.voice_assistant.config import detect_language


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

# Multilingual localized crisis escalation responses for all 8 supported languages
EMERGENCY_RESPONSES_BY_LANGUAGE: Dict[str, Dict[str, str]] = {
    "en": {
        "self_harm": EMERGENCY_RESPONSE_SELF_HARM,
        "infant_harm": EMERGENCY_RESPONSE_INFANT_HARM,
        "immediate_danger": EMERGENCY_RESPONSE_IMMEDIATE_DANGER,
    },
    "hi": {
        "self_harm": (
            "मैं समझ सकती हूँ कि आप इस समय बहुत कठिन दौर से गुजर रही हैं, लेकिन कृपया जानें कि आप अकेली नहीं हैं। "
            "कृपया तुरंत आपातकालीन सहायता से संपर्क करें:\n"
            "• भारत में: टेली-मानस (Tele-MANAS) टोल-फ्री 14416 या 1800-891-4416 पर कॉल करें (24/7 निःशुल्क मानसिक स्वास्थ्य सहायता), "
            "या आपातकालीन सेवा के लिए 112 डायल करें।\n"
            "• अमेरिका/कनाडा: 988 पर कॉल करें या टेक्स्ट करें।\n"
            "कृपया किसी अपने को तुरंत अपने पास बुलाएं।"
        ),
        "infant_harm": (
            "यह साझा करने के लिए धन्यवाद। यदि आपके मन में बच्चे को नुकसान पहुँचाने के विचार आ रहे हैं, "
            "तो कृपया बच्चे को पालने (crib) में सुरक्षित लिटा दें, दूसरे कमरे में जाएं, और तुरंत सहायता लें:\n"
            "• टेली-मानस टोल-फ्री: 14416 या 1800-891-4416 (24/7 निःशुल्क सहायता), या आपातकालीन नंबर 112 / 108 पर कॉल करें।"
        ),
        "immediate_danger": (
            "यदि आप या आपका बच्चा तत्काल खतरे में हैं, तो कृपया तुरंत 112 पर कॉल करें। मानसिक स्वास्थ्य सहायता के लिए टेली-मानस को 14416 पर कॉल करें।"
        ),
    },
    "kn": {
        "self_harm": (
            "ನೀವು ಅನುಭವಿಸುತ್ತಿರುವ ನೋವು ನನಗೆ ಅರ್ಥವಾಗುತ್ತಿದೆ, ಆದರೆ ನೀವು ಒಬ್ಬಂಟಿಯಲ್ಲ. ದಯವಿಟ್ಟು ತಕ್ಷಣವೇ ತುರ್ತು ನೆರವನ್ನು ಸಂಪರ್ಕಿಸಿ:\n"
            "• ಭಾರತದಲ್ಲಿ: ಟೆಲಿ-ಮಾನಸ್ (Tele-MANAS) ಉಚಿತ ಸಹಾಯವಾಣಿ 14416 ಅಥವಾ 1800-891-4416 ಗೆ ಕರೆ ಮಾಡಿ (24/7 ಉಚಿತ ಮಾನಸಿಕ ಆರೋಗ್ಯ ಬೆಂಬಲ), "
            "ಅಥವಾ ತುರ್ತು ಸೇವೆಗಳಿಗಾಗಿ 112 ಗೆ ಕರೆ ಮಾಡಿ.\n"
            "ದಯವಿಟ್ಟು ಈಗಲೇ ನಿಮ್ಮವರನ್ನು ಸಂಪರ್ಕಿಸಿ."
        ),
        "infant_harm": (
            "ಮಗುವಿಗೆ ಹಾನಿ ಮಾಡುವ ಆಲೋಚನೆಗಳು ಬರುತ್ತಿದ್ದರೆ, ದಯವಿಟ್ಟು ಮಗುವನ್ನು ತೊಟ್ಟಿಲಿನಲ್ಲಿ (crib) ಸುರಕ್ಷಿತವಾಗಿ ಮಲಗಿಸಿ, "
            "ಬೇರೆ ಕೋಣೆಗೆ ಬಂದು ತಕ್ಷಣವೇ ಸಹಾಯ ಪಡೆಯಿರಿ:\n"
            "• ಟೆಲಿ-ಮಾನಸ್ ಉಚಿತ ಸಂಖ್ಯೆ: 14416 ಅಥವಾ 1800-891-4416 ಗೆ ಕರೆ ಮಾಡಿ, ಅಥವಾ ತುರ್ತು ಸಂಖ್ಯೆ 112 / 108 ಗೆ ಕರೆ ಮಾಡಿ."
        ),
        "immediate_danger": (
            "ನೀವು ಅಥವಾ ನಿಮ್ಮ ಮಗು ತಕ್ಷಣದ ಅಪಾಯದಲ್ಲಿದ್ದರೆ, ದಯವಿಟ್ಟು 112 ಗೆ ಕರೆ ಮಾಡಿ. ಮಾನಸಿಕ ಆರೋಗ್ಯ ಬೆಂಬಲಕ್ಕಾಗಿ ಟೆಲಿ-ಮಾನಸ್ 14416 ಗೆ ಕರೆ ಮಾಡಿ."
        ),
    },
    "ta": {
        "self_harm": (
            "உங்கள் வலியை நான் உணர்கிறேன், ஆனால் நீங்கள் தனியாக இல்லை. தயவுசெய்து உடனடியாக அவசர உதவியை தொடர்பு கொள்ளுங்கள்:\n"
            "• இந்தியாவில்: டெலி-மானாஸ் (Tele-MANAS) இலவச உதவி எண் 14416 அல்லது 1800-891-4416 (24/7 இலவச மனநல ஆதரவு), "
            "அல்லது அவசர உதவிக்கு 112 ஐ அழைக்கவும்."
        ),
        "infant_harm": (
            "குழந்தைக்கு தீங்கு விளைவிக்கும் எண்ணங்கள் தோன்றினால், தயவுசெய்து குழந்தையை தொட்டிலில் (crib) பாதுகாப்பாக படுக்க வைத்து, "
            "அடுத்த அறைக்குச் சென்று உடனடியாக உதவி பெறுங்கள்:\n"
            "• டெலி-மானாஸ்: 14416 அல்லது 1800-891-4416, அல்லது அவசர எண் 112 / 108 ஐ அழைக்கவும்."
        ),
        "immediate_danger": (
            "நீங்களோ அல்லது குழந்தையோ உடனடி ஆபத்தில் இருந்தால் உடனடியாக 112 ஐ அழைக்கவும். மனநல உதவிக்கு 14416 ஐ அழைக்கவும்."
        ),
    },
    "te": {
        "self_harm": (
            "మీ బాధను నేను అర్థం చేసుకోగలను, కానీ మీరు ఒంటరిగా లేరు. దయచేసి వెంటనే అత్యవసర సహాయాన్ని సంప్రదించండి:\n"
            "• భారతదేశంలో: టెలి-మానస్ (Tele-MANAS) టోల్-ఫ్రీ 14416 లేదా 1800-891-4416 కు కాల్ చేయండి (24/7 ఉచిత మానసిక ఆరోగ్య మద్దతు), "
            "లేదా అత్యవసర సేవల కోసం 112 కు కాల్ చేయండి."
        ),
        "infant_harm": (
            "బిడ్డకు హాని కలిగించే ఆలోచనలు వస్తుంటే, దయచేసి బిడ్డను ఊయలలో (crib) సురక్షితంగా పడుకోబెట్టి, "
            "వేరే గదిలోకి వెళ్లి వెంటనే సహాయం పొందండి:\n"
            "• టెలి-మానస్ టోల్-ఫ్రీ: 14416 లేదా 1800-891-4416 కు కాల్ చేయండి, లేదా 112 / 108 కు కాల్ చేయండి."
        ),
        "immediate_danger": (
            "మీరు లేదా మీ బిడ్డ ప్రమాదంలో ఉంటే వెంటనే 112 కు కాల్ చేయండి. మానసిక ఆరోగ్య సహాయానికి 14416 కు కాల్ చేయండి."
        ),
    },
    "ml": {
        "self_harm": (
            "നിങ്ങളുടെ വേദന ഞാൻ മനസ്സിലാക്കുന്നു, എന്നാൽ നിങ്ങൾ തനിച്ചല്ല. ദയവായി ഉടൻ തന്നെ അടിയന്തര സഹായം തേടുക:\n"
            "• ഇന്ത്യയിൽ: ടെലി-മാനസ് (Tele-MANAS) ടോൾ-ഫ്രീ 14416 അല്ലെങ്കിൽ 1800-891-4416 (24/7 സൗജന്യ മാനസികാരോഗ്യ സഹായം), "
            "അല്ലെങ്കിൽ അടിയന്തര സേവനങ്ങൾക്ക് 112 വിളിക്കുക."
        ),
        "infant_harm": (
            "കുഞ്ഞിനെ ഉപദ്രവിക്കാനുള്ള ചിന്തകൾ തോന്നുന്നുവെങ്കിൽ, ദയവായി കുഞ്ഞിനെ തൊട്ടിലിൽ (crib) സുരക്ഷിതമായി കിടത്തി, "
            "മറ്റൊരു മുറിയിലേക്ക് മാറി ഉടൻ തന്നെ സഹായം തേടുക:\n"
            "• ടെലി-മാനസ് ടോൾ-ഫ്രീ: 14416 അല്ലെങ്കിൽ 1800-891-4416, അല്ലെങ്കിൽ 112 / 108 വിളിക്കുക."
        ),
        "immediate_danger": (
            "നിങ്ങളോ കുഞ്ഞോ അടിയന്തര അപകടത്തിലാണെങ്കിൽ ഉടൻ തന്നെ 112 വിളിക്കുക. മാനസികാരോഗ്യ സഹായത്തിനായി 14416 വിളിക്കുക."
        ),
    },
    "bn": {
        "self_harm": (
            "আপনার কষ্ট আমি বুঝতে পারছি, কিন্তু জানবেন আপনি একা নন। দয়া করে অবিলম্বে জরুরি সহায়তায় যোগাযোগ করুন:\n"
            "• ভারতে: টেলি-মানস (Tele-MANAS) টোল-ফ্রি 14416 বা 1800-891-4416 (24/7 বিনামূল্যে মানসিক স্বাস্থ্য সহায়তা), "
            "বা জরুরি পরিষেবার জন্য 112 তে কল করুন।"
        ),
        "infant_harm": (
            "শিশুকে আঘাত করার চিন্তা এলে, দয়া করে শিশুকে বিছানায় বা দোলনায় (crib) নিরাপদে রাখুন, "
            "অন্য ঘরে যান এবং অবিলম্বে সাহায্য নিন:\n"
            "• টেলি-মানস টোল-ফ্রি: 14416 বা 1800-891-4416, বা জরুরি নম্বর 112 / 108 এ কল করুন।"
        ),
        "immediate_danger": (
            "আপনি বা আপনার শিশু তাৎক্ষণিক বিপদে পড়লে অবিলম্বে 112 তে কল করুন। মানসিক স্বাস্থ্য সহায়তার জন্য টেলি-মানস 14416 তে কল করুন।"
        ),
    },
    "mr": {
        "self_harm": (
            "तुम्हाला होणारा त्रास मला समजतोय, पण तुम्ही एकट्या नाही आहात. कृपया लगेचच मदतीसाठी संपर्क करा:\n"
            "• भारतात: टेली-मानस (Tele-MANAS) टोल-फ्री 14416 किंवा 1800-891-4416 (24/7 मोफत मानसिक आरोग्य सहाय्य), "
            "किंवा आणीबाणी सेवेसाठी 112 वर कॉल करा."
        ),
        "infant_harm": (
            "बाळाला इजा करण्याचे विचार येत असल्यास, कृपया बाळाला पाळण्यात (crib) सुरक्षित ठेवा, "
            "दुसऱ्या खोलीत जा आणि लगेच मदत मिळवा:\n"
            "• टेली-मानस टोल-फ्री: 14416 किंवा 1800-891-4416, किंवा आणीबाणीसाठी 112 / 108 वर कॉल करा."
        ),
        "immediate_danger": (
            "तुम्ही किंवा बाळ धोक्यात असल्यास त्वरित 112 वर कॉल करा. मानसिक आरोग्यासाठी 14416 वर कॉल करा."
        ),
    },
}


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
    # Multilingual self-harm patterns: Hindi / Marathi / Kannada / Tamil / Telugu / Malayalam / Bengali
    re.compile(r"(?:खुद\s*को\s*मार|आत्महत्या|मरना\s*चाहती|जान\s*देना|जीने\s*का\s*मन\s*नहीं|स्वतःला\s*मार|जीव\s*द्यावा)", re.IGNORECASE),
    re.compile(r"(?:ಆತ್ಮಹತ್ಯೆ|ಸಾಯಬೇಕು|ಪ್ರಾಣ\s*ತೆಗೆದುಕೊಳ್ಳ|ನನ್ನನ್ನು\s*ನಾನೇ\s*ಕೊಲ್ಲ)", re.IGNORECASE),
    re.compile(r"(?:தற்கொலை|சாக\s*வேண்டும்|என்னை\s*நானே\s*கொன்று|உயிரை\s*விட)", re.IGNORECASE),
    re.compile(r"(?:ఆత్మహత్య|చనిపోవాలని|నన్ను\s*నేను\s*చంపు|ప్రాణం\s*తీసుకోవ)", re.IGNORECASE),
    re.compile(r"(?:ആത്മഹത്യ|മരിക്കണം|എന്നെത്തന്നെ\s*കൊല്ലാൻ|ജീവനൊടുക്കാൻ)", re.IGNORECASE),
    re.compile(r"(?:আত্মহত্যা|মরতে\s*চাই|নিজেকে\s*মেরে\s*ফেল|বেঁচে\s*থাকার\s*ইচ্ছে\s*নেই)", re.IGNORECASE),
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
    # Multilingual infant-harm patterns
    re.compile(r"(?:बच्चे\s*को\s*(?:मार|चोट|नुकसान|फेंक|दबा)|शिशु\s*को\s*मार|बाळाला\s*(?:मार|इजा|फेक|त्रास))", re.IGNORECASE),
    re.compile(r"(?:ಮಗುವನ್ನು\s*(?:ಕೊಲ್ಲ|ಹೊಡೆ|ಎಸೆ|ಸಾಯಿಸ|ಉಸಿರುಗಟ್ಟಿಸ)|ಕೂಸಿಗೆ\s*ಹಾನಿ)", re.IGNORECASE),
    re.compile(r"(?:குழந்தையை\s*(?:கொல்ல|காயப்படுத்த|தூக்கி\s*வீச|அழிக்க))", re.IGNORECASE),
    re.compile(r"(?:బిడ్డను\s*(?:చంప|గాయపరచ|విసిరే|హాని))", re.IGNORECASE),
    re.compile(r"(?:കുഞ്ഞിനെ\s*(?:കൊല്ല|ദ്രോഹിക്ക|എറിയാൻ|ശ്വാസം\s*മുട്ടിക്ക))", re.IGNORECASE),
    re.compile(r"(?:শিশুকে\s*(?:মেরে|আঘাত|ফেলে|ক্ষতি))", re.IGNORECASE),
]

# Patterns indicating immediate external violence or physical crisis
_IMMEDIATE_DANGER_PATTERNS = [
    re.compile(r"\b(?:in\s+immediate\s+danger|someone\s+is\s+attacking\s+me|being\s+abused\s+right\s+now)\b", re.IGNORECASE),
    re.compile(r"\b(?:severe\s+hemorrhage|uncontrolled\s+bleeding|can't\s+breathe|passing\s+out\s+repeatedly)\b", re.IGNORECASE),
    re.compile(r"(?:जीवक\s*धोका|तातडीचा\s*धोका|ತುರ್ತು\s*ಅಪಾಯ|உடனடி\s*ஆபத்து|తీవ్రమైన\s*రక్తస్రావం)", re.IGNORECASE),
]


@dataclass
class SafetyCheckResult:
    """Outcome of the deterministic safety evaluation."""

    is_safe: bool
    category: Optional[str] = None
    emergency_response: Optional[str] = None
    matched_rules: List[str] = field(default_factory=list)
    language: str = "en"


class SafetyGuard:
    """Evaluates text messages deterministically for acute postpartum safety emergencies."""

    def __init__(self) -> None:
        """Initialize compiled patterns for zero-latency deterministic safety evaluation."""
        self._self_harm_rules = _SELF_HARM_PATTERNS
        self._infant_harm_rules = _INFANT_HARM_PATTERNS
        self._danger_rules = _IMMEDIATE_DANGER_PATTERNS

    def evaluate(self, text: str, language: Optional[str] = None) -> SafetyCheckResult:
        """Scan input text for crisis triggers.

        Ordinary postpartum struggles (e.g. 'I am exhausted', 'I have been crying',
        'I feel anxious', 'I feel overwhelmed') MUST NOT be flagged as emergencies.

        Args:
            text: Raw input string from the user.
            language: Optional explicit language code (en, hi, kn, ta, te, ml, bn, mr).
                If omitted, automatically detected from text.

        Returns:
            SafetyCheckResult indicating safety status, category, and urgent response if triggered.
        """
        if not text or not text.strip():
            return SafetyCheckResult(is_safe=True)

        cleaned = text.strip()
        lang = (language or detect_language(cleaned) or "en").lower()
        if lang not in EMERGENCY_RESPONSES_BY_LANGUAGE:
            lang = "en"

        # 1. Check Infant Harm first (highest urgency in maternal mental health)
        for pattern in self._infant_harm_rules:
            if pattern.search(cleaned):
                responses = EMERGENCY_RESPONSES_BY_LANGUAGE.get(lang, EMERGENCY_RESPONSES_BY_LANGUAGE["en"])
                return SafetyCheckResult(
                    is_safe=False,
                    category="infant_harm",
                    emergency_response=responses["infant_harm"],
                    matched_rules=["INFANT_HARM_INTENT"],
                    language=lang,
                )

        # 2. Check Self-Harm / Suicide
        for pattern in self._self_harm_rules:
            if pattern.search(cleaned):
                responses = EMERGENCY_RESPONSES_BY_LANGUAGE.get(lang, EMERGENCY_RESPONSES_BY_LANGUAGE["en"])
                return SafetyCheckResult(
                    is_safe=False,
                    category="self_harm",
                    emergency_response=responses["self_harm"],
                    matched_rules=["SELF_HARM_OR_SUICIDAL_INTENT"],
                    language=lang,
                )

        # 3. Check Immediate Danger / Physical Emergency
        for pattern in self._danger_rules:
            if pattern.search(cleaned):
                responses = EMERGENCY_RESPONSES_BY_LANGUAGE.get(lang, EMERGENCY_RESPONSES_BY_LANGUAGE["en"])
                return SafetyCheckResult(
                    is_safe=False,
                    category="immediate_danger",
                    emergency_response=responses["immediate_danger"],
                    matched_rules=["IMMEDIATE_PHYSICAL_DANGER"],
                    language=lang,
                )

        # Clean / Safe for supportive LLM engagement
        return SafetyCheckResult(is_safe=True, language=lang)
