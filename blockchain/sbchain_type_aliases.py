# region Imports
# Standard Library
from typing import List, Dict, TypedDict
# endregion


# region Type aliases


class TransactionDict(TypedDict):
    sender: str
    receiver: str
    amount: int
    method: str


class BlockDict(TypedDict):
    index: int
    timestamp: float
    data: List[str | Dict[str, TransactionDict]]
    previous_block_hash: str
    nonce: int
    block_hash: str
# endregion
