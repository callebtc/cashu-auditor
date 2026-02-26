# tests/test_graph_api.py

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Mint, SwapEvent
from src.schemas import MintState
from src.database import engine


@pytest.mark.asyncio
async def test_read_graph_empty(async_client):
    response = await async_client.get("/graph/")
    assert response.status_code == 200
    assert response.json() == {"nodes": [], "edges": []}


@pytest.mark.asyncio
async def test_read_graph_with_data(async_client):
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
        mint1_id = mint1.id
        mint2_id = mint2.id

        # Create multiple swaps between same mints (should be aggregated)
        swap1 = SwapEvent(
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
        swap2 = SwapEvent(
            from_id=mint1_id,
            to_id=mint2_id,
            from_url=mint1.url,
            to_url=mint2.url,
            amount=30,
            fee=2,
            created_at=datetime.utcnow(),
            time_taken=150,
            state=MintState.OK.value,
        )
        session.add(swap1)
        session.add(swap2)
        await session.commit()

    response = await async_client.get("/graph/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1

    # Check edge aggregation
    edge = data["edges"][0]
    assert edge["from_id"] == mint1_id
    assert edge["to_id"] == mint2_id
    assert edge["count"] == 2
    assert edge["total_amount"] == 80  # 50 + 30
    assert edge["total_fee"] == 3  # 1 + 2
    assert edge["state"] == MintState.OK.value


@pytest.mark.asyncio
async def test_read_graph_multiple_edges(async_client):
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
        mint3 = Mint(
            url="https://mint3.example.com",
            name="Mint 3",
            balance=300,
            sum_donations=300,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add(mint1)
        session.add(mint2)
        session.add(mint3)
        await session.commit()
        await session.refresh(mint1)
        await session.refresh(mint2)
        await session.refresh(mint3)

        # Create swaps between different mints
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
            to_id=mint3.id,
            from_url=mint2.url,
            to_url=mint3.url,
            amount=30,
            fee=2,
            created_at=datetime.utcnow(),
            time_taken=150,
            state=MintState.OK.value,
        )
        session.add(swap1)
        session.add(swap2)
        await session.commit()

    response = await async_client.get("/graph/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2
