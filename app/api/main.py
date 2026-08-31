"""
Project Expert AI
FastAPI Main v3

Application entry point.
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.api.routes import router
from app.api.norms import router as norms_router


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
""",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep the general API router for existing endpoints.
app.include_router(router)

# Register norms directly on the application so the complete
# /api/norms route table is explicit and independently testable.
# This avoids relying on nested router inclusion for the upload route.
app.include_router(norms_router)


@app.on_event("startup")
def startup_event():
    print("=" * 70)
    print("Starting Project Expert AI API")
    print("Version: 0.1.0")
    print("API documentation: /docs")
    print("=" * 70)
