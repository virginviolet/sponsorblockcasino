"""
Command modules for the SBCoin Nightclub bot.
This package contains all the slash commands available in the bot.
"""
from .leaderboard import (leaderboard_group, leaderboard_slots_group, holder,
                          slots_single_win, sponsor)
from .maintainer import (
    maintainer_group,
    maintainer_donation_goal_group,
    aml_group,
    reels,  # pyright: ignore [reportUnknownVariableType]
    approve,  # pyright: ignore [reportUnknownVariableType]
    block_receivals,  # pyright: ignore [reportUnknownVariableType]
    decrypt_spreadsheet,  # pyright: ignore [reportUnknownVariableType]
    maintainer_donation_goal)
from .mining import mining_group, mining_stats, mining_settings
from .slots import slots_group, insert_coins, show_help, jackpot, reboot, rtp, slots_utils
from .about_coin import about_coin
from .balance import balance
from .donation_goal import donation_goal
from .transfer import transfer

__all__: list[str] = [
    # .leaderboard
    "leaderboard_group",
    "leaderboard_slots_group",
    "holder",
    "sponsor",
    "slots_single_win",

    # .maintainer
    "maintainer_group",
    "maintainer_donation_goal_group",
    "aml_group",
    "maintainer_donation_goal",
    "reels",
    "approve",
    "block_receivals",
    "decrypt_spreadsheet",

    # .mining
    "mining_settings",
    "mining_stats",
    "mining_group",

    # .slots
    "slots_group",
    "insert_coins",
    "show_help",
    "jackpot",
    "reboot",
    "rtp",
    "slots_utils",

    # .about_coin
    "about_coin",

    # .balance
    "balance",

    # .donation_goal
    "donation_goal",

    # .transfer
    "transfer"
]
