"""
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, dolls, events
from app.core.config import settings
from app.db.session import engine
from app.db.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("Starting up Dolls Inventory API...")

    # Validate AUTH_MODE configuration
    if settings.AUTH_MODE == "none":
        if not settings.ALLOW_INSECURE_LOCAL:
            raise RuntimeError(
                "AUTH_MODE=none requires ALLOW_INSECURE_LOCAL=true. "
                "This mode is insecure and should only be used for local development."
            )
        print("WARNING: Running in AUTH_MODE=none (insecure local mode)")
    elif settings.AUTH_MODE == "forwardauth":
        print(f"Running in AUTH_MODE=forwardauth")
    else:
        raise RuntimeError(f"Invalid AUTH_MODE: {settings.AUTH_MODE}. Must be 'none' or 'forwardauth'")

    # Ensure database directory exists
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Database path: {settings.DB_PATH}")

    # Create database tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

    yield

    # Shutdown
    print("Shutting down Dolls Inventory API...")


# Create FastAPI app
app = FastAPI(
    title="Dolls Inventory API",
    description="API for managing dolls inventory and storage locations",
    version="0.2.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(dolls.router, prefix="/api")
app.include_router(events.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Dolls Inventory API",
        "version": "0.2.0",
        "auth_mode": settings.AUTH_MODE,
    }

