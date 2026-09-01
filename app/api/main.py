"""
Project Expert AI
FastAPI Main v4

Application entry point.
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.api.routes import router
from app.api.norms import router as norms_router
from app.api.norm_files import router as norm_files_router
from app.api.reports import router as reports_router


app = FastAPI(
    title="Project Expert AI",
    description="""
Local Engineering AI Assistant
for design documentation analysis.

Capabilities:

- RAG based normative search
- Engineering query classification
- Evidence validation
- Local LLM inference via LM Studio
- PDF and DOCX check report generation
""",
    version="0.1.0",
)

# The frontend may be opened through either localhost or 127.0.0.1.
# Keep both origins explicit so browser requests to the local API receive
# CORS headers even when the hostnames differ.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
for route in norms_router.routes:
    app.router.routes.append(route)
for route in norm_files_router.routes:
    app.router.routes.append(route)
for route in reports_router.routes:
    app.router.routes.append(route)


@app.on_event("startup")
def startup_event():
    print("=" * 70)
    print("Starting Project Expert AI API")
    print("Version: 0.1.0")
    print("API documentation: /docs")
    print("Report API: /api/reports/pdf and /api/reports/docx")
    print("=" * 70)
