# region Imports
import core.global_state as global_state
from discord import (Intents, Client)
from discord.ext import commands
from discord.ext.commands import Bot  # type: ignore
from sys import exit as sys_exit
from core.global_state import time_zone
from blockchain.models.blockchain import Blockchain
from models.grifter_suppliers import GrifterSuppliers
from models.slot_machine import SlotMachine
from models.transfers_waiting_approval import TransfersWaitingApproval
from models.log import Log
from bot_configuration import invoke_bot_configuration
from utils.decrypt_transactions import DecryptedTransactionsSpreadsheet
# endregion

# region Bot setup
print("Starting bot...")
intents: Intents = Intents.default()
intents.message_content = True
intents.members = True
global_state.bot = commands.Bot(command_prefix="!", intents=intents)
client = Client(intents=intents)
# endregion

# region Bot environment


def setup_bot_environment() -> None:
    global coin
    global slot_machine, grifter_suppliers, transfers_waiting_approval, log
    global blockchain
    print("Setting up bot environment...")
    try:
        print(f"Initializing blockchain...")
        global_state.blockchain = Blockchain()
        print(f"Blockchain initialized.")
    except Exception as e:
        print(f"ERROR: Error initializing blockchain: {e}")
        print("This script will be terminated.")
        sys_exit(1)

    invoke_bot_configuration()

    print("Starting class instances...")
    global_state.log = Log(time_zone=time_zone)
    global_state.slot_machine = SlotMachine()
    global_state.transfers_waiting_approval = TransfersWaitingApproval()
    global_state.grifter_suppliers = GrifterSuppliers()
    global_state.decrypted_transactions_spreadsheet = (
        DecryptedTransactionsSpreadsheet(time_zone=time_zone))
    print("Class instances started.")
    print("Bot environment set up.")


# endregion

# region Run bot
def run_bot() -> None:
    print("Running bot...")
    assert isinstance(global_state.bot, Bot), (
        "bot must be initialized before running the bot.")
    DISCORD_TOKEN: str | None = global_state.DISCORD_TOKEN
    if DISCORD_TOKEN is not None:
        print("Discord token found.")
        global_state.bot.run(DISCORD_TOKEN)
    else:
        error_message: str = ("ERROR: DISCORD_TOKEN is not set "
                              "in the environment variables.")
        raise ValueError(error_message)
# endregion
