from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.api.endpoints import api as endpoints
from app.logging import setup_logging
from app.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Set up the application lifespan management."""
    setup_logging()
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(
    version="1.0.0",
    title="Auto RIA Cars Scraper API",
    description="API for scraping auto.ria.com listings and car details.",
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)

app.include_router(endpoints, tags=["Scraper"], prefix="/api/v1")
