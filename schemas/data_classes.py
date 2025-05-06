# region Imports
# Standard Library
from dataclasses import dataclass
from typing import Dict, List, Optional

# Third party
from pydantic import BaseModel

# Local
from .typed import ReelSymbol, Reels, SpinEmojis
# endregion

# region Data Classes


@dataclass(frozen=True)
class ReactionUser:
    global_name: str | None
    id: int
    name: str
    mention: str


class SlotMachineConfig(BaseModel):
    combo_events: dict[str, ReelSymbol]
    reels: Reels
    reel_spin_emojis: SpinEmojis
    fees: dict[str, int | float]
    jackpot_pool: int
    new_bonus_wait_seconds: int
    starting_bonus_die_enabled: bool


class SlotEvent(BaseModel):
    fixed_amount: int
    name: str
    name_friendly: str
    wager_multiplier: float


class SlotFeeDetail(BaseModel):
    amount: int
    name: str
    percentage: float


class SlotMessage(BaseModel):
    author_id: int
    author_name: str
    channel_id: int
    id: int


class SlotReelSymbol(BaseModel):
    id: int
    name: str


class SlotResultSimple(BaseModel):
    reel1: SlotReelSymbol
    reel2: SlotReelSymbol
    reel3: SlotReelSymbol


class UserSimple(BaseModel):
    global_name: Optional[str]
    id: int
    mention: str
    name: str


class SlotsHighScoreEntry(BaseModel):
    created_at: float
    event: SlotEvent
    fees: Dict[str, SlotFeeDetail]
    id: int
    message: SlotMessage
    result: SlotResultSimple
    user: UserSimple
    wager: int
    win_money: int


class SlotsHighScoreCategory(BaseModel):
    entries: List[SlotsHighScoreEntry]
    last_updated: float


class HighScores(BaseModel):
    highest_wins: SlotsHighScoreCategory
    highest_wager: SlotsHighScoreCategory


class DonationGoal(BaseModel):
    created_at: float
    donated_amount: int
    donation_recipient_id: int
    donation_recipient_name: str
    donation_recipient_mention: str
    goal_description: str | None
    id: int
    reward_setting_key: str | None
    reward_setting_value: bool | None
    target_amount: int
    goal_reached_message_content: str | None
# endregion
