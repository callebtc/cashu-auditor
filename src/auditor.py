import asyncio
import time
import bolt11
import random
from cashu.wallet.wallet import Wallet
from cashu.wallet.crud import get_lightning_invoices
from cashu.core.models import GetInfoResponse
from cashu.wallet.helpers import receive, deserialize_token_from_string
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Mint, SwapEvent
from .database import engine, get_db
from .schemas import MintState

SWAP_DELAY = 5 * 60  # seconds
BALANCE_UPDATE_DELAY = 60  # seconds
MINIMUM_AMOUNT = 5  # satoshis


class Auditor:
    wallet: Wallet

    def __init__(self):
        pass

    async def init_wallet(self):
        # we need to run the migrations once
        self.wallet = await Wallet.with_db("https://testnut.cashu.space", ".")
        await self.wallet.load_proofs()
        logger.info(f"Wallet initialized. Balance: {self.wallet.available_balance}")

        # await self.mint_outstanding()

        await self.update_all_balances()
        asyncio.create_task(self.update_balances_task())
        asyncio.create_task(self.monitor_swap_task())

    async def monitor_swap_task(self):
        while True:
            try:
                await self.swap_task()
            except Exception as e:
                logger.error(f"swap_task crashed: {e}")
                await asyncio.sleep(5)

    async def mint_outstanding(self):
        # get all mints
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint))
            mints = result.scalars().all()

        # load all wallets and get mint quotes that are outstanding
        for mint in mints:
            wallet = await Wallet.with_db(mint.url, ".")
            await wallet.load_proofs()
            try:
                logger.info(f"Loading mint: {mint.url}")
                await wallet.load_mint()
            except Exception as e:
                logger.error(f"Error loading mint: {e}")
                await self.bump_mint_errors(mint)
                continue
            mint_quotes = await get_lightning_invoices(
                db=wallet.db,
                paid=False,
            )
            # TODO: Filter invoices per mint!!!
            for mint_quote in mint_quotes:
                invoice = bolt11.decode(mint_quote.bolt11)
                if (
                    mint_quote.amount < 0
                    or mint_quote.paid
                    or invoice.expiry_time < time.time()
                ):
                    continue
                logger.info(f"Checking unpaid mint quote: {mint_quote}")
                try:
                    proofs = await wallet.mint(mint_quote.amount, mint_quote.id)
                    await self.bump_mint_n_mints(mint)
                except Exception as e:
                    logger.error(f"Error minting: {e}")
                    await self.bump_mint_errors(mint)

    async def update_all_balances(self):
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint))
            mints = result.scalars().all()
            for mint in mints:
                wallet = await Wallet.with_db(mint.url, ".")
                await wallet.load_proofs()
                mint.balance = wallet.available_balance
            await session.commit()

    async def set_mint_state(self, mint: Mint, state: MintState):
        async with AsyncSession(engine) as session:
            mint.state = state.value
            session.add(mint)
            await session

    async def bump_mint_errors(self, mint: Mint):
        async with AsyncSession(engine) as session:
            mint_in_session = await session.merge(mint)
            mint_in_session.n_errors += 1
            mint_in_session.state = MintState.ERROR.value
            await session.commit()

    async def bump_mint_n_mints(self, mint: Mint):
        async with AsyncSession(engine) as session:
            mint_in_session = await session.merge(mint)
            mint_in_session.n_mints += 1
            await session.commit()

    async def bump_mint_n_melts(self, mint: Mint):
        async with AsyncSession(engine) as session:
            mint_in_session = await session.merge(mint)
            mint_in_session.n_melts += 1
            await session.commit()

    async def update_balances_task(self):
        while True:
            await asyncio.sleep(BALANCE_UPDATE_DELAY)
            await self.update_all_balances()

    async def receive_token(self, token: str) -> int:
        token_obj = deserialize_token_from_string(token)
        if token_obj.unit != "sat":
            raise ValueError("Only satoshi units are supported.")
        self.wallet = await Wallet.with_db(token_obj.mint, ".")
        await self.wallet.load_mint()
        await self.wallet.load_proofs()
        balance_before = self.wallet.available_balance
        wallet_after = await receive(self.wallet, token_obj)
        balance_received = wallet_after.available_balance - balance_before
        return balance_received

    async def get_mint(self, mint_url: str) -> Mint:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint).where(Mint.url == mint_url))
            mint = result.scalars().first()
            return mint

    async def update_mint_db(self, wallet: Wallet):
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint).where(Mint.url == wallet.url))
            mint = result.scalars().first()
            if mint:
                mint.balance = wallet.available_balance
                await session.commit()
            else:
                logger.error(f"Mint with URL {wallet.url} not found.")

    async def choose_to_mint(self) -> Mint:
        # choose mint with highest balance to donation ratio
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint))
            mints = result.scalars().all()
            mints = [
                mint
                for mint in mints
                if mint.state == MintState.OK.value or mint.n_melts > 0
            ]
            mint = max(
                mints,
                key=lambda mint: (mint.sum_donations - mint.balance)
                / mint.sum_donations,
            )
            return mint

    async def choose_from_mint_and_amount(self, to_mint: Mint) -> tuple[Mint, int]:
        # choose mint with enough balance to send to to_mint
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint).where(Mint.url != to_mint.url))
            mints = result.scalars().all()
        mint_max_balance = max(mints, key=lambda mint: mint.balance)
        max_receivable = to_mint.sum_donations - to_mint.balance
        max_receivable = max(max_receivable, MINIMUM_AMOUNT)
        max_amount = min(max_receivable, mint_max_balance.balance)
        amount = random.randint(MINIMUM_AMOUNT, max_amount)
        mints = [mint for mint in mints if mint.balance * 0.8 >= amount]
        from_mint = random.choice(mints)
        return from_mint, amount

    async def store_swap_event(
        self,
        from_mint: Mint,
        to_mint: Mint,
        amount: int,
        fee: int,
        time_taken: int,
        state: str,
    ):
        async with AsyncSession(engine) as session:
            swap_event = SwapEvent(
                from_id=from_mint.id,
                to_id=to_mint.id,
                from_url=from_mint.url,
                to_url=to_mint.url,
                amount=amount,
                fee=fee,
                time_taken=time_taken,
                state=state,
            )
            session.add(swap_event)
            await session.commit()

    async def swap_task(self):
        while True:
            await asyncio.sleep(SWAP_DELAY)

            to_mint = await self.choose_to_mint()
            to_wallet = await Wallet.with_db(to_mint.url, ".")
            try:
                await to_wallet.load_mint()
                await to_wallet.load_proofs()
            except Exception as e:
                logger.error(f"Error loading mint: {e}")
                await self.bump_mint_errors(to_mint)
                raise e

            from_mint, amount = await self.choose_from_mint_and_amount(to_mint)
            from_wallet = await Wallet.with_db(from_mint.url, ".")
            try:
                await from_wallet.load_mint()
                await from_wallet.load_proofs()
            except Exception as e:
                logger.error(f"Error loading mint: {e}")
                await self.bump_mint_errors(from_mint)
                raise e

            logger.info(
                f"Swapping from {from_mint.url} to {to_mint.url} amount: {amount} sat"
            )

            try:
                invoice = await to_wallet.mint_quote(amount)
            except Exception as e:
                logger.error(f"Error getting invoice: {e}")
                await self.bump_mint_errors(to_mint)
                raise e

            try:
                melt_quote = await from_wallet.melt_quote(invoice.bolt11)
            except Exception as e:
                logger.error(f"Error getting melt quote: {e}")
                await self.bump_mint_errors(from_mint)
                await self.store_swap_event(
                    from_mint,
                    to_mint,
                    amount,
                    0,
                    0,
                    "ERROR",
                )
                raise e

            balance_before_melt = from_wallet.available_balance
            total_amount = melt_quote.amount + melt_quote.fee_reserve

            send_proofs, _ = await from_wallet.select_to_send(
                from_wallet.proofs, total_amount, include_fees=True, set_reserved=True
            )

            try:
                time_start = time.time()
                melt_response = await from_wallet.melt(
                    send_proofs,
                    invoice.bolt11,
                    melt_quote.fee_reserve,
                    melt_quote.quote,
                )
                time_taken_ms = (time.time() - time_start) * 1000
                await from_wallet.load_proofs()
                balance_after_melt = from_wallet.available_balance
                await self.bump_mint_n_melts(from_mint)
            except Exception as e:
                logger.error(f"Error melting: {e}")
                await self.bump_mint_errors(from_mint)
                await self.store_swap_event(
                    from_mint,
                    to_mint,
                    amount,
                    0,
                    0,
                    "ERROR",
                )
                raise e

            await asyncio.sleep(5)

            try:
                proofs = await to_wallet.mint(amount, invoice.id)
                await self.bump_mint_n_mints(to_mint)
            except Exception as e:
                logger.error(f"Error minting: {e}")
                await self.bump_mint_errors(to_mint)
                raise e

            await self.update_mint_db(from_wallet)
            await self.update_mint_db(to_wallet)

            await self.store_swap_event(
                from_mint,
                to_mint,
                amount,
                (balance_before_melt - balance_after_melt) - amount,
                time_taken_ms,
                "OK",
            )

            logger.success(
                f"Swap from {from_mint.url} to {to_mint.url} of {amount} sat successful."
            )
