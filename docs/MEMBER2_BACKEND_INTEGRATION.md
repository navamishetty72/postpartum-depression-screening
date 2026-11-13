# Member 2: Database & Clinical Application Backend Integration Guide

This document details the complete Member 2 clinical application backend architecture, available API endpoints, request/response models, database migrations, and operational guidelines for the MIORA Postpartum Depression Screening Platform.

---

## 1. Architectural Boundaries & Ownership

- **Member 1 owns**:
  - Multimodal clinical analysis (`POST /api/screenings/analyze`)
  - Audio CNN processing, Video pipeline, and Text NER inference (`POST /api/text-ner/extract`)
  - EPDS scoring algorithms (`/api/questionnaire/epds`, `/api/questionnaire/epds/submit`)
  - Multimodal discordance and late fusion
- **Member 2 owns**:
  - PostgreSQL / SQLAlchemy 2.0 declarative database foundation & connection pooling
  - Alembic database migration management
  - Mother patient management (`/api/mothers`)
  - Multimodal screening persistence service & screening history retrieval (`/api/screenings`)
  - Clinician-managed clinical reviews (`/api/clinical-reviews`)
  - Prioritized care plan management (`/api/care-plans`)
  - Clinical screening handoff routing (`/api/screenings/{screening_id}/handoff`)
  - Regulatory HIPAA/ISO audit logging (`AuditLog`)
  - Dashboard analytics (`/api/dashboard/metrics`, `/api/dashboard/screening-activity`, `/api/dashboard/alerts`)

---

## 2. Implemented Endpoints & Contracts

### A. Mother Management
- `POST /api/mothers`: Register a new mother record.
- `GET /api/mothers`: Paginated list of registered mothers (`skip`, `limit`).
- `GET /api/mothers/{mother_id}`: Retrieve details for a specific mother UUID.
- `PUT /api/mothers/{mother_id}`: Partially update an existing mother record.

### B. Screening Persistence & History
- `GET /api/mothers/{mother_id}/screenings`: Retrieve all screenings for a mother, ordered newest first.
- `GET /api/screenings/{screening_id}`: Retrieve an individual screening by UUID.
- `ScreeningService.persist_screening(db, data)`: Internal persistence interface invoked by Member 1 after `/api/screenings/analyze`.

### C. Clinical Reviews
- `POST /api/clinical-reviews`: Clinician-managed review recording confirmation, override, qualitative notes, and immediate escalation.
- `GET /api/mothers/{mother_id}/clinical-reviews`: Retrieve reviews for a mother, ordered newest first.

### D. Care Plans
- `GET /api/mothers/{mother_id}/care-plan`: Retrieve the active care plan for a mother.
- `PUT /api/mothers/{mother_id}/care-plan`: Upsert a mother's care plan (priority: `routine`, `urgent`, `crisis`; interventions: `counseling`, `psychiatry`, `obgyn_followup`, `support_group`, `tele_manas`).

### E. Screening Handoff
- `POST /api/screenings/{screening_id}/handoff`: Initiates clinical handoff, recording the event in the audit log while preserving all original screening data and EPDS Q10 safety alerts.

### F. Dashboard Analytics
- `GET /api/dashboard/metrics`: Summary counts of mothers, screenings, high-risk screenings, pending reviews, and active care plans.
- `GET /api/dashboard/screening-activity?timeframe=4w`: Weekly chronological screening time-series over `4w`, `8w`, or `12w`.
- `GET /api/dashboard/alerts`: Active clinical alerts (EPDS Q10 safety triggers, high-risk screenings, immediate escalations).

---

## 3. Privacy, Audit, & Clinical Safety Guards

1. **Non-Negotiable EPDS Question 10 Invariant**:
   - Any affirmative answer on EPDS Question 10 (`score > 0`) triggers a critical safety alert.
   - It is never erased, overridden, or suppressed by a low total score, model prediction, or clinical review.
2. **Missing Modalities Are Not Low-Risk**:
   - If audio or video modalities fail or are unavailable, they remain explicitly flagged as `unavailable` or `failed`.
   - The platform never fabricates predictions or treats missing data as a negative screen.
3. **Audit Log Privacy Safeguards**:
   - The `audit_logs` table records actor IDs, action verbs, resource identifiers, and timestamps.
   - **Strict Rule**: Raw patient narratives, audio transcripts, forum quotes, passwords, and clinical notes are never stored in audit logs.
4. **Transparent Handoff Semantics**:
   - The `/api/screenings/{screening_id}/handoff` endpoint returns `status="RECORDED_IN_AUDIT_LOG"` and explicitly disclaims external telephony or emergency dispatch unless a live external gateway is integrated.

---

## 4. Known Limitations & Environment Requirements

- **PostgreSQL Database**: Configured via `DATABASE_URL`. SQLAlchemy engine implements connection pooling with automatic fallback to SQLite for local development and unit tests. True PostgreSQL integration testing should be performed in staging with a live PostgreSQL 15+ container.
- **Alembic Migrations**:
  - `001_initial_foundation`: Base schema creation.
  - `002_align_contract`: Contract alignment for mothers and screenings.
  - Apply with: `alembic upgrade head`.

