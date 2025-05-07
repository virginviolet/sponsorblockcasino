# region Imports
# Standard library
from typing import Dict, TYPE_CHECKING
from os import getenv

# Third party
from dotenv import load_dotenv

if TYPE_CHECKING:
    from discord import Client

if TYPE_CHECKING:
    # Standard library
    from subprocess import Popen

    # Third-party
    from discord.ext.commands import Bot  # pyright: ignore [reportMissingTypeStubs]

    # Local
    from bot_configuration import BotConfiguration
    from models.checkpoints import ChannelCheckpoints
    from models.grifter_suppliers import GrifterSuppliers
    from models.log import Log
    from models.slot_machine import SlotMachine
    from models.slot_machine_high_scores import SlotMachineHighScores
    from models.transfers_waiting_approval import TransfersWaitingApproval
    from models.message_mining_registry import MessageMiningRegistryManager
    from schemas.data_classes import DonationGoal
    from utils.decrypt_transactions import DecryptedTransactionsSpreadsheet
    from sponsorblockchain.models.blockchain import Blockchain
# endregion

# region Constants
load_dotenv()

DISCORD_TOKEN: str | None = getenv('DISCORD_TOKEN')
# endregion

# region Global variables

# Number of messages to keep track of in each channel
per_channel_checkpoint_limit: int = 3
active_slot_machine_players: Dict[int, float] = {}
starting_bonus_timeout: int = 30
time_zone: str = "Canada/Central"

waitress_process: "Popen[str] | None" = None
log: "Log | None" = None
configuration: "BotConfiguration | None" = None
blockchain: "Blockchain | None" = None
slot_machine: "SlotMachine | None" = None
grifter_suppliers: "GrifterSuppliers | None" = None
transfers_waiting_approval: "TransfersWaitingApproval | None" = None
decrypted_transactions_spreadsheet: (
    "DecryptedTransactionsSpreadsheet | None") = None
message_mining_registry: "MessageMiningRegistryManager | None" = None
slot_machine_high_scores: "SlotMachineHighScores | None" = None
bot: "Bot | None" = None
client: "Client | None" = None

# Bot configuration
coin: str = ""
Coin: str = ""
coins: str = ""
Coins: str = ""
coin_emoji_id: int = 0
coin_emoji_name: str = ""
casino_house_id: int = 0
administrator_id: int = 0
casino_channel_id: int = 0
mining_updates_channel_id = 0
mining_updates_channel_name: str = ""
mining_highlights_channel_id = 0
mining_highlights_channel_name: str = ""
blockchain_name: str = ""
Blockchain_name: str = ""
network_mining_enabled: bool = False
grifter_swap_id: int = 0
sbcoin_id: int = 0
auto_approve_transfer_limit: int = 0
aml_office_channel_id: int = 0
aml_office_thread_id: int = 0
reaction_messages_enabled: bool = False
leaderboard_slots_highest_win_blocked: bool = True
leaderboard_slots_highest_wager_blocked: bool = True
leaderboard_holder_blocked: bool = True

donation_goal: "DonationGoal | None" = None

all_channel_checkpoints: "Dict[int, ChannelCheckpoints]" = {}

about_coin_formatted: str | None = None
leaderboard_slots_single_win_formatted: str | None = None
leaderboard_slots_wager_formatted: str | None = None
donation_goal_formatted: str | None = None

active_slot_machine_players: Dict[int, float] = {}
# endregion
