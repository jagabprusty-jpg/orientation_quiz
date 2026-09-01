from app.routes.student import router as student_router
from app.routes.quiz import router as quiz_router
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.ws import router as ws_router

__all__ = ["student_router", "quiz_router", "admin_router", "auth_router", "ws_router"]
