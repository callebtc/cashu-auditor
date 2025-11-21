import base64
from unittest.mock import AsyncMock, MagicMock, patch

import cbor2
import pytest

from src.main import BASE_URL


def decode_payment_request(pr_value: str):
    assert pr_value.startswith("creqA")
    payload = pr_value[5:]
    padding = "=" * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload + padding)
    return cbor2.loads(decoded)


@pytest.mark.asyncio
async def test_get_payment_request(async_client):
    response = await async_client.get("/pr")
    assert response.status_code == 200
    payload = response.json()
    assert "pr" in payload
    decoded = decode_payment_request(payload["pr"])
    assert decoded["u"] == "sat"
    assert decoded["d"] == "Cashu mint auditor donation"
    assert decoded["t"][0]["a"] == f"{BASE_URL}/donate"


@pytest.mark.asyncio
async def test_get_payment_request_scoped_to_mint(async_client):
    mint_url = "https://mint.scope.test"
    response = await async_client.get("/pr", params={"url": mint_url})
    assert response.status_code == 200
    decoded = decode_payment_request(response.json()["pr"])
    assert decoded["m"] == [mint_url]


def sample_payload():
    return {
        "mint": "https://mint.example.com",
        "unit": "sat",
        "memo": "donation",
        "proofs": [
            {"id": "00" * 16, "amount": 5, "secret": "sec", "C": "commitment"}
        ],
    }


@pytest.mark.asyncio
async def test_receive_donation_success(async_client):
    token_mock = MagicMock()
    token_mock.serialize.return_value = "serialized-token"
    receive_mock = AsyncMock()

    with patch(
        "src.main.PaymentPayload.to_tokenv4", return_value=token_mock
    ) as mocked_to_tokenv4, patch(
        "src.main.receive_token", receive_mock
    ):
        response = await async_client.post("/donate", json=sample_payload())

    assert response.status_code == 200
    mocked_to_tokenv4.assert_called_once()
    assert receive_mock.await_count == 1
    args, _ = receive_mock.await_args
    assert args[0] == "serialized-token"
    assert args[1].__class__.__name__ == "AsyncSession"


@pytest.mark.asyncio
async def test_receive_donation_invalid_payload(async_client):
    receive_mock = AsyncMock()

    with patch(
        "src.main.PaymentPayload.to_tokenv4",
        side_effect=ValueError("boom"),
    ), patch("src.main.receive_token", receive_mock):
        response = await async_client.post("/donate", json=sample_payload())

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid token format"
    receive_mock.assert_not_awaited()
