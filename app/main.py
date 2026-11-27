"""Create the FastAPI application and include every module's router.

Run locally with: uvicorn app.main:app --reload
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from redis import Redis

from app.accounts.router import router as accounts_router
from app.audit.router import router as audit_router
from app.content.router import router as content_router
from app.core.config import load_config
from app.core.db import make_session_factory
from app.core.errors import add_error_pages
from app.core.health import database_answers, redis_answers
from app.core.log_setup import configure_logging
from app.experts.router import router as experts_router
from app.gallery.router import router as gallery_router
from app.kpi.router import router as kpi_router
from app.public.router import router as public_router
from app.search.router import router as search_router
from app.workflow.router import router as workflow_router

STATIC_DIR = Path(__file__).resolve().parent / "static"

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
    # debug stays False everywhere: in debug mode Starlette shows stack traces instead of our 500 page.
    application = FastAPI(
        title="AIDA Digital Resource Repository", debug=False, docs_url=None, redoc_url=None
    )
    application.state.session_factory = make_session_factory(config.database_url)
    # Short timeouts, so a stuck Redis fails the health check instead of hanging it.
    application.state.redis = Redis.from_url(config.redis_url, socket_timeout=2, socket_connect_timeout=2)
    for router in ROUTERS:
        application.include_router(router)
    # ponytail: the app serves /static itself; move it to an Nginx location if traffic ever needs it.
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    add_error_pages(application)

    @application.get("/healthz", include_in_schema=False)
    def healthz(request: Request) -> JSONResponse:
        """Return 200 when the database and Redis answer, else 503, with no detail (P6-OPS-02)."""
        state = request.app.state
        healthy = database_answers(state.session_factory) and redis_answers(state.redis)
        if healthy:
            return JSONResponse({"status": "ok"})
        return JSONResponse({"status": "fail"}, status_code=503)

    return application


app = create_app()
