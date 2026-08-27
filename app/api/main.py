"""
VKS Expert AI
FastAPI Main v2

Purpose:
Application entry point.

Architecture:

Client
  |
  v
FastAPI
  |
  v
API Router
  |
  v
RAG Pipeline
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.api.routes import router



# ==========================================================
# Application
# ==========================================================


app = FastAPI(

    title="VKS Expert AI",

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

    allow_origins=[
        "http://localhost:8080"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)

# ==========================================================
# Routes
# ==========================================================


app.include_router(
    router
)



# ==========================================================
# Startup information
# ==========================================================


@app.on_event(
    "startup"
)
def startup_event():

    print("=" * 70)

    print(
        "Starting VKS Expert AI API"
    )

    print(
        "Version: 0.1.0"
    )

    print(
        "API documentation: /docs"
    )

    print("=" * 70)
    