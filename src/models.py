from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Mint(Base):
    __tablename__ = "mints"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(512), unique=True)
    info = Column(String(10_000), nullable=True)
    name = Column(String(50), unique=True)
    balance = Column(Integer)
    sum_donations = Column(Integer)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    next_update = Column(DateTime)
    state = Column(String(10))
    n_errors = Column(Integer)
    n_mints = Column(Integer)
    n_melts = Column(Integer)


class SwapEvent(Base):
    __tablename__ = "swaps"

    id = Column(Integer, primary_key=True, index=True)
    from_id = Column(Integer, foreign_key="mints.id")
    to_id = Column(Integer, foreign_key="mints.id")
    from_url = Column(String, foreign_key="mints.url")
    to_url = Column(String, foreign_key="mints.url")
    amount = Column(Integer)
    fee = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    time_taken = Column(Integer)
    state = Column(String(10))
    error = Column(String(10_000))
