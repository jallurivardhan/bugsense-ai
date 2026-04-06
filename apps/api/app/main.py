from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import Base, async_session, engine
from app.db.models import BenchmarkTestCaseModel
from app.routes import benchmarks, bug_analysis, dashboard, documents, health, test_generation
from app.routes.insights import router as insights_router
from app.services.custom_examples_service import custom_examples_service

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        f"{settings.APP_TAGLINE} - bug analysis, test generation, "
        "and QA knowledge management"
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(bug_analysis.router, prefix="/api/v1/bug-analysis", tags=["Bug Analysis"])
app.include_router(test_generation.router, prefix="/api/v1/test-generation", tags=["Test Generation"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(benchmarks.router, prefix="/api/v1/benchmarks", tags=["Benchmarks"])
app.include_router(insights_router, prefix="/api/v1")


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        await custom_examples_service.load_from_db(session)


@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} API", "tagline": settings.APP_TAGLINE, "version": "0.1.0"}
