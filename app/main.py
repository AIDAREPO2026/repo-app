"""Create the FastAPI application and include every module's router.

Run locally with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.accounts.router import router as accounts_router
from app.audit.router import router as audit_router
from app.content.router import router as content_router
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
    application = FastAPI(title="AIDA Digital Resource Repository", docs_url=None, redoc_url=None)
    for router in ROUTERS:
        application.include_router(router)

    @application.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        """Report liveness only, with no version or dependency detail (P6-OPS-02)."""
        return {"status": "ok"}

    return application


app = create_app()
