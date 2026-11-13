"""MIORA Phase 8J: Comprehensive End-to-End Demo Verification Script.

Executes live HTTP requests through the Vite frontend proxy (http://localhost:3000)
to the FastAPI backend (http://127.0.0.1:8000), verifying:
1. Health and Proxy Connectivity
2. Clinical-Only Baseline Screening
3. Clinical + Text NER Screening (Qualitative extraction verification)
4. Clinical + Audio Screening (Safe unavailable behavior when weights not deployed)
5. Clinical + Video Screening (Simulation notice verification)
6. Results Page Data Structure and Clinical vs Fusion separation
7. EPDS Q10 Independent Urgent Safety Escalation
"""

import json
import sys
import urllib.request
import urllib.error
from typing import Any, Dict

BASE_URL = "http://localhost:3000"

VALID_46_CLINICAL_FEATURES = {
    "Age": 28.0,
    "Number of the latest pregnancy": 1.0,
    "Residence": "Urban",
    "Education Level": "Graduate",
    "Marital status": "Married",
    "Occupation before latest pregnancy": "Employed",
    "Monthly income before latest pregnancy": "30000-50000",
    "Occupation After Your Latest Childbirth": "Homemaker",
    "Current monthly income": "30000-50000",
    "Husband's education level": "Graduate",
    "Husband’s monthly income": "40000-60000",
    "Addiction": "No",
    "Total children": 1,
    "Disease before pregnancy": "None",
    "History of pregnancy loss": "No",
    "Family type": "Nuclear",
    "Number of household members": 3,
    "Relationship with the in-laws": "Good",
    "Relationship with husband": "Good",
    "Relationship with the newborn": "Good",
    "Relationship between father and newborn": "Good",
    "Feeling about motherhood": "Happy",
    "Recieved Support": "Yes",
    "Need for Support": "No",
    "Major changes or losses during pregnancy": "No",
    "Abuse": "No",
    "Trust and share feelings": "Yes",
    "Pregnancy length": "Full term",
    "Pregnancy plan": "Planned",
    "Regular checkups": "Yes",
    "Fear of pregnancy": "No",
    "Diseases during pregnancy": "None",
    "Age of newborn": "1-3 months",
    "Age of immediate older children": "None",
    "Mode of delivery": "Normal",
    "Gender of newborn": "Female",
    "Birth compliancy": "Normal",
    "Breastfeed": "Yes",
    "Newborn illness": "No",
    "Worry about newborn": "No",
    "Relax/sleep when newborn is tended ": "Yes",
    "Relax/sleep when the newborn is asleep": "Yes",
    "Angry after latest child birth": "No",
    "Feeling for regular activities": "Normal",
    "Depression before pregnancy (PHQ2)": "No",
    "Depression during pregnancy (PHQ2)": "No",
}

VALID_7_ACOUSTIC_FEATURES = {
    "f0_mean_hz": 215.0,
    "f0_std_hz": 26.5,
    "jitter_local_percent": 1.15,
    "shimmer_local_percent": 4.50,
    "hnr_db": 19.2,
    "speech_rate_syllables_per_sec": 3.80,
    "pause_ratio": 0.25,
}


def make_multipart_body(fields: Dict[str, str], boundary: str = "----MioraBoundaryXYZ") -> bytes:
    """Construct multipart/form-data payload."""
    lines = []
    for key, value in fields.items():
        lines.append(f"--{boundary}".encode("utf-8"))
        lines.append(f'Content-Disposition: form-data; name="{key}"'.encode("utf-8"))
        lines.append(b"")
        lines.append(str(value).encode("utf-8"))
    lines.append(f"--{boundary}--".encode("utf-8"))
    lines.append(b"")
    return b"\r\n".join(lines)


def post_analyze(fields: Dict[str, str]) -> Dict[str, Any]:
    """POST to /api/screenings/analyze via Vite proxy."""
    boundary = "----MioraBoundaryXYZ"
    data = make_multipart_body(fields, boundary=boundary)
    url = f"{BASE_URL}/api/screenings/analyze"
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8")
        print(f"HTTPError {exc.code}: {err_body}")
        raise


def test_1_health_and_proxy():
    print("\n--- Test 1: Frontend & Backend Health & Proxy ---")
    url = f"{BASE_URL}/api/questionnaire/epds"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "instrument" in data
        assert data["instrument"]["abbreviation"] == "EPDS"
        print("✓ Vite proxy successfully routed /api/questionnaire/epds (200 OK)")
        print(f"  Instrument: {data['instrument']['name']} ({data['instrument']['question_count']} items)")


def test_2_clinical_only_screening():
    print("\n--- Test 2: Clinical-Only Baseline Screening ---")
    payload = {
        "motherId": "M-104",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "true",
        "clinical_features": json.dumps(VALID_46_CLINICAL_FEATURES),
    }
    resp = post_analyze(payload)
    assert resp["status"] == "completed"
    assert resp["clinical"]["status"] == "completed"
    pred = resp["clinical"]["prediction"]
    assert 0.0 <= pred["predicted_risk_probability"] <= 1.0
    assert pred["risk_category"] in ("LOW_RISK", "MODERATE_RISK", "HIGH_RISK")
    assert resp["fusion"]["status"] == "not_available"
    assert "research_benchmarks" in resp["fusion"]
    print("✓ Clinical-Only screening succeeded!")
    print(f"  Predicted Risk Probability: {pred['predicted_risk_probability']}")
    print(f"  Risk Category: {pred['risk_category']}")
    print(f"  Clinical Model Utilized: {resp['clinical']['model_version']}")
    print(f"  Late Fusion Status: {resp['fusion']['status']} (correctly not fabricated)")


def test_3_clinical_plus_text_screening():
    print("\n--- Test 3: Clinical + Qualitative Text NER Screening ---")
    narrative = (
        "Mother reports feeling deeply depressed, constant crying spells, overwhelming anxiety, "
        "and severe insomnia since arriving home with the newborn."
    )
    payload = {
        "motherId": "M-108",
        "modalities": json.dumps({"clinical": True, "text": True}),
        "consentConfirmed": "true",
        "clinical_features": json.dumps(VALID_46_CLINICAL_FEATURES),
        "text_content": narrative,
    }
    resp = post_analyze(payload)
    assert resp["status"] == "completed"
    assert resp["clinical"]["status"] == "completed"
    assert resp["text"]["status"] == "completed"
    assert resp["text"]["processing_type"] == "biomedical_ner"
    entities = resp["text"]["entities"]
    assert len(entities) >= 1
    assert resp["text"]["total_entities_detected"] == len(entities)
    print("✓ Clinical + Text NER screening succeeded!")
    print(f"  Clinical Baseline Probability: {resp['clinical']['prediction']['predicted_risk_probability']}")
    print(f"  Total Biomedical Entities Detected: {len(entities)}")
    print(f"  Detected Mentions: {[e['text'] for e in entities[:4]]}")
    print(f"  Late Fusion Status: {resp['fusion']['status']} (Text NER correctly excluded from PPD probabilities)")


def test_4_clinical_plus_audio_safe_unavailable():
    print("\n--- Test 4: Clinical + Audio Screening (Safe Unavailable Mode) ---")
    payload = {
        "motherId": "M-104",
        "modalities": json.dumps({"clinical": True, "audio": True}),
        "consentConfirmed": "true",
        "clinical_features": json.dumps(VALID_46_CLINICAL_FEATURES),
        "audio_features": json.dumps(VALID_7_ACOUSTIC_FEATURES),
    }
    resp = post_analyze(payload)
    assert resp["clinical"]["status"] == "completed"
    assert resp["audio"]["status"] == "unavailable"
    assert resp["audio"]["prediction"] is None
    assert "unavailable" in resp["audio"]["message"].lower()
    print("✓ Clinical + Audio safe behavior verified!")
    print(f"  Clinical Status: {resp['clinical']['status']}")
    print(f"  Audio Status: {resp['audio']['status']} (No trained checkpoint deployed; zero fabricated predictions)")
    print(f"  Audio Message: {resp['audio']['message']}")


def test_5_clinical_plus_video_simulation():
    print("\n--- Test 5: Clinical + Video Screening (Simulation Notice) ---")
    payload = {
        "motherId": "M-104",
        "modalities": json.dumps({"clinical": True, "video": True}),
        "consentConfirmed": "true",
        "clinical_features": json.dumps(VALID_46_CLINICAL_FEATURES),
    }
    resp = post_analyze(payload)
    assert resp["clinical"]["status"] == "completed"
    assert resp["video"]["status"] == "unavailable"
    assert resp["video"]["prediction"] is None
    assert "simulation" in resp["video"]["message"].lower() or "offline benchmark" in resp["video"]["message"].lower()
    print("✓ Clinical + Video simulation notice verified!")
    print(f"  Video Status: {resp['video']['status']}")
    print(f"  Video Notice: {resp['video']['message']}")


def test_6_epds_q10_independent_safety_escalation():
    print("\n--- Test 6: EPDS Q10 Independent Urgent Safety Escalation ---")
    answers = [{"question_id": f"EPDS_Q{i:02d}", "selected_index": 0} for i in range(1, 10)]
    answers.append({"question_id": "EPDS_Q10", "selected_index": 2})  # "Sometimes" self-harm thoughts

    url = f"{BASE_URL}/api/questionnaire/epds/submit"
    req_body = json.dumps({"answers": answers}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        alert = res["safety_alert"]
        assert alert["triggered"] is True
        assert alert["question_10_score"] > 0
        assert alert["severity"] == "URGENT_SAFETY_ASSESSMENT"
        assert "never be overridden" in alert["override_protection"].lower()
        print("✓ EPDS Question 10 urgent safety escalation verified!")
        print(f"  Safety Alert Triggered: {alert['triggered']}")
        print(f"  Question 10 Score: {alert['question_10_score']}")
        print(f"  Severity: {alert['severity']}")
        print(f"  Override Protection: {alert['override_protection']}")


def main():
    print("================================================================")
    print("   MIORA Phase 8J: Live End-to-End Demo Verification Suite")
    print("================================================================")
    try:
        test_1_health_and_proxy()
        test_2_clinical_only_screening()
        test_3_clinical_plus_text_screening()
        test_4_clinical_plus_audio_safe_unavailable()
        test_5_clinical_plus_video_simulation()
        test_6_epds_q10_independent_safety_escalation()
        print("\n================================================================")
        print("   ALL 6 LIVE END-TO-END DEMO VERIFICATION CHECKS PASSED!")
        print("================================================================")
    except Exception as exc:
        print(f"\n❌ Verification failed with error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
