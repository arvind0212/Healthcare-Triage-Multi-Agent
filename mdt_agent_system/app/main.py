import uvicorn
import logging.config
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mdt_agent_system.app.core.config.settings import settings
from mdt_agent_system.app.core.logging.log_config import LOGGING_CONFIG
from mdt_agent_system.app.core.status.service import StatusUpdateService, get_status_service

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services
    logger.info("Application startup...")
    # Initialize StatusUpdateService singleton instance
    status_service = get_status_service()
    logger.info(f"StatusUpdateService initialized: {status_service}")
    # You could initialize other services here (e.g., DB connections)
    yield
    # Shutdown: Cleanup resources
    logger.info("Application shutdown...")
    # Perform cleanup if needed (e.g., close DB connections)

app = FastAPI(
    title="MDT Agent System",
    version="1.0.0",
    description="A multi-agent system simulating a Multi-Disciplinary Team meeting for healthcare case review.",
    lifespan=lifespan # Add the lifespan context manager
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/health", tags=["Health Check"])
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}

# Add API routers
from .api import endpoints
app.include_router(endpoints.router)

if __name__ == "__main__":
    # Use settings object directly
    # Assuming HOST, PORT, RELOAD are needed settings (add them if not present)
    host = getattr(settings, 'HOST', '127.0.0.1') # Provide defaults
    port = getattr(settings, 'PORT', 8000)
    reload = getattr(settings, 'RELOAD', settings.DEBUG) # Use DEBUG if RELOAD not set

    logger.info(f"Starting Uvicorn server on {host}:{port}")
    # Note: Run with `uvicorn mdt_agent_system.app.main:app --reload` from the root directory
    # or by running this script directly
    uvicorn.run(
        "mdt_agent_system.app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=settings.LOG_LEVEL.lower() # Uvicorn uses lowercase log levels
    ) 