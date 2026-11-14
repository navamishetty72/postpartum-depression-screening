"""FastAPI backend application for the PPD Screening Research Prototype."""

from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables early before database or service imports
load_dotenv()
_project_root = Path(__file__).resolve().parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file, override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.care_plans import router as care_plans_router
from backend.routers.clinical_reviews import router as clinical_reviews_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.mothers import router as mothers_router
from backend.routers.questionnaire import router as questionnaire_router
from backend.routers.screenings import router as screenings_router
from backend.routers.text_ner import router as text_ner_router
from backend.routers.clinical_numerical import router as clinical_router
from backend.routers.screening import router as screening_router
from backend.routers.voice_assistant import router as voice_assistant_router
from backend.database.connection import init_db
from backend.services.text_ner_service import text_ner_service
from backend.services.clinical_service import clinical_service
from backend.services.audio_service import audio_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application startup and shutdown lifecycle (load ML services once)."""
    try:
        init_db()
    except Exception:
        pass
    text_ner_service.startup()
    clinical_service.startup()
    audio_service.startup()
    yield
    audio_service.shutdown()
    clinical_service.shutdown()
    text_ner_service.shutdown()


app = FastAPI(
    title="PPD Screening Research Prototype API",
    version="1.0.0",
    description=(
        "Multimodal clinical screening research prototype for Postpartum Depression (PPD), "
        "including verified EPDS scoring, biomedical text entity extraction, "
        "and clinical numerical risk prediction."
    ),
    lifespan=lifespan,
)

# Enable CORS for local and staging React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(questionnaire_router)
app.include_router(text_ner_router)
app.include_router(mothers_router)
app.include_router(screenings_router)
app.include_router(clinical_reviews_router)
app.include_router(care_plans_router)
app.include_router(dashboard_router)




app.include_router(clinical_router)
app.include_router(screening_router)
app.include_router(voice_assistant_router)


@app.get("/", tags=["Health Check"])
def root_health_check() -> dict:
    """Root endpoint for health check and service status."""
    return {
        "status": "online",
        "service": "PPD Screening API",
        "version": "1.0.0",
        "is_diagnostic": False,
        "disclaimer": "Research prototype only. Not for clinical diagnostic use.",
    }
