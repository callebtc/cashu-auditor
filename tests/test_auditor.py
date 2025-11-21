# tests/test_auditor.py

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.auditor import Auditor
from src.models import Mint, Base
from src.schemas import MintState
from src.database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


@pytest_asyncio.fixture(scope="function")
async def db_setup():
    """Create database tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_bump_mint_errors(db_setup):
    """Test bumping error count for a mint."""
    auditor = Auditor()

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
        initial_errors = mint.n_errors

    await auditor.bump_mint_errors(mint_id)

    async with AsyncSession(engine) as session:
        result = await session.execute(select(Mint).where(Mint.id == mint_id))
        updated_mint = result.scalars().first()
        assert updated_mint.n_errors == initial_errors + 1
        assert updated_mint.state == MintState.ERROR.value


@pytest.mark.asyncio
async def test_bump_mint_n_mints(db_setup):
    """Test bumping mint count for a mint."""
    auditor = Auditor()

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
        initial_mints = mint.n_mints

    await auditor.bump_mint_n_mints(mint)

    async with AsyncSession(engine) as session:
        result = await session.execute(select(Mint).where(Mint.id == mint.id))
        updated_mint = result.scalars().first()
        assert updated_mint.n_mints == initial_mints + 1


@pytest.mark.asyncio
async def test_bump_mint_n_melts(db_setup):
    """Test bumping melt count for a mint."""
    auditor = Auditor()

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
        initial_melts = mint.n_melts

    await auditor.bump_mint_n_melts(mint)

    async with AsyncSession(engine) as session:
        result = await session.execute(select(Mint).where(Mint.id == mint.id))
        updated_mint = result.scalars().first()
        assert updated_mint.n_melts == initial_melts + 1
        assert updated_mint.state == MintState.OK.value


@pytest.mark.asyncio
async def test_get_mint(db_setup):
    """Test getting a mint by URL."""
    auditor = Auditor()

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

    result = await auditor.get_mint("https://testmint.example.com")
    assert result is not None
    assert result.url == "https://testmint.example.com"
    assert result.name == "Test Mint"


@pytest.mark.asyncio
async def test_get_mint_not_found(db_setup):
    """Test getting a mint that doesn't exist."""
    auditor = Auditor()

    result = await auditor.get_mint("https://nonexistent.example.com")
    assert result is None


@pytest.mark.asyncio
async def test_store_swap_event(db_setup):
    """Test storing a swap event."""
    auditor = Auditor()

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

    await auditor.store_swap_event(
        from_mint=mint1,
        to_mint=mint2,
        amount=50,
        fee=1,
        time_taken=100,
        state=MintState.OK.value,
    )

    async with AsyncSession(engine) as session:
        from src.models import SwapEvent

        result = await session.execute(
            select(SwapEvent).where(SwapEvent.from_id == mint1.id)
        )
        swap = result.scalars().first()
        assert swap is not None
        assert swap.from_id == mint1.id
        assert swap.to_id == mint2.id
        assert swap.amount == 50
        assert swap.fee == 1
        assert swap.time_taken == 100
        assert swap.state == MintState.OK.value


@pytest.mark.asyncio
async def test_store_swap_event_with_error(db_setup):
    """Test storing a swap event with an error."""
    auditor = Auditor()

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

    await auditor.store_swap_event(
        from_mint=mint1,
        to_mint=mint2,
        amount=50,
        fee=0,
        time_taken=0,
        state=MintState.ERROR.value,
        error="Test error message",
    )

    async with AsyncSession(engine) as session:
        from src.models import SwapEvent

        result = await session.execute(
            select(SwapEvent).where(SwapEvent.from_id == mint1.id)
        )
        swap = result.scalars().first()
        assert swap is not None
        assert swap.state == MintState.ERROR.value
        assert swap.error == "Test error message"
