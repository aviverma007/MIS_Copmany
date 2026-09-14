from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import actions, dashboard, export, reports, upload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nbh_mis")

app = FastAPI(
    title=config.APP_TITLE,
    description="Dynamic MIS backend for NBH customer complaint / facility management data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the deployed frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(export.router)
app.include_router(actions.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces / server paths to the client (spec section 41/42).
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred while processing your request. Please try again."},
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "app": config.APP_TITLE}


# ---------------------------------------------------------------------------
# Serve the pre-built React frontend (backend/static/, produced by
# `npm run build` in frontend/) so the whole app runs from a single process
# with zero Node/npm required at runtime -- useful on locked-down corporate
# machines where installing frontend dependencies isn't possible. If the
# static build isn't present (e.g. during frontend development against
# `npm run dev`), fall back to a simple API landing message.
# ---------------------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
STATIC_DIR = os.path.abspath(STATIC_DIR)
INDEX_HTML = os.path.join(STATIC_DIR, "index.html")

if os.path.isdir(os.path.join(STATIC_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

if os.path.isfile(INDEX_HTML):
    @app.get("/", include_in_schema=False)
    def serve_frontend_root():
        return FileResponse(INDEX_HTML)

    # SPA fallback: any non-API, non-doc path (e.g. /dashboard, /reports on a
    # hard refresh) should still return index.html so React Router can take
    # over client-side, instead of a 404.
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_catch_all(full_path: str):
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            raise HTTPException(status_code=404, detail="Not found.")
        return FileResponse(INDEX_HTML)
else:
    @app.get("/")
    def root():
        return {"message": f"{config.APP_TITLE} API. See /docs for the interactive API reference. "
                            "(No built frontend found in backend/static -- run `npm run build` in "
                            "frontend/ and copy dist/* into backend/static/ to serve the UI from here.)"}
