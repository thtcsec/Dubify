import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.logging import DubifyLogger
from app.api.endpoints import router as api_router
from app.core.worker import worker

# ─── Initialize Global Logging FIRST ────────────────────────────────────────
DubifyLogger.setup(level="DEBUG" if settings.DEBUG else "INFO")

logger = logging.getLogger(__name__)


# ─── Lifespan (replaces deprecated on_event) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    worker.start()
    logger.info("Dubify started.")
    yield
    # Shutdown
    worker.stop(timeout=10)
    logger.info("Dubify shut down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)


# ─── CORS ────────────────────────────────────────────────────────────────────
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if settings.DEBUG:
    _cors_origins = ["*"]  # Allow all in dev mode only

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Logging Middleware ──────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info("%s %s → %s (%sms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount Storage for public access
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")


@app.get("/")
def root():
    return {"message": "Welcome to Dubify API", "status": "active"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "engine": settings.normalized_processing_engine(),
        "mode": settings.normalized_processing_mode(),
        "cloud_ready": settings.cloud_engine_ready(),
        "piper_ready": settings.piper_ready(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
