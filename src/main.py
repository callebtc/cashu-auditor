# src/main.py

from datetime import datetime, timedelta
import json
import os
from typing import List, Optional

from cashu.wallet.helpers import deserialize_token_from_string
from cashu.core.base import Token
from fastapi import Depends, FastAPI, HTTPException, status, Query, Path
from loguru import logger
from sqlalchemy import select, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas, auditor
from .database import engine, get_db
from alembic import command
from alembic.config import Config
from .logging import configure_logger
from .payment_request import PaymentRequest, PaymentPayload
from .mint_location_resolver import MintLocationResolver

# Base URL for the HTTP endpoint in payment requests
BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise ValueError(
        "BASE_URL is not set, please set it in your environment or in the .env file"
    )

app = FastAPI(
    title="Cashu Mint Auditor API",
    description="API for managing and monitoring Cashu mints, tracking swaps, and handling donations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (not recommended for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

auditor = auditor.Auditor()
location_resolver = MintLocationResolver()


async def resolve_mint_location(mint: models.Mint, db: AsyncSession):
    """Resolve and update the location of a mint."""
    # Only resolve if resolver is ready (database loaded)
    if not location_resolver.ip_ranges:
        return
    try:
        coords = location_resolver.resolve_mint_location(mint.url)
        if coords:
            latitude, longitude = coords
            mint.latitude = latitude
            mint.longitude = longitude
            logger.info(f"Resolved location for {mint.url}: ({latitude}, {longitude})")
        else:
            logger.warning(f"Could not resolve location for {mint.url}")
    except Exception as e:
        logger.error(f"Error resolving location for {mint.url}: {e}")


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

    # Initialize location resolver and update database if needed
    resolver_ready = False
    try:
        await location_resolver.ensure_database_updated()
        resolver_ready = True
        logger.info("IP location database ready")
    except Exception as e:
        logger.error(f"Error initializing location resolver: {e}")

    async with AsyncSession(bind=engine) as session:
        result = await session.execute(select(models.Mint))
        mints = result.scalars().all()
        app.state.mints_cache = {mint.id: mint for mint in mints}
    print(f"Loaded {len(app.state.mints_cache)} mints into the in-memory cache.")

    # Resolve locations for all existing mints (only if resolver is ready)
    if resolver_ready:
        async with AsyncSession(bind=engine) as session:
            result = await session.execute(select(models.Mint))
            mints = result.scalars().all()
            resolved_count = 0
            for mint in mints:
                # Only resolve if location is not already set
                if mint.latitude is None or mint.longitude is None:
                    await resolve_mint_location(mint, session)
                    if mint.latitude is not None and mint.longitude is not None:
                        resolved_count += 1
            await session.commit()
            logger.info(f"Resolved locations for {resolved_count} mints")

    await auditor.init_wallet()


async def receive_token(token: str, db: AsyncSession) -> models.Mint:
    try:
        received = await auditor.receive_token(token)
        logger.success(f"Received {received}.")
    except Exception as e:
        logger.error(f"Error receiving token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error receiving token: {e}",
        )
    if received == 0:
        logger.error(f"Received {received}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Received {received}.",
        )
    try:
        token_obj: Token = deserialize_token_from_string(token)
        mint_url = token_obj.mint.rstrip("/")
        result = await db.execute(
            select(models.Mint).where(models.Mint.url == mint_url)
        )
        mint = result.scalars().first()
        logger.info(f"Mint: {mint}")
        if mint:
            # Update Existing Mint
            mint.balance = auditor.wallet.available_balance.amount
            mint.sum_donations += received.amount
            mint.next_update = datetime.utcnow() + timedelta(minutes=1)
            mint.info = json.dumps(auditor.wallet.mint_info.dict())
            logger.info(f"Updated existing mint: {mint.url}")
            logger.info(f"Balance: {mint.balance}, Sum donations: {mint.sum_donations}")
            # Resolve location if not already set
            if mint.latitude is None or mint.longitude is None:
                await resolve_mint_location(mint, db)
        else:
            # Create New Mint
            mint = models.Mint(
                name=auditor.wallet.mint_info.name,
                url=mint_url,
                info=json.dumps(auditor.wallet.mint_info.dict()),
                balance=auditor.wallet.available_balance.amount,
                sum_donations=auditor.wallet.available_balance.amount,
                updated_at=datetime.utcnow(),
                next_update=datetime.utcnow() + timedelta(minutes=1),
                state=schemas.MintState.UNKNOWN.value,
                n_errors=0,
                n_mints=0,
                n_melts=0,
            )
            logger.info(f"Added new mint: {mint.url}")
            db.add(mint)
            # Resolve location for new mint
            await resolve_mint_location(mint, db)

        await db.commit()
        await db.refresh(mint)
        db.expunge(mint)

        return mint

    except Exception as e:
        logger.error(f"Error in receive_token: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post(
    "/mints/",
    response_model=schemas.MintRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new mint",
    description="Creates a new mint by receiving a Cashu token. The token is validated and processed, and the mint information is stored in the database.",
    responses={
        201: {"description": "Mint successfully created"},
        400: {"description": "Invalid token or received 0 units"},
        500: {"description": "Internal server error"},
    },
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


@app.get(
    "/mints/url",
    response_model=schemas.MintRead,
    summary="Get mint by URL",
    description="Retrieves a specific mint by its URL. Returns 404 if the mint is not found.",
    responses={
        200: {"description": "Mint found and returned"},
        404: {"description": "Mint not found"},
    },
)
async def get_mint(
    url: str = Query(..., description="The URL of the mint to retrieve"),
    db: AsyncSession = Depends(get_db),
):
    """Endpoint to retrieve a Mint by its URL."""
    result = await db.execute(select(models.Mint).where(models.Mint.url == url))
    mint = result.scalars().first()
    if mint is None:
        raise HTTPException(status_code=404, detail="Mint not found")
    return mint


@app.get(
    "/mints/",
    response_model=List[schemas.MintRead],
    summary="List all mints",
    description="Retrieves a paginated list of all mints in the system. Use skip and limit parameters for pagination.",
    responses={200: {"description": "List of mints retrieved successfully"}},
)
async def read_mints(
    params: schemas.PaginationParams = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Endpoint to retrieve a list of all Mints.
    Supports pagination with `skip` and `limit` query parameters.
    """
    query = select(models.Mint).offset(params.skip)
    query = query.limit(params.limit)
    result = await db.execute(query)
    mints = result.scalars().all()
    return mints


@app.get(
    "/mints/{mint_id}",
    response_model=schemas.MintRead,
    summary="Get mint by ID",
    description="Retrieves a specific mint by its ID. Returns 404 if the mint is not found.",
    responses={
        200: {"description": "Mint found and returned"},
        404: {"description": "Mint not found"},
    },
)
async def read_mint(
    mint_id: int = Path(..., description="The ID of the mint to retrieve"),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint to retrieve a single Mint by its ID.
    """
    result = await db.execute(select(models.Mint).where(models.Mint.id == mint_id))
    mint = result.scalars().first()
    if mint is None:
        raise HTTPException(status_code=404, detail="Mint not found")
    return mint


@app.get(
    "/swaps/",
    response_model=List[schemas.SwapEventRead],
    summary="List all swaps",
    description="Retrieves a paginated list of all swap events in the system, ordered by creation date (newest first).",
    responses={200: {"description": "List of swaps retrieved successfully"}},
)
async def read_swaps(
    params: schemas.PaginationParams = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Endpoint to retrieve a list of all Swaps.
    Supports pagination with `skip` and `limit` query parameters.
    """
    result = await db.execute(
        select(models.SwapEvent)
        .order_by(desc(models.SwapEvent.created_at))
        .offset(params.skip)
        .limit(params.limit)
    )
    swaps = result.scalars().all()
    return swaps


@app.get(
    "/swaps/mint/{mint_id}",
    response_model=List[schemas.SwapEventRead],
    summary="List swaps for a specific mint",
    description="Retrieves a paginated list of swap events for a specific mint. Can filter by whether the mint was the source or destination of the swap.",
    responses={200: {"description": "List of swaps retrieved successfully"}},
)
async def read_swaps_mint(
    mint_id: int = Path(..., description="The ID of the mint to filter swaps by"),
    params: schemas.PaginationParams = Depends(),
    received: Optional[bool] = Query(
        None,
        description="If True, shows swaps where the mint was the destination. If False, shows swaps where the mint was the source.",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint to retrieve a list of Swaps for a specific Mint.
    Supports pagination with `skip` and `limit` query parameters.
    """
    result = await db.execute(
        select(models.SwapEvent)
        .order_by(desc(models.SwapEvent.created_at))
        .offset(params.skip)
        .limit(params.limit)
        .where(
            models.SwapEvent.from_id == mint_id
            if not received
            else models.SwapEvent.to_id == mint_id
        )
    )
    swaps = result.scalars().all()
    return swaps


@app.get(
    "/graph/",
    response_model=schemas.MintGraph,
    summary="Get mint graph",
    description="Retrieves a graph representation of all mints and their relationships through swaps. Returns nodes (mints) and edges (swaps) with aggregated information.",
    responses={200: {"description": "Graph data retrieved successfully"}},
)
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


@app.get(
    "/stats/",
    response_model=schemas.MintStats,
    summary="Get service statistics",
    description="Retrieves comprehensive statistics about the service, including total balances, swap counts, amounts, and timing information for both all-time and last 24 hours.",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        500: {"description": "Internal server error"},
    },
)
async def get_service_stats(db: AsyncSession = Depends(get_db)):
    """Endpoint to retrieve service statistics."""
    try:
        # Total balance
        result = await db.execute(select(func.sum(models.Mint.balance)))
        total_balance = result.scalar() or 0

        # Total swaps
        result = await db.execute(select(func.count(models.SwapEvent.id)))
        total_swaps = result.scalar() or 0

        # Swaps in the last 24 hours
        last_24h = datetime.utcnow() - timedelta(hours=24)
        result = await db.execute(
            select(func.count(models.SwapEvent.id)).where(
                models.SwapEvent.created_at >= last_24h
            )
        )
        total_swaps_24h = result.scalar() or 0

        # Total amount swapped
        result = await db.execute(select(func.sum(models.SwapEvent.amount)))
        total_amount_swapped = result.scalar() or 0

        # Amount swapped in the last 24 hours
        result = await db.execute(
            select(func.sum(models.SwapEvent.amount)).where(
                models.SwapEvent.created_at >= last_24h
            )
        )
        total_amount_swapped_24h = result.scalar() or 0

        # Average swap time
        result = await db.execute(select(func.avg(models.SwapEvent.time_taken)))
        average_swap_time = result.scalar() or 0

        # Average swap time in the last 24 hours
        result = await db.execute(
            select(func.avg(models.SwapEvent.time_taken)).where(
                models.SwapEvent.created_at >= last_24h
            )
        )
        average_swap_time_24h = result.scalar() or 0

        return schemas.MintStats(
            total_balance=total_balance,
            total_swaps=total_swaps,
            total_swaps_24h=total_swaps_24h,
            total_amount_swapped=total_amount_swapped,
            total_amount_swapped_24h=total_amount_swapped_24h,
            average_swap_time=average_swap_time,
            average_swap_time_24h=average_swap_time_24h,
        )
    except Exception as e:
        logger.error(f"Error fetching service statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get(
    "/pr",
    response_model=schemas.PaymentRequestResponse,
    summary="Get payment request",
    description="Generates a Cashu payment request for donations. Optionally accepts a specific mint URL to restrict the payment to a particular mint.",
    responses={200: {"description": "Payment request generated successfully"}},
)
async def get_payment_request(
    url: Optional[str] = Query(
        None, description="Optional URL of a specific mint to restrict the payment to"
    )
):
    """
    Endpoint to get a Cashu payment request for donation.
    Returns a base64-encoded CBOR payment request as per NUT-18.
    """
    payment_request = PaymentRequest(
        unit="sat",
        description="Cashu mint auditor donation",
        http_endpoint=f"{BASE_URL}/donate",
    )
    if url:
        payment_request.mints = [url]
    return schemas.PaymentRequestResponse(pr=payment_request.serialize())


@app.post(
    "/donate",
    summary="Receive donation",
    description="Endpoint to receive a Cashu payment as per NUT-18. Processes the donation payment and updates the corresponding mint information.",
    responses={
        200: {"description": "Donation processed successfully"},
        400: {"description": "Invalid token format"},
        500: {"description": "Internal server error"},
    },
)
async def receive_donation(payload: PaymentPayload, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to receive a Cashu payment as per NUT-18.
    This endpoint is called by the sender wallet to complete the donation.
    """
    logger.info(f"Received donation payment payload: {payload}")
    try:
        token = payload.to_tokenv4().serialize()
        print(f"Received token: {token}")
        await receive_token(token, db)
    except Exception as e:
        logger.error(f"Error parsing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format",
        )

    return {"status": "success", "message": "Donation received"}
