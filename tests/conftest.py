# tests/conftest.py

import os
import pytest_asyncio
from httpx import AsyncClient

from src.main import app
from src.database import engine
from src.models import Base

os.environ["TESTING"] = "True"


@pytest_asyncio.fixture(scope="function")
async def async_client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
