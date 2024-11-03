# src/main.py

from datetime import datetime, timedelta
import json
import os
from typing import List

from cashu.wallet.helpers import deserialize_token_from_string
from cashu.core.base import Token
from fastapi import Depends, FastAPI, HTTPException, status
from loguru import logger
from sqlalchemy import select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas, auditor
from .database import engine, get_db
from alembic import command
from alembic.config import Config
from .logging import configure_logger

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (not recommended for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

auditor = auditor.Auditor()


@app.on_event("startup")
async def startup():
    """
    Startup event to create database tables and load all Mints into memory.
    """
    configure_logger()

    os.chdir("src")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    os.chdir("..")

    async with AsyncSession(bind=engine) as session:
        result = await session.execute(select(models.Mint))
        mints = result.scalars().all()
        app.state.mints_cache = {mint.id: mint for mint in mints}
    print(f"Loaded {len(app.state.mints_cache)} mints into the in-memory cache.")

    await auditor.init_wallet()


async def receive_token(token: str, db: AsyncSession) -> models.Mint:
    try:
        received = await auditor.receive_token(token)
        logger.success(f"Received {received} units.")
    except Exception as e:
        logger.error(f"Error while receiving token: {e}")
        raise e
    token_obj: Token = deserialize_token_from_string(token)
    mint_url = token_obj.mint.rstrip("/")
    # load mint form db with token_obj.mint (URL)
    result = await db.execute(select(models.Mint).where((models.Mint.url == mint_url)))
    mint = result.scalars().first()
    if mint:
        mint.balance = auditor.wallet.available_balance
        mint.sum_donations += received
        mint.next_update = datetime.utcnow() + timedelta(minutes=1)
        mint.info = json.dumps(auditor.wallet.mint_info.dict())
    else:
        mint = models.Mint(
            name=auditor.wallet.mint_info.name,
            url=mint_url,
            info=json.dumps(auditor.wallet.mint_info.dict()),
            balance=auditor.wallet.available_balance,
            sum_donations=auditor.wallet.available_balance,
            updated_at=datetime.utcnow(),
            next_update=datetime.utcnow() + timedelta(minutes=1),
            state=schemas.MintState.UNKNOWN.value,
            n_errors=0,
            n_mints=0,
            n_melts=0,
        )
        db.add(mint)
    await db.commit()
    await db.refresh(mint)
    await db.expunge(mint)
    return mint


@app.post(
    "/mints/", response_model=schemas.MintRead, status_code=status.HTTP_201_CREATED
)
async def create_mint(
    charge_request: schemas.ChargeRequest, db: AsyncSession = Depends(get_db)
):
    try:
        new_mint = await receive_token(charge_request.token, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting token: {e}.",
        )

    return new_mint


@app.get("/mints/", response_model=List[schemas.MintRead])
async def read_mints(
    skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)
):
    """
    Endpoint to retrieve a list of all Mints.
    Supports pagination with `skip` and `limit` query parameters.
    """
    query = select(models.Mint).offset(skip)
    if limit:
        query = query.limit(limit)
    result = await db.execute(query)
    mints = result.scalars().all()
    return mints


@app.get("/mints/{mint_id}", response_model=schemas.MintRead)
async def read_mint(mint_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to retrieve a single Mint by its ID.
    """
    result = await db.execute(select(models.Mint).where(models.Mint.id == mint_id))
    mint = result.scalars().first()
    if mint is None:
        raise HTTPException(status_code=404, detail="Mint not found")
    return mint


@app.get("/swaps/", response_model=List[schemas.SwapEventRead])
async def read_swaps(
    skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)
):
    """
    Endpoint to retrieve a list of all Swaps.
    Supports pagination with `skip` and `limit` query parameters.
    """
    result = await db.execute(
        select(models.SwapEvent)
        .order_by(desc(models.SwapEvent.created_at))
        .offset(skip)
        .limit(limit)
    )
    swaps = result.scalars().all()
    return swaps


@app.get("/graph/", response_model=schemas.MintGraph)
async def read_mint_graph(db: AsyncSession = Depends(get_db)):
    """
    Endpoint to retrieve a graph of all Mints and Swaps.
    """
    result = await db.execute(select(models.Mint))
    mints = result.scalars().all()
    mints = [schemas.MintRead.from_orm(mint) for mint in mints]
    for mint in mints:
        mint.info = ""
    result = await db.execute(
        select(models.SwapEvent).order_by(asc(models.SwapEvent.created_at))
    )
    swaps = result.scalars().all()
    # reduce all swaps to edges with unique from_id, to_id pairs and aggregated total_amount, total_fee, and count
    edges = {}
    for swap in swaps:
        key = (swap.from_id, swap.to_id)
        if key in edges:
            edges[key]["count"] += 1
            edges[key]["total_amount"] += swap.amount
            edges[key]["total_fee"] += swap.fee
            edges[key]["last_swap"] = max(edges[key]["last_swap"], swap.created_at)
            edges[key]["state"] = schemas.MintState(swap.state)
        else:
            edges[key] = {
                "from_id": swap.from_id,
                "to_id": swap.to_id,
                "count": 1,
                "total_amount": swap.amount,
                "total_fee": swap.fee,
                "last_swap": swap.created_at,
                "state": schemas.MintState(swap.state),
            }
    edges_list = list(edges.values())
    return schemas.MintGraph(nodes=mints, edges=edges_list)
