"""
Scopes:
- applications.commands
- bot

Permissions:
- Send Messages
- Read Message History

Privileged Gateway Intents:
- Server Members Intent
- Message Content Intent
"""

# region Imports
# from pathlib import Path
# from os.path import exists, basename
# import os
# import pandas as pd
# import threading
# import subprocess
# import signal
# import asyncio
# import json
# import pytz
# import random
# import math
# from builtins import open
# from time import sleep, time
# from datetime import datetime
# from humanfriendly import format_timespan
# from discord import (Guild, Intents, Interaction, Member, Message, Client,
#                      Emoji, MessageInteraction, PartialEmoji, Role, User,
#                      TextChannel, VoiceChannel, app_commands, utils,
#                      CategoryChannel, ForumChannel, StageChannel, DMChannel,
#                      GroupChannel, Thread, AllowedMentions, InteractionMessage,
#                      File)
# from discord.app_commands import AppCommand
# from discord.abc import PrivateChannel
# from discord.ui import View, Button, Item
# from discord.raw_models import RawReactionActionEvent
# from discord.utils import MISSING
# from discord.ext.commands import Bot  # type: ignore
# from discord.ext import commands
# from os import environ as os_environ, getenv, makedirs
# from os.path import exists
# from dotenv import load_dotenv
# from hashlib import sha256
# from sys import exit as sys_exit
# from sympy import (symbols, Expr, Add, Mul, Float, Integer, Eq, Lt, Ge, Gt,
#                    Rational, simplify, Piecewise, pretty)
# from _collections_abc import dict_items
# from typing import (Dict, KeysView, List, LiteralString, NoReturn, TextIO, cast,
#                     Literal, Any)
# from type_aliases import (BotConfig, Reels, ReelSymbol,
#                           ReelResult, ReelResults,
#                           SpinEmojis, SlotMachineConfig,
#                           SaveData, TransactionRequest, T)
# from core.global_state import bot, waitress_process, coin, Coin, coins, Coins, coin_emoji_id, coin_emoji_name, casino_house_id, administrator_id, casino_channel_id, blockchain_name, Blockchain_name, about_command_mention, grifter_swap_id, sbcoin_id, log, blockchain, active_slot_machine_players, all_channel_checkpoints
# import blockchain.sbchain as sbchain
# from core.bot import run_bot, setup_bot_environment, bot, intents, client
# from utils.get_project_root import get_project_root
# import core.global_state as global_state
# per_channel_checkpoint_limit, active_slot_machine_players, starting_bonus_timeout, waitress_process, log, blockchain, coin, Coin, coins, Coins, coin_emoji_id, coin_emoji_name, casino_house_id, administrator_id, casino_channel_id, blockchain_name, Blockchain_name, about_command_mention, grifter_swap_id, sbcoin_id = global_state.get_variables()
# endregion

# region Imports
# import core.global_state  # type: ignore
from core.register_event_handlers import (register_event_handlers,
                                          register_commands)
from blockchain.models.blockchain import Blockchain
from blockchain.start_sbchain import start_flask_app_thread
from core.bot import setup_bot_environment, run_bot
# endregion

if __name__ == "__main__":
    setup_bot_environment()
    run_bot()
    register_event_handlers()
    register_commands()
    start_flask_app_thread()
    blockchain = Blockchain()

# TODO Track reaction removals
# TODO Make leaderboard
# TODO Add casino jobs
# TODO Add more games
