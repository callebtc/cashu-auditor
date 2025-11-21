from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, AnyUrl, Field


class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(
        default=100, ge=1, le=1000, description="Number of items to return"
    )


class PaymentRequestResponse(BaseModel):
    pr: str


class MintState(Enum):
    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class ChargeRequest(BaseModel):
    token: str


class MintRead(BaseModel):
    id: int
    url: AnyUrl
    info: Optional[str] = None
    name: str
    balance: int
    sum_donations: int
    updated_at: datetime
    next_update: Optional[datetime] = None
    state: MintState
    n_errors: int
    n_mints: int
    n_melts: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        orm_mode = True


class SwapEventRead(BaseModel):
    id: int
    from_id: int
    to_id: int
    from_url: AnyUrl
    to_url: AnyUrl
    amount: int
    fee: int
    created_at: datetime
    time_taken: int
    state: MintState
    error: Optional[str] = None

    class Config:
        orm_mode = True


class MintGraphEdge(BaseModel):
    from_id: int
    to_id: int
    count: int
    total_amount: int
    total_fee: int
    last_swap: datetime
    state: MintState


class MintGraph(BaseModel):
    nodes: list[MintRead]
    edges: list[MintGraphEdge]


class MintStats(BaseModel):
    total_balance: int
    total_swaps: int
    total_swaps_24h: int
    total_amount_swapped: int
    total_amount_swapped_24h: int
    average_swap_time: float
    average_swap_time_24h: float
