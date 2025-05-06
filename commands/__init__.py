"""
Command modules for the SBCoin Nightclub bot.
This package contains all the slash commands available in the bot.
"""

from .leaderboard import (leaderboard_group, leaderboard_slots_group, holder,
                          slots_single_win, sponsor)
from .maintainer.maintainer_main import maintainer_group
from .maintainer import maintainer_donation_goal, reels
from .mining.mining_main import mining_group
from .mining import mining_stats, mining_settings
from .slots.slots_main import slots_group
from .slots import insert_coins, show_help, jackpot, reboot, rtp, slots_utils
from .about_coin import about_coin
from .aml import aml_group
from .balance import balance
from .donation_goal import donation_goal
from .transfer import transfer

__all__: list[str] = [
    "transfer",
    "reels", 
    "balance",
    "about_coin",
    "maintainer_donation_goal",
    "aml_group",
    "mining_settings",
    "mining_stats",
    "mining_group",
    "slots_group",
    "insert_coins",
    "show_help",
    "jackpot",
    "reboot",
    "rtp",
    "slots_utils",
    "maintainer_group",
    "donation_goal",
    "leaderboard_group",
    "leaderboard_slots_group",
    "holder",
    "sponsor",
    "slots_single_win"
]
