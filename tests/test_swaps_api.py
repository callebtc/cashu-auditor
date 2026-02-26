# tests/test_swaps_api.py

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Mint, SwapEvent
from src.schemas import MintState
from src.database import engine


@pytest.mark.asyncio
async def test_read_swaps_empty(async_client):
    response = await async_client.get("/swaps/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_read_swaps_pagination(async_client):
    # Create test mints
    async with AsyncSession(engine) as session:
        mint1 = Mint(
            url="https://mint1.example.com",
            name="Mint 1",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        mint2 = Mint(
            url="https://mint2.example.com",
            name="Mint 2",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add(mint1)
        session.add(mint2)
        await session.commit()
        await session.refresh(mint1)
        await session.refresh(mint2)

        # Create test swaps
        for i in range(5):
            swap = SwapEvent(
                from_id=mint1.id,
                to_id=mint2.id,
                from_url=mint1.url,
                to_url=mint2.url,
                amount=10 + i,
                fee=1,
                created_at=datetime.utcnow(),
                time_taken=100,
                state=MintState.OK.value,
            )
            session.add(swap)
        await session.commit()

    # Test pagination
    response = await async_client.get("/swaps/?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Should be ordered by created_at descending (newest first)
    assert data[0]["amount"] >= data[1]["amount"]

    # Test skip
    response = await async_client.get("/swaps/?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_read_swaps_mint_not_found(async_client):
    response = await async_client.get("/swaps/mint/999")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_read_swaps_mint_received(async_client):
    # Create test mints
    async with AsyncSession(engine) as session:
        mint1 = Mint(
            url="https://mint1.example.com",
            name="Mint 1",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        mint2 = Mint(
            url="https://mint2.example.com",
            name="Mint 2",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add(mint1)
        session.add(mint2)
        await session.commit()
        await session.refresh(mint1)
        await session.refresh(mint2)
        mint1_id = mint1.id
        mint2_id = mint2.id

        # Create swap where mint2 is the destination
        swap = SwapEvent(
            from_id=mint1_id,
            to_id=mint2_id,
            from_url=mint1.url,
            to_url=mint2.url,
            amount=50,
            fee=1,
            created_at=datetime.utcnow(),
            time_taken=100,
            state=MintState.OK.value,
        )
        session.add(swap)
        await session.commit()

    # Test received=True (mint2 is destination)
    response = await async_client.get(f"/swaps/mint/{mint2_id}?received=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["to_id"] == mint2_id
    assert data[0]["from_id"] == mint1_id


@pytest.mark.asyncio
async def test_read_swaps_mint_sent(async_client):
    # Create test mints
    async with AsyncSession(engine) as session:
        mint1 = Mint(
            url="https://mint1.example.com",
            name="Mint 1",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        mint2 = Mint(
            url="https://mint2.example.com",
            name="Mint 2",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add(mint1)
        session.add(mint2)
        await session.commit()
        await session.refresh(mint1)
        await session.refresh(mint2)
        mint1_id = mint1.id
        mint2_id = mint2.id

        # Create swap where mint1 is the source
        swap = SwapEvent(
            from_id=mint1_id,
            to_id=mint2_id,
            from_url=mint1.url,
            to_url=mint2.url,
            amount=50,
            fee=1,
            created_at=datetime.utcnow(),
            time_taken=100,
            state=MintState.OK.value,
        )
        session.add(swap)
        await session.commit()

    # Test received=False (mint1 is source)
    response = await async_client.get(f"/swaps/mint/{mint1_id}?received=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["from_id"] == mint1_id
    assert data[0]["to_id"] == mint2_id


@pytest.mark.asyncio
async def test_read_swaps_mint_error_state(async_client):
    # Create test mints
    async with AsyncSession(engine) as session:
        mint1 = Mint(
            url="https://mint1.example.com",
            name="Mint 1",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        mint2 = Mint(
            url="https://mint2.example.com",
            name="Mint 2",
            balance=100,
            sum_donations=100,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add(mint1)
        session.add(mint2)
        await session.commit()
        await session.refresh(mint1)
        await session.refresh(mint2)

        # Create swap with error state
        swap = SwapEvent(
            from_id=mint1.id,
            to_id=mint2.id,
            from_url=mint1.url,
            to_url=mint2.url,
            amount=50,
            fee=0,
            created_at=datetime.utcnow(),
            time_taken=0,
            state=MintState.ERROR.value,
            error="Test error message",
        )
        session.add(swap)
        await session.commit()

    response = await async_client.get("/swaps/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["state"] == MintState.ERROR.value
    assert data[0]["error"] == "Test error message"
