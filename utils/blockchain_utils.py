"""
Functions for interacting with the blockchain from the Discord bot.
"""
# region Imports
# Standard Library
from hashlib import sha256
from typing import TYPE_CHECKING

# Third party
from discord import Member, User

# Local
if TYPE_CHECKING:
    from sponsorblockchain.sponsorblockchain_types import (
        BlockData)
import core.global_state as g
from schemas.data_classes import ReactionUser
from core.terminate_bot import terminate_bot
from sponsorblockchain.sponsorblockchain_types import Transaction
from sponsorblockchain.models.blockchain import Blockchain
from sponsorblockchain.models.block import Block
# endregion

# region Get timestamp


def get_last_block_timestamp() -> float | None:
    """
    Retrieves the timestamp of the last block in the blockchain.

    Returns:
        float | None: The timestamp of the last block if available,
        otherwise None.

    Raises:
        Exception: If there is an error retrieving the last block.
    """
    if g.blockchain is None:
        raise ValueError("blockchain is None.")

    last_block_timestamp: float | None = None
    try:
        # Get the last block's timestamp for logging
        last_block: None | Block = g.blockchain.get_last_block()
        if last_block is not None:
            last_block_timestamp = last_block.timestamp
            del last_block
        else:
            print("ERROR: Last block is None.")
            return None
    except Exception as e:
        print(f"ERROR: Error getting last block: {e}")
        return None
    return last_block_timestamp


# endregion

# region Add tx block


async def add_block_transaction(blockchain: Blockchain,
                                sender: Member | User | ReactionUser | int,
                                receiver: Member | User | ReactionUser | int,
                                amount: int,
                                method: str) -> None:
    """
    Adds a transaction to the blockchain.

    Args:
        blockchain: The blockchain instance to which the transaction will
            be added.
        sender: The sender of the transaction. Can be a Member, User,
            or an integer User ID.
        receiver: The receiver of the transaction. Can be a Member, User,
            or an integer ID.
        amount: The amount of the transaction.
        method: The method of the transaction; "reaction", "slot_machine",
            "transfer".

    Raises:
        Exception: If there is an error adding the transaction to
            the blockchain.
    """
    sender_id: int
    receiver_id: int
    if isinstance(sender, int):
        sender_id = sender
    else:
        sender_id = sender.id
    if isinstance(receiver, int):
        receiver_id = receiver
    else:
        receiver_id = receiver.id
    sender_id_unhashed: int = sender_id
    receiver_id_unhashed: int = receiver_id
    sender_id_hash: str = (
        sha256(str(sender_id_unhashed).encode()).hexdigest())
    del sender_id
    del sender_id_unhashed
    receiver_id_hash: str = (
        sha256(str(receiver_id_unhashed).encode()).hexdigest())
    del receiver_id
    del receiver_id_unhashed
    print("Adding transaction to blockchain...")
    try:
        transaction = Transaction(
            sender=sender_id_hash,
            receiver=receiver_id_hash,
            amount=amount,
            method=method
        )
        data: BlockData = (
            [{"transaction": transaction}])
        blockchain.add_block(data=data, difficulty=0)
    except Exception as e:
        print(f"ERROR: Error adding transaction to blockchain: {e}")
        await terminate_bot()
    print("Transaction added to blockchain.")
# endregion
