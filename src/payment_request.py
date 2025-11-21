import base64
from typing import List, Optional, Dict, Any, Union

import cbor2
from pydantic import BaseModel, Field

from cashu.core.base import TokenV4, TokenV4Token, TokenV4Proof


class Transport(BaseModel):
    t: str  # Type of Transport
    a: str  # Target of Transport
    g: Optional[List[List[str]]] = None  # Optional tags for the Transport


class PaymentRequest:
    def __init__(
        self,
        unit: Optional[str] = None,
        mints: Optional[List[str]] = None,
        amount: Optional[int] = None,
        description: Optional[str] = None,
        http_endpoint: Optional[str] = None,
        payment_id: Optional[str] = None,
        single_use: Optional[bool] = None,
    ):
        self.payment_id = payment_id  # i: Payment id
        self.amount = amount  # a: The amount of the requested payment
        self.unit = unit  # u: The unit of the requested payment
        self.single_use = single_use  # s: Whether the payment request is for single use
        self.mints = (
            mints or []
        )  # m: A set of mints from which the payment is requested
        self.description = description  # d: A human readable description

        # Create transport with HTTP POST endpoint if provided
        self.transports = []
        if http_endpoint:
            self.transports.append(Transport(t="post", a=http_endpoint))

    def to_dict(self) -> Dict[str, Any]:
        """Convert PaymentRequest to dictionary format for serialization"""
        result = {}

        if self.payment_id is not None:
            result["i"] = self.payment_id

        if self.amount is not None:
            result["a"] = self.amount

        if self.unit is not None:
            result["u"] = self.unit

        if self.single_use is not None:
            result["s"] = self.single_use

        if self.mints:
            result["m"] = self.mints

        if self.description is not None:
            result["d"] = self.description

        if self.transports:
            result["t"] = [
                {"t": t.t, "a": t.a, **({"g": t.g} if t.g is not None else {})}
                for t in self.transports
            ]

        return result

    def serialize(self) -> str:
        """
        Serialize the payment request to a base64-encoded CBOR string
        with the 'creqA' prefix as specified in NUT-18
        """
        # Convert to dictionary format
        payment_request_dict = self.to_dict()

        # Serialize to CBOR
        cbor_data = cbor2.dumps(payment_request_dict)

        # Encode to base64 url-safe
        base64_data = base64.urlsafe_b64encode(cbor_data).decode("utf-8")

        # Add prefix
        return f"creqA{base64_data}"


class Proof(BaseModel):
    """Cashu proof as defined in NUT-00"""

    id: str
    amount: int
    secret: str
    C: str

    class Config:
        extra = "allow"  # Allow extra fields for DLEQ proofs


class PaymentPayload(BaseModel):
    """
    Payment payload as defined in NUT-18

    This is the format that a sender sends to a receiver when making a payment
    """

    id: Optional[str] = None  # Payment ID (corresponding to 'i' in request)
    memo: Optional[str] = None  # Optional memo to be sent with payment
    mint: str  # Mint URL from which the ecash is from
    unit: str  # Unit of the payment
    proofs: List[Proof]  # Array of proofs

    def to_tokenv4(self) -> TokenV4:
        """
        Convert the PaymentPayload to a TokenV4 object
        """
        # get all unique p.ids
        unique_ids = {proof.id for proof in self.proofs}

        # # now do the equivalent of this:
        # tokens: List[TokenV4Token] = []
        # for keyset_id in keyset_ids:
        #     proofs_keyset = [p for p in proofs if p.id == keyset_id]
        #     tokenv4_proofs = []
        #     for proof in proofs_keyset:
        #         tokenv4_proofs.append(TokenV4Proof.from_proof(proof, include_dleq))
        #     tokenv4_token = TokenV4Token(i=bytes.fromhex(keyset_id), p=tokenv4_proofs)
        #     tokens.append(tokenv4_token)

        # return TokenV4(m=mint_url, u=unit_str, t=tokens, d=memo)

        # Create a list of TokenV4Token objects
        tokens: List[TokenV4Token] = []
        for keyset_id in unique_ids:
            print(f"Processing keyset ID: {keyset_id}")
            # Filter proofs for the current keyset ID
            proofs_keyset = [p for p in self.proofs if p.id == keyset_id]
            # add p.dleq = None to each proof
            for proof in proofs_keyset:
                proof.dleq = None
                proof.witness = None

            # Create TokenV4Proof objects from the proofs
            tokenv4_proofs = [TokenV4Proof.from_proof(proof) for proof in proofs_keyset]

            # Create a TokenV4Token object with the keyset ID and proofs
            tokenv4_token = TokenV4Token(i=bytes.fromhex(keyset_id), p=tokenv4_proofs)

            # Append to the tokens list
            tokens.append(tokenv4_token)

        # Create the TokenV4 object
        return TokenV4(m=self.mint, u=self.unit, d=self.memo, t=tokens)
