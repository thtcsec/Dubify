from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.logging import DubifyLogger
from app.api.endpoints import router as api_router
from app.core.worker import worker

# ─── Initialize Global Logging FIRST ────────────────────────────────────────
DubifyLogger.setup(level="DEBUG" if settings.DEBUG else "INFO")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


@app.on_event("startup")
async def startup_event():
    worker.start()


@app.on_event("shutdown")
async def shutdown_event():
    worker.stop()


# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount Storage for public access
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")


@app.get("/")
def root():
    return {"message": "Welcome to Dubify API", "status": "active"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
