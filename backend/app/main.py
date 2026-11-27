from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from backend.app.config import settings
from backend.app.middleware.logging_middleware import LoggingAndContextMiddleware
from backend.app.middleware.error_handler import validation_exception_handler, global_exception_handler
from backend.app.database.init_db import init_db

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    description="Production-grade AI Resume Analyzer & Job Matcher REST API",
    version="1.0.0",
)

# Custom logging & request ID middleware (inner)
app.add_middleware(LoggingAndContextMiddleware)

# CORS Middleware (outermost so preflight & error responses always include CORS headers)
_dev_origin_regex = (
    settings.CORS_ORIGIN_REGEX
    or (
        r"^https?://(localhost|127\.0\.0\.1|\[::1\]|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?$"
        if settings.ENVIRONMENT != "production"
        else None
    )
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=_dev_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)


@app.on_event("startup")
async def on_startup():
    """Initialize database tables on startup."""
    init_db()


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint to verify backend service and database status."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "ai_provider": settings.AI_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
    }


# Include API Routers (Auth, Users, Resumes, Jobs, Analysis, Applications, AI)
from backend.app.api import ai, analysis, applications, auth, jobs, resumes, users

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(resumes.router, prefix=f"{settings.API_V1_STR}/resumes", tags=["Resumes"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["Jobs"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_STR}/analysis", tags=["Analysis"])
app.include_router(applications.router, prefix=f"{settings.API_V1_STR}/applications", tags=["Applications"])
app.include_router(ai.router, prefix=f"{settings.API_V1_STR}/ai", tags=["AI Engine"])

