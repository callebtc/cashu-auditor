# tests/test_auditor.py

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from datetime import datetime
from types import SimpleNamespace

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


@pytest.mark.asyncio
async def test_choose_to_mint_filters_candidates(db_setup, monkeypatch):
    auditor = Auditor()

    async with AsyncSession(engine) as session:
        eligible_ok = Mint(
            url="https://mint-ok.example.com",
            name="Mint OK",
            balance=120,
            sum_donations=200,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.OK.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        eligible_low = Mint(
            url="https://mint-low.example.com",
            name="Mint Low",
            balance=50,
            sum_donations=120,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        ineligible_state = Mint(
            url="https://mint-bad.example.com",
            name="Mint Bad",
            balance=150,
            sum_donations=200,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.ERROR.value,
            n_errors=1,
            n_mints=0,
            n_melts=0,
        )
        ineligible_balance = Mint(
            url="https://mint-rich.example.com",
            name="Mint Rich",
            balance=300,
            sum_donations=250,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.OK.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add_all(
            [eligible_ok, eligible_low, ineligible_state, ineligible_balance]
        )
        await session.commit()

    captured = {}

    def fake_choice(seq):
        captured["candidates"] = [mint.url for mint in seq]
        return seq[0]

    monkeypatch.setattr("src.auditor.random.choice", fake_choice)
    chosen = await auditor.choose_to_mint()
    assert chosen.url in ("https://mint-ok.example.com", "https://mint-low.example.com")
    assert set(captured["candidates"]) == {
        "https://mint-ok.example.com",
        "https://mint-low.example.com",
    }


@pytest.mark.asyncio
async def test_choose_to_mint_no_candidates(db_setup):
    auditor = Auditor()
    async with AsyncSession(engine) as session:
        mint = Mint(
            url="https://mint-empty.example.com",
            name="Mint Empty",
            balance=200,
            sum_donations=150,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.ERROR.value,
            n_errors=2,
            n_mints=0,
            n_melts=0,
        )
        session.add(mint)
        await session.commit()

    with pytest.raises(ValueError):
        await auditor.choose_to_mint()


@pytest.mark.asyncio
async def test_choose_from_mint_and_amount_selects_valid_source(db_setup, monkeypatch):
    auditor = Auditor()
    async with AsyncSession(engine) as session:
        to_mint = Mint(
            url="https://mint-target.example.com",
            name="Mint Target",
            balance=40,
            sum_donations=200,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.OK.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        rich_mint = Mint(
            url="https://mint-rich-source.example.com",
            name="Mint Rich Source",
            balance=500,
            sum_donations=400,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.OK.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        poor_mint = Mint(
            url="https://mint-poor-source.example.com",
            name="Mint Poor Source",
            balance=70,
            sum_donations=150,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.OK.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add_all([to_mint, rich_mint, poor_mint])
        await session.commit()
        await session.refresh(to_mint)
        await session.refresh(rich_mint)

    monkeypatch.setattr("src.auditor.random.randint", lambda *_: 90)
    monkeypatch.setattr("src.auditor.random.choice", lambda seq: seq[0])

    from_mint, amount = await auditor.choose_from_mint_and_amount(to_mint)
    assert from_mint.id == rich_mint.id
    assert amount == 90


@pytest.mark.asyncio
async def test_choose_from_mint_and_amount_no_sources(db_setup, monkeypatch):
    auditor = Auditor()
    async with AsyncSession(engine) as session:
        to_mint = Mint(
            url="https://mint-target.example.com",
            name="Mint Target",
            balance=40,
            sum_donations=200,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.OK.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        weak_mint = Mint(
            url="https://mint-weak.example.com",
            name="Mint Weak",
            balance=40,
            sum_donations=150,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow(),
            state=MintState.OK.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        session.add_all([to_mint, weak_mint])
        await session.commit()
        await session.refresh(to_mint)

    monkeypatch.setattr("src.auditor.random.randint", lambda *_: 40)

    with pytest.raises(ValueError):
        await auditor.choose_from_mint_and_amount(to_mint)


@pytest.mark.asyncio
async def test_recover_errors_bumps_secret_derivation(monkeypatch):
    auditor = Auditor()
    wallet = SimpleNamespace(db="db-path", keyset_id="keyset")
    bump_mock = AsyncMock()
    monkeypatch.setattr("src.auditor.bump_secret_derivation", bump_mock)

    handled = await auditor.recover_errors(wallet, Exception("secret already used"))
    assert handled is True
    bump_mock.assert_awaited_once_with(wallet.db, wallet.keyset_id, by=10)


@pytest.mark.asyncio
async def test_recover_errors_handles_spent_proofs(monkeypatch):
    auditor = Auditor()
    wallet = SimpleNamespace(proofs=["p1", "p2"])
    wallet.invalidate = AsyncMock(return_value=["p2"])

    handled = await auditor.recover_errors(wallet, Exception("already spent token"))
    assert handled is True
    wallet.invalidate.assert_awaited_once()


@pytest.mark.asyncio
async def test_recover_errors_unhandled():
    auditor = Auditor()
    wallet = SimpleNamespace(proofs=[])
    handled = await auditor.recover_errors(wallet, Exception("other error"))
    assert handled is False
