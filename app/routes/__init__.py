from app.routes.api import api_router
from app.routes.frontend import mount_frontend
from app.routes.frontend import router as frontend_router

__all__ = ["api_router", "frontend_router", "mount_frontend"]
