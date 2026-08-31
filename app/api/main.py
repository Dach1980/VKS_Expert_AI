"""
Project Expert AI
FastAPI Main v4

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

# FastAPI 0.141.x keeps included routers as _IncludedRouter wrappers.
# Register the already-built norms APIRoute objects directly so that the
# norms API is present in OpenAPI and dispatched by the application exactly
# as declared in app/api/norms.py. No second processing architecture is used.
for route in norms_router.routes:
    app.router.routes.append(route)


@app.on_event("startup")
def startup_event():
    print("=" * 70)
    print("Starting Project Expert AI API")
    print("Version: 0.1.0")
    print("API documentation: /docs")
    print("=" * 70)
