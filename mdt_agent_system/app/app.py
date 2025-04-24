"""
MDT Agent System - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MDT Agent System",
        description="Simulated Multi-Disciplinary Team Agent System",
        version="1.0.0"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    # Import and include API routers
    from mdt_agent_system.app.api.endpoints import router as api_router
    app.include_router(api_router, prefix="/api")
    
    # Mount static files
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Root route to serve the static index.html
    @app.get("/")
    async def root():
        """Serve the main application page."""
        from fastapi.responses import FileResponse
        index_path = os.path.join(static_dir, "index.html")
        return FileResponse(index_path)

    return app
