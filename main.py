import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from .routes import api_router

# ---------------------------------------------------
# Configuration (environment variables)
# ---------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/spendsense")

# ---------------------------------------------------
# Async DB Engine & Session
# ---------------------------------------------------
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_="asyncio", expire_on_commit=False, autoflush=False, autocommit=False)

# ---------------------------------------------------
# FastAPI Application
# ---------------------------------------------------
app = FastAPI(
    title="SpendSense AI",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# -------------------- CORS --------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# Startup / Shutdown Events
# ---------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def on_shutdown() -> None:
    await engine.dispose()

# ---------------------------------------------------
# Dependency Injection for DB Session
# ---------------------------------------------------
async def get_db() -> "AsyncSession":
    async with AsyncSessionLocal() as session:
        yield session

# ---------------------------------------------------
# Include API router
# ---------------------------------------------------
app.include_router(api_router, prefix="/api/v1")

# ---------------------------------------------------
# Command for local dev (uvicorn)
# ---------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
