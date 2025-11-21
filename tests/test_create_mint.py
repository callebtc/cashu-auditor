import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import auditor
from src.models import Mint
from src.schemas import MintState
from src.database import engine


class FakeAmount:
    def __init__(self, amount: int):
        self.amount = amount

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return self.amount == other
        if isinstance(other, FakeAmount):
            return self.amount == other.amount
        return NotImplemented

    def __str__(self):
        return str(self.amount)

    __repr__ = __str__


async def create_mint_record(**overrides) -> Mint:
    defaults = dict(
        url="https://mint.example.com",
        name="Stored Mint",
        info="{}",
        balance=100,
        sum_donations=100,
        updated_at=datetime.utcnow(),
        next_update=datetime.utcnow(),
        state=MintState.UNKNOWN.value,
        n_errors=0,
        n_mints=0,
        n_melts=0,
    )
    defaults.update(overrides)
    async with AsyncSession(engine) as session:
        mint = Mint(**defaults)
        session.add(mint)
        await session.commit()
        await session.refresh(mint)
        return mint


def setup_wallet(monkeypatch, balance: int = 400, name: str = "Mock Mint"):
    class MintInfo:
        def __init__(self, mint_name: str):
            self.name = mint_name

        def dict(self):
            return {"name": self.name}

    wallet = SimpleNamespace(
        available_balance=SimpleNamespace(amount=balance),
        mint_info=MintInfo(name),
    )
    monkeypatch.setattr(auditor, "wallet", wallet, raising=False)
    return wallet


def stub_token(monkeypatch, mint_url: str):
    token_obj = SimpleNamespace(mint=mint_url)
    monkeypatch.setattr(
        "src.main.deserialize_token_from_string",
        lambda _: token_obj,
    )


@pytest.mark.asyncio
async def test_create_mint_creates_new_record(async_client, monkeypatch):
    setup_wallet(monkeypatch, balance=450, name="Fresh Mint")
    receive_mock = AsyncMock(return_value=FakeAmount(75))
    monkeypatch.setattr(auditor, "receive_token", receive_mock)
    stub_token(monkeypatch, "https://new-mint.example.com/")

    response = await async_client.post("/mints/", json={"token": "stub-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://new-mint.example.com"
    assert data["name"] == "Fresh Mint"
    assert data["balance"] == 450
    assert data["sum_donations"] == 450
    assert data["state"] == MintState.UNKNOWN.value
    receive_mock.assert_awaited()

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Mint).where(Mint.url == "https://new-mint.example.com")
        )
        mint = result.scalars().first()
        assert mint is not None
        assert mint.balance == 450
        assert mint.sum_donations == 450
        assert json.loads(mint.info)["name"] == "Fresh Mint"


@pytest.mark.asyncio
async def test_create_mint_updates_existing_record(async_client, monkeypatch):
    existing = await create_mint_record(
        url="https://existing.example.com",
        name="Existing Mint",
        info='{"name": "Existing Mint"}',
        balance=120,
        sum_donations=200,
        state=MintState.OK.value,
    )

    setup_wallet(monkeypatch, balance=320, name="Updated Mint")
    receive_mock = AsyncMock(return_value=FakeAmount(25))
    monkeypatch.setattr(auditor, "receive_token", receive_mock)
    stub_token(monkeypatch, "https://existing.example.com/")

    response = await async_client.post("/mints/", json={"token": "stub-token"})
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == existing.id
    assert data["balance"] == 320
    assert data["sum_donations"] == 225
    assert data["name"] == "Existing Mint"

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Mint).where(Mint.id == existing.id)
        )
        mint = result.scalars().first()
        assert mint.balance == 320
        assert mint.sum_donations == 225
        assert json.loads(mint.info)["name"] == "Updated Mint"


@pytest.mark.asyncio
async def test_create_mint_rejects_zero_amount(async_client, monkeypatch):
    setup_wallet(monkeypatch)
    receive_mock = AsyncMock(return_value=FakeAmount(0))
    monkeypatch.setattr(auditor, "receive_token", receive_mock)

    response = await async_client.post("/mints/", json={"token": "stub-token"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Received 0."
    receive_mock.assert_awaited()


@pytest.mark.asyncio
async def test_create_mint(async_client: AsyncClient):
    # This is a sample token, replace with a valid one for your tests
    token = "cashuAeyJ0b2tlbiI6IFt7InByb29mcyI6IFt7ImlkIjogIjAwIiwgImFtb3VudCI6IDEsICJzZWNyZXQiOiAiYjRmMzk5Y2Q3YTRlYTIxOWJhMGUzMWRlZDAzYjM3Y2YifSwgeyJpZCI6ICIwMCIsICJhbW91bnQiOiAyLCAic2VjcmV0IjogIjM1ZDY0Y2U3Yzk5MGI4YTYzYzY0YjM5Mjc5Yzc0MjZlIn1dLCAibWludCI6ICJodHRwOi8vbG9jYWxob3N0OjgwMDAifV19"

    response = await async_client.post("/mints/", json={"token": token})

    # Since we don't have a valid mint, we expect a 400
    assert response.status_code == 400
