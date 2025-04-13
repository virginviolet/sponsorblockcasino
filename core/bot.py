# region Imports
# Standard library
import core.global_state as g
from sys import exit as sys_exit

# Third party
from discord import Intents, Client
from discord.ext import commands
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
from bot_configuration import invoke_bot_configuration
from models.grifter_suppliers import GrifterSuppliers
from models.log import Log
from models.message_mining_registry import MessageMiningRegistryManager
from models.slot_machine import SlotMachine
from models.transfers_waiting_approval import TransfersWaitingApproval
from utils.decrypt_transactions import DecryptedTransactionsSpreadsheet
# FIXME blockchain gets defined both here and in the waitress thread
from sponsorblockchain.sponsorblockchain_main import blockchain
# endregion

# region Bot setup
print("Starting bot...")
intents: Intents = Intents.default()
intents.message_content = True
intents.members = True
g.bot = commands.Bot(command_prefix="!", intents=intents)
g.client = Client(intents=intents)
# endregion

# region Bot environment


def setup_bot_environment() -> None:
    print("Setting up bot environment...")
    try:
        print(f"Initializing blockchain...")
        g.blockchain = blockchain
        print(f"Blockchain initialized.")
    except Exception as e:
        print(f"ERROR: Error initializing blockchain: {e}")
        print("This script will be terminated.")
        sys_exit(1)

    invoke_bot_configuration()

    print("Starting class instances...")
    g.log = Log(time_zone=g.time_zone)
    g.message_mining_registry = MessageMiningRegistryManager()
    g.slot_machine = SlotMachine()
    g.transfers_waiting_approval = TransfersWaitingApproval()
    g.grifter_suppliers = GrifterSuppliers()
    g.decrypted_transactions_spreadsheet = (
        DecryptedTransactionsSpreadsheet(time_zone=g.time_zone))
    print("Class instances started.")
    print("Bot environment set up.")
# endregion

# region Run bot
def run_bot() -> None:
    print("Running bot...")
    assert isinstance(g.bot, Bot), (
        "bot must be initialized before running the bot.")
    DISCORD_TOKEN: str | None = g.DISCORD_TOKEN
    if DISCORD_TOKEN is not None:
        print("Discord token found.")
        g.bot.run(DISCORD_TOKEN)
    else:
        error_message: str = ("ERROR: DISCORD_TOKEN is not set "
                              "in the environment variables.")
        raise ValueError(error_message)
# endregion
