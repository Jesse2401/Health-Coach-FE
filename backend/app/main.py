from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from contextlib import asynccontextmanager
import logging

from app.api.routes import router
from app.database import engine, Base
from app.services.redis_service import RedisService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting up...")
    
    try:
        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    try:
        # Initialize Redis connection
        await RedisService.get_instance()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed (non-fatal): {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    try:
        await RedisService.close()
    except Exception as e:
        logger.warning(f"Redis cleanup error: {e}")
    
    try:
        await engine.dispose()
    except Exception as e:
        logger.warning(f"Database cleanup error: {e}")
    
    logger.info("Cleanup complete")


app = FastAPI(
    title="AI Health Coach",
    description="A WhatsApp-like AI health coaching chat application",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration - allow common development ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with user-friendly messages."""
    errors = exc.errors()
    
    # Extract meaningful error messages
    error_messages = []
    for error in errors:
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "Invalid value")
        
        # Make common errors more user-friendly
        if "string_too_long" in str(error.get("type", "")):
            msg = "Message is too long. Please keep it under 4000 characters."
        elif "string_too_short" in str(error.get("type", "")):
            msg = "Message cannot be empty."
        elif "missing" in str(error.get("type", "")):
            msg = f"Required field '{field}' is missing."
        
        error_messages.append(msg)
    
    detail = error_messages[0] if len(error_messages) == 1 else "; ".join(error_messages)
    
    logger.warning(f"Validation error: {detail}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": detail}
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    """Handle Pydantic model validation errors."""
    logger.warning(f"Pydantic validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid request data. Please check your input."}
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    logger.warning(f"Value error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again."}
    )


# Include API routes
app.include_router(router)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "ai-health-coach"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "AI Health Coach API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
