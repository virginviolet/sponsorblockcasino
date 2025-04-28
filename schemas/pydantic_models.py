from typing import Dict, List, Optional
from pydantic import BaseModel

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

class SlotsHighScoreWinEntry(BaseModel):
    created_at: float
    event: SlotEvent
    fees: Dict[str, SlotFeeDetail]
    id: int
    message: SlotMessage
    result: SlotResultSimple
    user: UserSimple
    wager: int
    win_money: int

class SlotsHighScoreWins(BaseModel):
    entries: List[SlotsHighScoreWinEntry]
    last_updated: float

class HighScores(BaseModel):
    highest_wins: SlotsHighScoreWins