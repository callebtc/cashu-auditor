# tests/test_donations_api.py

import pytest


@pytest.mark.asyncio
async def test_get_payment_request(async_client):
    response = await async_client.get("/pr")
    assert response.status_code == 200
    assert "pr" in response.json()
