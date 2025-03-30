import asyncio
import json
import time
from typing import Optional
import random
from cashu.wallet.wallet import Wallet
from cashu.wallet.crud import get_bolt11_mint_quotes, bump_secret_derivation
from cashu.wallet.helpers import receive, deserialize_token_from_string
from cashu.core.models import ProofState
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashu.core.base import MintQuoteState
from cashu.core.helpers import sum_proofs
from src.models import Mint, SwapEvent
from .database import engine
from .schemas import MintState
from .helpers import sanitize_err

MIN_SWAP_DELAY = 5 * 60  # seconds
MAX_SWAP_DELAY = 15 * 60  # seconds
BALANCE_UPDATE_DELAY = 60  # seconds
MINIMUM_AMOUNT = 5  # satoshis
MAXIMUM_AMOUNT = 100  # satoshis


class Auditor:
    wallet: Wallet

    def __init__(self):
        pass

    async def init_wallet(self):
        # we need to run the migrations once
        self.wallet = await Wallet.with_db("https://testnut.cashu.space", ".")
        await self.wallet.load_proofs(reload=True)
        logger.info(f"Wallet initialized. Balance: {self.wallet.available_balance}")

        await self.update_all_balances()
        asyncio.create_task(self.monitor_swap_task())

        # asyncio.create_task(self.update_balances_task())
        # asyncio.create_task(self.mint_outstanding())
        asyncio.create_task(self.update_all_mint_infos())

    async def monitor_swap_task(self):
        while True:
            try:
                await self.swap_task()
            except Exception as e:
                logger.error(f"swap_task failed: {e}")
                await asyncio.sleep(5)

    async def mint_outstanding(self):
        # get all mints
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint))
            mints = result.scalars().all()
            session.expunge_all()  # Detach mints before session closes

        # load all wallets and get mint quotes that are outstanding
        for mint in mints:
            wallet = await Wallet.with_db(mint.url, ".")
            mint_quotes = await get_bolt11_mint_quotes(
                db=wallet.db,
                state=MintQuoteState.unpaid,
                mint=mint.url,
            )
            if not mint_quotes:
                continue
            await wallet.load_proofs(reload=True)
            try:
                logger.info(f"Loading mint: {mint.url}")
                await wallet.load_mint()
            except Exception as e:
                logger.error(f"Error loading mint: {e}")
                await self.bump_mint_errors(mint)
                continue
            logger.info(f"Found {len(mint_quotes)} unpaid mint quotes.")
            # TODO: Filter invoices per mint!!!
            for i, mint_quote in enumerate(mint_quotes):
                logger.info(
                    f"Checking mint quote: {mint_quote} ({i+1}/{len(mint_quotes)})"
                )
                if mint_quote.amount < 0 or mint_quote.paid:
                    continue
                logger.info(f"Checking unpaid mint quote: {mint_quote}")
                await asyncio.sleep(1)
                try:
                    proofs = await wallet.mint(mint_quote.amount, mint_quote.quote)
                    logger.info(f"Minted {sum_proofs(proofs)} sats on {mint.url}")
                    await self.bump_mint_n_mints(mint)
                except Exception as e:
                    logger.error(f"Error minting: {e}")
                    await self.recover_errors(wallet, e)
                    await self.bump_mint_errors(mint)

    async def check_proofs(self, wallet: Wallet):
        reserved_proofs = [p for p in wallet.proofs if p.reserved]
        if len(reserved_proofs) == 0:
            return
        logger.info(
            f"Checking {len(reserved_proofs)} of {len(wallet.proofs)} reserved proofs on mint {wallet.url}"
        )
        # invalidate proofs in batches
        try:
            batch_size = 50
            for _proofs in [
                reserved_proofs[i : i + batch_size]
                for i in range(0, len(reserved_proofs), batch_size)
            ]:
                logger.info(f"Checking {len(_proofs)} proofs on mint {wallet.url}")
                await wallet.invalidate(_proofs, check_spendable=True)
        except Exception as e:
            logger.error(f"Error checking proofs: {e}")

        reserved_proofs = [p for p in wallet.proofs if p.reserved]
        await wallet.set_reserved(reserved_proofs, reserved=False)
        # Update the reserved status in wallet.proofs
        for p in wallet.proofs:
            p.reserved = False

    async def recover_errors(self, wallet: Wallet, e: Exception) -> bool:
        if "outputs have already been signed before" in str(
            e
        ) or "secret already used" in str(e):
            logger.error(
                "Outputs have already been signed before error. Bumping keyset counter."
            )
            await bump_secret_derivation(wallet.db, wallet.keyset_id, by=10)
            return True
        if "already spent" in str(e) or "Proof already used" in str(e):
            logger.error("Token already spent error. Invalidating wallet proofs.")
            len_checked = len(wallet.proofs)
            spendable_proofs = await wallet.invalidate(
                wallet.proofs, check_spendable=True
            )
            logger.info(f"Invalidated {len_checked-len(spendable_proofs)} proofs.")
            return True
        return False

    async def update_all_balances(self):
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint))
            mints = result.scalars().all()
            session.expunge_all()  # Detach mints before session closes
        for mint in mints:
            wallet = await Wallet.with_db(mint.url, ".")
            await wallet.load_proofs(reload=True)
            mint.balance = wallet.available_balance
        # Now update the balances in the database
        async with AsyncSession(engine) as session:
            for mint in mints:
                session.add(mint)
            await session.commit()

    async def update_mint_balance(self, mint: Mint):
        wallet = await Wallet.with_db(mint.url, ".")
        await wallet.load_proofs(reload=True)
        new_balance = wallet.available_balance
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.execute(select(Mint).where(Mint.id == mint.id))
            mint_in_session = result.scalars().first()
            if not mint_in_session:
                raise ValueError(f"Mint with ID {mint.id} not found.")
            mint_in_session.balance = new_balance
            # Update the original mint object
            logger.info(
                f"Updated balance for mint {mint_in_session.url} to {mint_in_session.balance} sat."
            )
            await session.commit()
            session.expunge(mint_in_session)

    async def update_all_mint_infos(self):
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint))
            mints = result.scalars().all()
            session.expunge_all()  # Detach mints
        for mint in mints:
            logger.info(f"Updating mint info for {mint.url}")
            try:
                wallet = await Wallet.with_db(mint.url, ".")
                await wallet.load_mint()
                mint.info = json.dumps(wallet.mint_info.dict())
            except Exception as e:
                logger.error(f"Error loading mint: {e}")
                await self.bump_mint_errors(mint)
                continue
        # Now update the mints in the database
        async with AsyncSession(engine) as session:
            for mint in mints:
                session.add(mint)
            await session.commit()

    async def update_wallet_mint_info(self, wallet: Wallet):
        logger.info(f"Updating mint info for {wallet.url}")
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint).where(Mint.url == wallet.url))
            mint = result.scalars().first()
            if mint:
                mint.info = json.dumps(wallet.mint_info.dict())
                logger.debug(f"Updated mint info for {wallet.url}: {mint.info}")
                await session.commit()
            else:
                logger.error(f"Mint with URL {wallet.url} not found.")

    async def bump_mint_errors(self, mint_id: int):
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint).where(Mint.id == mint_id))
            mint_in_session = result.scalars().first()
            if mint_in_session:
                previous_n_errors = mint_in_session.n_errors
                mint_in_session.n_errors += 1
                mint_in_session.state = MintState.ERROR.value

                # Update the original mint object
                logger.debug(
                    f"Bumping n_errors for {mint_in_session.url} from {previous_n_errors} to {mint_in_session.n_errors}"
                )

                await session.commit()
                session.expunge(mint_in_session)
            else:
                logger.error(f"Mint with ID {mint_in_session.id} not found.")

    async def bump_mint_n_mints(self, mint: Mint):
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.execute(select(Mint).where(Mint.id == mint.id))
            mint_in_session = result.scalars().first()
            if mint_in_session:
                previous_n_mints = mint_in_session.n_mints
                mint_in_session.n_mints += 1
                await session.commit()
                session.expunge(mint_in_session)
                # Update the original mint object
                mint.n_mints = mint_in_session.n_mints
                logger.debug(
                    f"Bumping n_mints for {mint.url} from {previous_n_mints} to {mint.n_mints}"
                )
            else:
                logger.error(f"Mint with ID {mint.id} not found.")

    async def bump_mint_n_melts(self, mint: Mint):
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.execute(select(Mint).where(Mint.id == mint.id))
            mint_in_session = result.scalars().first()
            if mint_in_session:
                previous_n_melts = mint_in_session.n_melts
                mint_in_session.n_melts += 1
                mint_in_session.state = MintState.OK.value
                await session.commit()
                session.expunge(mint_in_session)
                # Update the original mint object
                mint.n_melts = mint_in_session.n_melts
                mint.state = mint_in_session.state
                logger.debug(
                    f"Bumping n_melts for {mint.url} from {previous_n_melts} to {mint.n_melts}"
                )
            else:
                logger.error(f"Mint with ID {mint.id} not found.")

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
        await self.wallet.load_proofs(reload=True)
        balance_before = self.wallet.available_balance
        wallet_after = await receive(self.wallet, token_obj)
        balance_received = wallet_after.available_balance - balance_before
        return balance_received

    async def get_mint(self, mint_url: str) -> Mint:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint).where(Mint.url == mint_url))
            mint = result.scalars().first()
            if mint:
                session.expunge(mint)  # Detach the mint
            else:
                logger.error(f"Mint with URL {mint_url} not found.")
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
            session.expunge_all()  # Detach mints before session closes

        min_balance_threshold = 100
        mints = [
            mint
            for mint in mints
            if mint.state == MintState.OK.value or mint.balance < min_balance_threshold
        ]
        mints = [mint for mint in mints if mint.balance < mint.sum_donations]
        if not mints:
            raise ValueError("No suitable mints found.")
        # mint = max(
        #     mints,
        #     key=lambda mint: (
        #         (mint.sum_donations - mint.balance) / mint.sum_donations
        #         if mint.sum_donations > 0 and mint.balance > 0
        #         else 0
        #     ),
        # )
        to_mint = random.choice(mints)
        return to_mint

    async def choose_from_mint_and_amount(self, to_mint: Mint) -> tuple[Mint, int]:
        # choose mint with enough balance to send to to_mint
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Mint).where(Mint.url != to_mint.url))
            mints = result.scalars().all()
            session.expunge_all()  # Detach mints
        if not mints:
            raise ValueError("No mints available for selection.")

        mint_max_balance = max(mints, key=lambda mint: mint.balance)
        max_receivable = to_mint.sum_donations - to_mint.balance
        max_receivable = max(max_receivable, MINIMUM_AMOUNT)
        max_amount = min(max_receivable, mint_max_balance.balance)
        amount = random.randint(MINIMUM_AMOUNT, min(max_amount, MAXIMUM_AMOUNT))

        mints = [mint for mint in mints if mint.balance * 0.8 >= amount]
        if not mints:
            raise ValueError("No mints have sufficient balance.")
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
        error: Optional[str] = None,
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
                error=error,
            )
            session.add(swap_event)
            await session.commit()

    async def swap_task(self):
        while True:
            swap_delay = random.randint(MIN_SWAP_DELAY, MAX_SWAP_DELAY)
            await asyncio.sleep(swap_delay)

            to_mint = await self.choose_to_mint()
            to_wallet = await Wallet.with_db(to_mint.url, ".")
            try:
                await to_wallet.load_mint()
                await to_wallet.load_proofs(reload=True)
                await self.update_wallet_mint_info(to_wallet)
            except Exception as e:
                logger.error(f"Error loading mint: {e}")
                await self.bump_mint_errors(to_mint.id)
                raise e

            from_mint, amount = await self.choose_from_mint_and_amount(to_mint)
            from_wallet = await Wallet.with_db(from_mint.url, ".")
            try:
                await from_wallet.load_mint()
                await from_wallet.load_proofs(reload=True)
                await self.update_wallet_mint_info(from_wallet)
            except Exception as e:
                logger.error(f"Error loading mint: {e}")
                await self.bump_mint_errors(from_mint.id)
                raise e

            logger.info(
                f"Swapping from {from_mint.url} to {to_mint.url} amount: {amount} sat"
            )

            await self.update_mint_balance(from_mint)
            await self.update_mint_balance(to_mint)

            try:
                mint_quote = await to_wallet.request_mint(amount)
            except Exception as e:
                logger.error(f"Error getting invoice: {e}")
                await self.bump_mint_errors(to_mint.id)
                raise e

            try:
                melt_quote = await from_wallet.melt_quote(mint_quote.request)
            except Exception as e:
                logger.error(f"Error getting melt quote: {e}")
                await self.bump_mint_errors(from_mint.id)
                await self.store_swap_event(
                    from_mint,
                    to_mint,
                    amount,
                    0,
                    0,
                    MintState.ERROR.value,
                    sanitize_err(e),
                )
                raise e

            balance_before_melt = from_wallet.available_balance
            total_amount = melt_quote.amount + melt_quote.fee_reserve

            try:
                send_proofs, _ = await from_wallet.select_to_send(
                    from_wallet.proofs,
                    total_amount,
                    include_fees=True,
                    set_reserved=True,
                )
            except Exception as e:
                this_error = await self.recover_errors(from_wallet, e)
                logger.error(
                    f"Could not select amount ({melt_quote.amount} sat) plus fee reserve ({melt_quote.fee_reserve} sat) total {total_amount} sat from sending wallet."
                )
                raise e

            mint_worked = False
            try:
                time_start = time.time()
                await from_wallet.melt(
                    send_proofs,
                    mint_quote.request,
                    melt_quote.fee_reserve,
                    melt_quote.quote,
                )
                time_taken_ms = (time.time() - time_start) * 1000
                await from_wallet.load_proofs(reload=True)
                balance_after_melt = from_wallet.available_balance
                logger.info(
                    f"Melt successful: time taken: {int(time_taken_ms)} ms. Amount: {melt_quote.amount} sat. Fee reserve: {melt_quote.fee_reserve} sat. Fee: {(balance_before_melt - balance_after_melt) - amount} sat."
                )
            except Exception as e:
                logger.error(f"Error melting: {e}")
                melt_error = sanitize_err(e)
                time_taken_ms = (time.time() - time_start) * 1000
                await from_wallet.load_proofs(reload=True)
                balance_after_melt = from_wallet.available_balance
                this_error = await self.recover_errors(from_wallet, e)
                # still try to mint in case of any non-recoverable error
                if not this_error:
                    try:
                        logger.info("Trying to mint although melt failed.")
                        await asyncio.sleep(5)
                        proofs = await to_wallet.mint(amount, mint_quote.quote)
                        mint_worked = True
                        logger.success("Mint worked.")
                    except Exception as e2:
                        logger.error(f"Error minting: {e2}")
                        pass

                if not mint_worked:
                    logger.info("Mint did not work.Checking proof states.")
                    spent_proofs = []
                    unspent_proofs = []
                    proof_states = await from_wallet.check_proof_state(send_proofs)
                    for j, state in enumerate(proof_states.states):
                        if state == ProofState.spent:
                            spent_proofs.append(send_proofs[j])
                        elif state == ProofState.unspent:
                            unspent_proofs.append(send_proofs[j])

                    logger.info(f"Unspent proofs: {len(unspent_proofs)}")
                    logger.info(f"Spent proofs: {len(spent_proofs)}")
                    await from_wallet.set_reserved(unspent_proofs, reserved=False)
                    await from_wallet.invalidate(spent_proofs)

                    if this_error:
                        logger.info("Not storing this event as a failure.")
                        raise Exception("Error melting and minting.")
                    await self.bump_mint_errors(from_mint.id)
                    await self.store_swap_event(
                        from_mint,
                        to_mint,
                        amount,
                        0,
                        0,
                        MintState.ERROR.value,
                        melt_error,
                    )

                    raise e
                else:
                    pass

            if not mint_worked:
                try:
                    logger.info("Minting after melt succeed.")
                    await asyncio.sleep(2)
                    proofs = await to_wallet.mint(amount, mint_quote.quote)
                    logger.info(f"Minted {sum_proofs(proofs)} sat to {to_mint.url}")
                except Exception as e:
                    logger.error(f"Error minting: {e}")
                    await self.bump_mint_errors(to_mint.id)
                    raise e

            await self.update_mint_db(from_wallet)
            await self.update_mint_db(to_wallet)
            await self.bump_mint_n_melts(from_mint)
            await self.bump_mint_n_mints(to_mint)
            await self.store_swap_event(
                from_mint,
                to_mint,
                amount,
                (balance_before_melt - balance_after_melt) - amount,
                time_taken_ms,
                MintState.OK.value,
            )

            await self.update_mint_balance(from_mint)
            await self.update_mint_balance(to_mint)

            logger.success(
                f"Swap from {from_mint.url} to {to_mint.url} of {amount} sat successful."
            )
