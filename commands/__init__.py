"""
Command modules for the SBCoin Nightclub bot.
This package contains all the slash commands available in the bot.
"""

from .about_coin import about_coin
from .balance import balance
from .mining import mining
from .reels import reels
from .transfer import transfer
from .groups.aml import aml_group
from .groups.slots.slots_main import slots_group
from .groups.slots import insert_coins
from .groups.slots import show_help
from .groups.slots import jackpot
from .groups.slots import reboot
from .groups.slots import rtp
from .groups.slots import utils

__all__: list[str] = [
    "transfer",
    "reels", 
    "mining",
    "balance",
    "about_coin",
    "aml_group",
    "slots_group",
    "insert_coins",
    "show_help",
    "jackpot",
    "reboot",
    "rtp",
    "utils"
]
