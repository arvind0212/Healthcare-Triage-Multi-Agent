import uvicorn
import logging.config
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from mdt_agent_system.app.core.config.settings import settings
from mdt_agent_system.app.core.logging.log_config import LOGGING_CONFIG
from mdt_agent_system.app.core.status.service import StatusUpdateService, get_status_service

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    status_service = get_status_service()
    logger.info(f"StatusUpdateService initialized: {status_service}")
    yield
    logger.info("Application shutdown...")

app = FastAPI(
    title="MDT Agent System",
    version="1.0.0",
    description="A multi-agent system simulating a Multi-Disciplinary Team meeting for healthcare case review.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/", tags=["UI"])
async def root():
    """Root endpoint that serves the main UI page."""
    from fastapi.responses import FileResponse
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)

@app.get("/health", tags=["Health Check"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}

from .api import endpoints
app.include_router(endpoints.router, prefix="/api")

if __name__ == "__main__":
    host = getattr(settings, 'HOST', '127.0.0.1')
    port = getattr(settings, 'PORT', 8000)
    reload = getattr(settings, 'RELOAD', settings.DEBUG)

    logger.info(f"Starting Uvicorn server on {host}:{port}")
    uvicorn.run(
        "mdt_agent_system.app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=settings.LOG_LEVEL.lower()
    )