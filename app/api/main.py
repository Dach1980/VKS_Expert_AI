"""
Project Expert AI
FastAPI Main v8

Application entry point.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.norms import router as norms_router
from app.api.norm_files import router as norm_files_router
from app.api.report_evidence import router as report_evidence_router
from app.api.reports import router as reports_router
from app.api.routes import router
from app.api.skills import router as skills_router


app = FastAPI(
    title="Project Expert AI",
    description="Local Engineering AI Assistant for design documentation analysis.",
    version="0.1.0",
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print(
        f"[Project Expert AI][API] Unhandled {request.method} "
        f"{request.url.path}: {exc}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Внутренняя ошибка API: {exc}"},
    )


app.include_router(router)
for route in norms_router.routes:
    app.router.routes.append(route)
for route in norm_files_router.routes:
    app.router.routes.append(route)
for route in reports_router.routes:
    app.router.routes.append(route)
for route in report_evidence_router.routes:
    app.router.routes.append(route)
for route in skills_router.routes:
    app.router.routes.append(route)


@app.on_event("startup")
def startup_event():
    print("=" * 70)
    print("Starting Project Expert AI API")
    print("Version: 0.1.0")
    print("CORS: localhost/127.0.0.1 on local development ports")
    print("API documentation: /docs")
    print("Knowledge Base API: /api/knowledge-base/query")
    print("RAG diagnostics: /api/knowledge-base/diagnostics")
    print("Knowledge Base status: /api/knowledge-base/status")
    print("Skills API: /api/skills")
    print("Check API: /api/checks/{document_id}")
    print("Report API: /api/reports/{document_id}, /api/reports/pdf, /api/reports/docx")
    print("Evidence API: /api/reports/evidence/{document_id}/{filename}")
    print("=" * 70)


# Keep CORS on the outermost ASGI layer so browser clients also receive
# CORS headers for errors raised below FastAPI's normal exception middleware.
app = CORSMiddleware(
    app,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
