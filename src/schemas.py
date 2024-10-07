from curses import OK
from datetime import datetime
from enum import Enum, auto
from typing import Optional

from pydantic import BaseModel, HttpUrl


class MintState(Enum):
    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"


class ChargeRequest(BaseModel):
    token: str


class MintRead(BaseModel):
    id: int
    url: HttpUrl
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

    class Config:
        orm_mode = True


class SwapEventRead(BaseModel):
    id: int
    from_id: int
    to_id: int
    from_url: HttpUrl
    to_url: HttpUrl
    amount: int
    fee: int
    created_at: datetime
    time_taken: int
    state: MintState

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
