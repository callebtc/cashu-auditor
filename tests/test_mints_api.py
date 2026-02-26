# tests/test_mints_api.py

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Mint
from src.schemas import MintState
from src.database import engine


@pytest.mark.asyncio
async def test_read_mints_empty(async_client):
    response = await async_client.get("/mints/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_read_mints_pagination(async_client):
    # Create some test mints
    async with AsyncSession(engine) as session:
        for i in range(5):
            mint = Mint(
                url=f"https://mint{i}.example.com",
                name=f"Test Mint {i}",
                balance=100 + i,
                sum_donations=100 + i,
                updated_at=datetime.utcnow(),
                next_update=datetime.utcnow(),
                state=MintState.UNKNOWN.value,
                n_errors=0,
                n_mints=0,
                n_melts=0,
            )
            session.add(mint)
        await session.commit()

    # Test pagination with skip and limit
    response = await async_client.get("/mints/?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_read_mints_includes_location(async_client):
    """Ensure API returns latitude and longitude when stored."""
    async with AsyncSession(engine) as session:
        mint = Mint(
            url="https://located.example.com",
            name="Located Mint",
            balance=200,
            sum_donations=200,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.OK.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
            latitude=12.34,
            longitude=56.78,
        )
        session.add(mint)
        await session.commit()

    response = await async_client.get("/mints/")
    assert response.status_code == 200
    data = response.json()
    located = next(
        item for item in data if item["url"] == "https://located.example.com"
    )
    assert located["latitude"] == 12.34
    assert located["longitude"] == 56.78

    # Test limit
    response = await async_client.get("/mints/?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_read_mint_by_id_not_found(async_client):
    response = await async_client.get("/mints/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_read_mint_by_id_success(async_client):
    # Create a test mint
    async with AsyncSession(engine) as session:
        mint = Mint(
            url="https://testmint.example.com",
            name="Test Mint",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add(mint)
        await session.commit()
        await session.refresh(mint)
        mint_id = mint.id

    response = await async_client.get(f"/mints/{mint_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == mint_id
    assert data["url"] == "https://testmint.example.com"
    assert data["name"] == "Test Mint"


@pytest.mark.asyncio
async def test_get_mint_by_url_not_found(async_client):
    response = await async_client.get("/mints/url?url=https://nonexistent.example.com")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_mint_by_url_success(async_client):
    # Create a test mint
    async with AsyncSession(engine) as session:
        mint = Mint(
            url="https://testmint.example.com",
            name="Test Mint",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add(mint)
        await session.commit()

    response = await async_client.get("/mints/url?url=https://testmint.example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://testmint.example.com"
    assert data["name"] == "Test Mint"


@pytest.mark.asyncio
async def test_get_mint_by_url_with_trailing_slash(async_client):
    # Create a test mint
    async with AsyncSession(engine) as session:
        mint = Mint(
            url="https://testmint.example.com",
            name="Test Mint",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add(mint)
        await session.commit()

    # Test with trailing slash - the API doesn't strip trailing slashes from query params
    # So this should return 404 since the URL doesn't match exactly
    response = await async_client.get("/mints/url?url=https://testmint.example.com/")
    assert response.status_code == 404
