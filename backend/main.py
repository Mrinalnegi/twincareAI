"""
TwinCare AI — FastAPI Application Entry Point

An AI-powered Personal Health Intelligence Platform that builds a living Digital Twin
from uploaded health reports, predicts disease risk with explainable AI, and provides
a conversational health copilot grounded in the user's own data.

Built for AMD Developer Hackathon: ACT II, Track 3 — Unicorn (Open Innovation)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import create_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # --- Startup ---
    logger.info("🚀 Starting TwinCare AI Backend...")

    # Create database tables
    logger.info("Creating database tables...")
    create_tables()
    logger.info("✅ Database tables created")

    # Pre-load the heart disease model
    try:
        from ai.heart_model import load_model
        model = load_model()
        if model:
            logger.info("✅ Heart disease model loaded (PyTorch)")
        else:
            logger.info("⚠️ Heart disease model not found — using rule-based fallback")
    except Exception as e:
        logger.warning(f"⚠️ Could not load heart disease model: {e}")

    # Create uploads directory
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs("ml_models", exist_ok=True)

    logger.info(f"✅ TwinCare AI Backend ready (env={settings.ENVIRONMENT})")
    yield

    # --- Shutdown ---
    logger.info("🛑 Shutting down TwinCare AI Backend...")


# Create FastAPI app
app = FastAPI(
    title="TwinCare AI",
    description=(
        "AI-powered Personal Health Intelligence Platform — "
        "Digital Twin, Risk Prediction, and Health Copilot"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
from routers.auth import router as auth_router
from routers.reports import router as reports_router
from routers.digital_twin import router as digital_twin_router
from routers.risk_predictions import router as risk_predictions_router
from routers.copilot import router as copilot_router
from routers.dashboard import router as dashboard_router
from routers.patient_intake import router as patient_intake_router

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)
app.include_router(digital_twin_router, prefix=API_PREFIX)
app.include_router(risk_predictions_router, prefix=API_PREFIX)
app.include_router(copilot_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(patient_intake_router, prefix=API_PREFIX)


# --- Health check ---
@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for Docker and monitoring."""
    return {
        "status": "healthy",
        "service": "TwinCare AI Backend",
        "version": "1.0.0",
    }


@app.get("/", tags=["System"])
def root():
    """Root endpoint with API info."""
    return {
        "message": "Welcome to TwinCare AI API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }
