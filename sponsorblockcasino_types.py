# region Imports
# Standard Library
from dataclasses import dataclass
from typing import Dict, TypedDict, List, TypeVar

# Third party
from discord import PartialEmoji
from pydantic import BaseModel
# endregion

# region Types


class BotConfig(TypedDict):
    coin: str
    Coin: str
    coins: str
    Coins: str
    coin_emoji_id: int
    coin_emoji_name: str
    casino_house_id: int
    administrator_id: int
    casino_channel_id: int
    mining_updates_channel_id: int
    mining_updates_channel_name: str
    mining_highlights_channel_id: int
    mining_highlights_channel_name: str
    blockchain_name: str
    Blockchain_name: str
    network_mining_enabled: bool
    grifter_swap_id: int
    sbcoin_id: int
    auto_approve_transfer_limit: int
    aml_office_channel_id: int
    aml_office_thread_id: int
    reaction_messages_enabled: bool


@dataclass(frozen=True)
class ReactionUser:
    global_name: str | None
    id: int
    name: str
    mention: str


class ReactionUserDict(TypedDict):
    global_name: str | None
    id: int
    name: str
    mention: str


class CoinReaction(TypedDict):
    created_at: float
    user: ReactionUser | ReactionUserDict


class MessageMiningTimeline(TypedDict):
    author_id: int
    author_name: str
    channel_id: int
    created_at: float
    reactions: List[CoinReaction]


class Reels(TypedDict):
    reel1: dict[str, int]
    reel2: dict[str, int]
    reel3: dict[str, int]


class ReelSymbol(TypedDict):
    emoji_name: str
    emoji_id: int
    fixed_amount: int
    wager_multiplier: float


class ReelResult(TypedDict):
    associated_combo_event: Dict[str, ReelSymbol]
    emoji: PartialEmoji


class ReelResults(TypedDict):
    reel1: ReelResult
    reel2: ReelResult
    reel3: ReelResult


class SpinEmoji(TypedDict):
    emoji_name: str
    emoji_id: int


class SpinEmojis(TypedDict):
    spin1: SpinEmoji
    spin2: SpinEmoji
    spin3: SpinEmoji


class SlotMachineConfig(BaseModel):
    combo_events: dict[str, ReelSymbol]
    reels: Reels
    reel_spin_emojis: SpinEmojis
    fees: dict[str, int | float]
    jackpot_pool: int
    new_bonus_wait_seconds: int
    starting_bonus_die_enabled: bool


class SaveData(TypedDict):
    user_name: str
    user_id: int
    has_visited_casino: bool
    starting_bonus_available: bool | float
    messages_mined: List[int]
    when_last_bonus_received: float | None
    reaction_message_received: bool
    mining_messages_enabled: bool
    blocked_from_receiving_coins: bool
    blocked_from_receiving_coins_reason: str | None


class TransactionRequest(TypedDict):
    sender_id: int
    receiver_id: int
    amount: int
    request_timestamp: float
    channel_id: int
    message_id: int
    purpose: str


T = TypeVar('T')
# endregion
