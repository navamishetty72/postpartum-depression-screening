# Backend REST API

## Overview
This module exposes FastAPI REST endpoints for real-time and batch clinical screening inference.

## Endpoints
- `GET /`: Health check and system metadata.
- `POST /predict/clinical`: Single-record clinical inference.
- `POST /predict/clinical/batch`: Batch clinical inference.
- `POST /predict/multimodal`: 4-branch late fusion inference.
- `POST /predict/multimodal/batch`: Batch multimodal inference.
