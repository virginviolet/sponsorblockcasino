"""
Command modules for the SBCoin Nightclub bot.
This package contains all the slash commands available in the bot.
"""

from .about_coin import about_coin
from .groups.aml import aml_group
from .balance import balance
from .mining import mining
from .reels import reels
from .slots import slots
from .transfer import transfer

__all__: list[str] = [
    "transfer",
    "slots",
    "reels", 
    "mining",
    "balance",
    "aml_group",
    "about_coin"
]
