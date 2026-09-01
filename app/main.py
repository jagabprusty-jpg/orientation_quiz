import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.exceptions import AppException
from app.routes.student import router as student_router
from app.routes.quiz import router as quiz_router
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.ws import router as ws_router

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler:
    Initializes database tables on startup.
    """
    create_db_and_tables()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for Live Janmashtami College Quiz with WebSocket real-time synchronization, admin authentication, independent rounds, and fast response-time leaderboard.",
    lifespan=lifespan,
)

# Configure CORS
origins = settings.CORS_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for custom application exceptions
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
        },
        headers=headers,
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Include Routers under API Prefix
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(student_router, prefix=settings.API_PREFIX)
app.include_router(quiz_router, prefix=settings.API_PREFIX)
app.include_router(admin_router, prefix=settings.API_PREFIX)
app.include_router(ws_router, prefix=settings.API_PREFIX)

# Serve Frontend static assets
if os.path.exists(frontend_dir):
    css_dir = os.path.join(frontend_dir, "css")
    js_dir = os.path.join(frontend_dir, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

    @app.get("/", tags=["Frontend"])
    def serve_frontend_root():
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
        }

    @app.get("/admin", tags=["Frontend"])
    def serve_admin_root():
        admin_path = os.path.join(frontend_dir, "admin.html")
        if os.path.exists(admin_path):
            return FileResponse(admin_path)
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
        }
