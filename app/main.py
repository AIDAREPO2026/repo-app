"""Create the FastAPI application and include every module's router.

Run locally with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.accounts.router import router as accounts_router
from app.audit.router import router as audit_router
from app.content.router import router as content_router
from app.core.config import load_config
from app.core.db import make_session_factory
from app.core.log_setup import configure_logging
from app.experts.router import router as experts_router
from app.gallery.router import router as gallery_router
from app.kpi.router import router as kpi_router
from app.public.router import router as public_router
from app.search.router import router as search_router
from app.workflow.router import router as workflow_router

# Listed explicitly so a reader can see every part of the app in one place.
ROUTERS = [
    public_router,
    accounts_router,
    content_router,
    workflow_router,
    search_router,
    experts_router,
    gallery_router,
    kpi_router,
    audit_router,
]


def create_app() -> FastAPI:
    """Build the application with all routers included."""
    # Loading config first makes a missing environment variable stop startup with a clear message.
    config = load_config()
    configure_logging()
    application = FastAPI(title="AIDA Digital Resource Repository", docs_url=None, redoc_url=None)
    application.state.session_factory = make_session_factory(config.database_url)
    for router in ROUTERS:
        application.include_router(router)

    @application.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        """Report liveness only, with no version or dependency detail (P6-OPS-02)."""
        return {"status": "ok"}

    return application


app = create_app()
