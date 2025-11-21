# tests/test_stats_api.py

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Mint, SwapEvent
from src.schemas import MintState
from src.database import engine


@pytest.mark.asyncio
async def test_read_stats_empty(async_client):
    response = await async_client.get("/stats/")
    assert response.status_code == 200
    assert response.json() == {
        "total_balance": 0,
        "total_swaps": 0,
        "total_swaps_24h": 0,
        "total_amount_swapped": 0,
        "total_amount_swapped_24h": 0,
        "average_swap_time": 0,
        "average_swap_time_24h": 0,
    }


@pytest.mark.asyncio
async def test_read_stats_with_data(async_client):
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
            balance=200,
            sum_donations=200,
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

        # Create swaps
        swap1 = SwapEvent(
            from_id=mint1.id,
            to_id=mint2.id,
            from_url=mint1.url,
            to_url=mint2.url,
            amount=50,
            fee=1,
            created_at=datetime.utcnow(),
            time_taken=100,
            state=MintState.OK.value,
        )
        swap2 = SwapEvent(
            from_id=mint2.id,
            to_id=mint1.id,
            from_url=mint2.url,
            to_url=mint1.url,
            amount=30,
            fee=2,
            created_at=datetime.utcnow() - timedelta(hours=12),  # Within 24h
            time_taken=150,
            state=MintState.OK.value,
        )
        session.add(swap1)
        session.add(swap2)
        await session.commit()

    response = await async_client.get("/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_balance"] == 300  # 100 + 200
    assert data["total_swaps"] == 2
    assert data["total_swaps_24h"] == 2
    assert data["total_amount_swapped"] == 80  # 50 + 30
    assert data["total_amount_swapped_24h"] == 80
    assert data["average_swap_time"] == 125.0  # (100 + 150) / 2
    assert data["average_swap_time_24h"] == 125.0


@pytest.mark.asyncio
async def test_read_stats_old_swaps(async_client):
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
            balance=200,
            sum_donations=200,
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

        # Create swap older than 24h
        swap = SwapEvent(
            from_id=mint1.id,
            to_id=mint2.id,
            from_url=mint1.url,
            to_url=mint2.url,
            amount=50,
            fee=1,
            created_at=datetime.utcnow() - timedelta(hours=25),  # Older than 24h
            time_taken=100,
            state=MintState.OK.value,
        )
        session.add(swap)
        await session.commit()

    response = await async_client.get("/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_swaps"] == 1
    assert data["total_swaps_24h"] == 0
    assert data["total_amount_swapped"] == 50
    assert data["total_amount_swapped_24h"] == 0
