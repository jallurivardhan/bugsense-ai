from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import Base, engine
from app.routes import benchmarks, bug_analysis, documents, health, test_generation

app = FastAPI(
    title="AI Assistant for Software Testing",
    description=(
        "AI-powered platform for bug analysis, test generation, "
        "and QA knowledge management"
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(
    bug_analysis.router, prefix="/api/v1/bug-analysis", tags=["Bug Analysis"]
)
app.include_router(
    test_generation.router,
    prefix="/api/v1/test-generation",
    tags=["Test Generation"],
)
app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["Documents"],
)
app.include_router(
    benchmarks.router,
    prefix="/api/v1/benchmarks",
    tags=["Benchmarks"],
)


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {
        "message": "AI Assistant for Software Testing API",
        "version": "0.1.0",
    }
