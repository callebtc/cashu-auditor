import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_mint(async_client: AsyncClient):
    # This is a sample token, replace with a valid one for your tests
    token = "cashuAeyJ0b2tlbiI6IFt7InByb29mcyI6IFt7ImlkIjogIjAwIiwgImFtb3VudCI6IDEsICJzZWNyZXQiOiAiYjRmMzk5Y2Q3YTRlYTIxOWJhMGUzMWRlZDAzYjM3Y2YifSwgeyJpZCI6ICIwMCIsICJhbW91bnQiOiAyLCAic2VjcmV0IjogIjM1ZDY0Y2U3Yzk5MGI4YTYzYzY0YjM5Mjc5Yzc0MjZlIn1dLCAibWludCI6ICJodHRwOi8vbG9jYWxob3N0OjgwMDAifV19"

    response = await async_client.post("/mints/", json={"token": token})

    # Since we don't have a valid mint, we expect a 400
    assert response.status_code == 400
