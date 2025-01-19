import sb_blockchain
import threading
import subprocess
import signal
import asyncio
import json
import pytz
from time import sleep, time
from datetime import datetime
from discord import Intents, Interaction, Member, Message, Client, Emoji, PartialEmoji, app_commands
from discord.ext import commands
from discord.raw_models import RawReactionActionEvent
from os import environ as os_environ, getenv
from os.path import exists
from dotenv import load_dotenv
from hashlib import sha256
from sys import exit as sys_exit
from typing import Dict, List, NoReturn, TextIO, cast


# region Variables
# Intents and bot setup
intents: Intents = Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot("!", intents=intents)
client = Client(intents=intents)
# Load .env file for the bot DISCORD_TOKEN
load_dotenv()
DISCORD_TOKEN: str | None = getenv('DISCORD_TOKEN')
# endregion

# region LastMessageId


class LastMessageId:
    def __init__(self, file_name: str = "data/bot_checkpoint.json") -> None:
        self.file_name: str = file_name
        self.last_message_id: int = self.read()

    def create(self) -> None:
        with open(self.file_name, "w") as f:
            f.write(json.dumps({"last_message_id": 0}))

    def save(self, message_id: int) -> None:
        if not exists(self.file_name):
            self.create()

        print(f"Saving checkpoint: {message_id}")
        with open(self.file_name, "w") as f:
            f.write(json.dumps({"last_message_id": message_id}))

    def read(self) -> int:
        if not exists(self.file_name):
            self.create()

        with open(self.file_name, "r") as f:
            message_id_str: str = json.loads(f.read())["last_message_id"]
            message_id_int: int = int(message_id_str)
            return message_id_int
# endregion

# region Log


class Log:
    '''
    The log cannot currently be verified or generated from the blockchain.
    Use a validated transactions file for verification (see 
    Blockchain.validate_transactions_file()).
    The log is meant to be a local record of events.
    '''

    def __init__(self,
                 file_name: str = "data/transactions.log",
                 time_zone: str | None = None) -> None:
        self.file_name: str = file_name
        self.time_zone: str | None = time_zone
        timestamp: float = time()
        if time_zone is not None:
            self.log(f"The time zone is set to '{time_zone}'.", timestamp)
        else:
            self.log("The time zone is set to the local time zone.", timestamp)

    def create(self) -> None:
        with open(self.file_name, "w"):
            pass

    def log(self, line: str, timestamp: float) -> None:
        if self.time_zone is None:
            # Use local time zone
            timestamp_friendly = (
                datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"))
        else:
            # Convert Unix timestamp to datetime object
            timestamp_dt: datetime = (
                datetime.fromtimestamp(timestamp, pytz.utc))

            # Adjust for time zone
            timestamp_dt = (
                timestamp_dt.astimezone(pytz.timezone(self.time_zone)))

            # Format the timestamp
            timestamp_friendly: str = (
                timestamp_dt.strftime("%Y-%m-%d %H:%M:%S"))

        # Create the log file if it doesn't exist
        if not exists(self.file_name):
            self.create()

        with open(self.file_name, "a") as f:
            timestamped_line: str = f"{timestamp_friendly}: {line}"
            print(timestamped_line)
            f.write(f"{timestamped_line}\n")


# endregion

# region Flask funcs


def start_flask_app_waitress() -> None:
    global waitress_process

    def stream_output(pipe: TextIO, prefix: str) -> None:
        # Receive output from the Waitress subprocess
        for line in iter(pipe.readline, ''):
            # print(f"{prefix}: {line}", end="")
            print(f"{line}", end="")
        if hasattr(pipe, 'close'):
            pipe.close()

    print("Starting Flask app with Waitress...")
    program = "waitress-serve"
    app_name = "sb_blockchain"
    host = "*"
    # Use the environment variable or default to 8000
    port: str = os_environ.get("PORT", "8080")
    command: List[str] = [
        program,
        f"--listen={host}:{port}",
        f"{app_name}:app"
    ]
    waitress_process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Flask app started with Waitress.")

    # Start threads to read output from the subprocess
    threading.Thread(
        target=stream_output,
        args=(waitress_process.stdout, "STDOUT"),
        daemon=True
    ).start()
    threading.Thread(
        target=stream_output,
        args=(waitress_process.stderr, "STDERR"),
        daemon=True
    ).start()


def start_flask_app() -> None:
    # For use with the Flask development server
    print("Starting flask app...")
    try:
        sb_blockchain.app.run(port=5000, debug=True, use_reloader=False)
    except Exception as e:
        print(f"Error running Flask app: {e}")
# endregion

# region Missed msgs


async def process_missed_messages() -> None:
    '''
    Process messages that were sent since the bot was last online.
    This does not process reaction to messages older than the last checkpoint
    (i.e. older than the last message sent before the bot went offline). That
    would require keeping track of every single message and reactions on the
    server in a database.
    '''
    global last_message_checkpointer
    last_message_id: int = int(last_message_checkpointer.read())
    checkpoint_found: bool = False
    missed_messages_processed_message: str = "Missed messages processed."
    print("Processing missed messages...")
    if last_message_id == 0:
        print("No checkpoint found.")
        checkpoint_found = False
    else:
        print(f"Checkpoint found: {last_message_id}")
        checkpoint_found = True

    message_id: int | None = None
    for guild in bot.guilds:
        print(f"Fetching messages from guild: {guild} ({guild.id})...")
        for channel in guild.text_channels:
            print("Fetching messages from "
                  f"channel: {channel} ({channel.id})...")
            async for message in channel.history(limit=None):
                if checkpoint_found and message.id == last_message_id:
                    print("Checkpoint reached.")
                    print(missed_messages_processed_message)
                    last_message_checkpointer.save(message.id)
                    return
                # print(f"{message.author}: {message.content}")
                for reaction in message.reactions:
                    async for user in reaction.users():
                        message_id = message.id
                        print(f"Reaction found: {reaction.emoji}: {user}.")
                        print(f"Message ID: {message_id}.")
                        print(f"{message.author}: {message.content}")
                        sender_id: int = user.id
                        receiver_id: int = message.author.id
                        emoji: PartialEmoji | Emoji | str = reaction.emoji
                        await process_reaction(emoji, sender_id, receiver_id)
            print(f"Messages from channel {channel.id} ({channel}) fetched.")
        print(f"Messages from guild {guild.id} ({guild}) fetched.")
    if not checkpoint_found and message_id is not None:
        last_message_checkpointer.save(message_id)
    print(missed_messages_processed_message)

# endregion

# region Process react


async def process_reaction(emoji: PartialEmoji | Emoji | str,
                           sender_user_id: int,
                           receiver_user_id: int) -> None:

    emoji_id: int | str | None = 0

    match emoji:
        case Emoji():
            emoji_id = emoji.id
        case PartialEmoji() if emoji.id is not None:
            emoji_id = emoji.id
        case PartialEmoji():
            return
        case str():
            return
    if emoji_id == sbcoin_emoji_id:
        print(f"{sender_user_id} is mining 1 SBCoin "
              f"for {receiver_user_id}...")
        print("Adding transaction to blockchain...")
        try:
            sender_user_id_hash: str = (
                sha256(str(sender_user_id).encode()).hexdigest())
            receiver_user_id_hash: str = sha256(
                str(receiver_user_id).encode()).hexdigest()
            add_block_transaction(
                blockchain=blockchain,
                sender=sender_user_id_hash,
                receiver=receiver_user_id_hash,
                amount=1,
                method="reaction"
            )
            print("Transaction added to blockchain.")
        except Exception as e:
            print(f"Error adding transaction to blockchain: {e}")
            await terminate_bot()

        # Log the mining
        block_retrieval_success: bool | None = None
        last_block_timestamp: float | None = None
        try:
            # Get the last block's timestamp for logging
            last_block: None | sb_blockchain.Block = blockchain.get_last_block()
            if last_block is not None:
                last_block_timestamp = last_block.timestamp
                del last_block
            else:
                block_retrieval_success = False
        except Exception as e:
            print(f"Error getting last block: {e}")
            block_retrieval_success = False
        if block_retrieval_success is False:
            await terminate_bot()

        try:
            if last_block_timestamp is not None:
                mined_message: str = (f"{sender_user_id} mined "
                                      "1 SBCoin for "
                                      f"{receiver_user_id}.")
                log.log(line=mined_message, timestamp=last_block_timestamp)
        except Exception as e:
            print(f"Error logging mining: {e}")
            await terminate_bot()

        chain_validity: bool | None = None
        try:
            print("Validating blockchain...")
            chain_validity = blockchain.is_chain_valid()
        except Exception as e:
            # TODO Revert blockchain to previous state
            print(f"Error validating blockchain: {e}")
            chain_validity = False

        if chain_validity is False:
            await terminate_bot()
# endregion

# region Add tx


def add_block_transaction(
    blockchain: sb_blockchain.Blockchain,
    sender: str,
    receiver: str,
    amount: int,
    method: str
) -> None:
    data: List[Dict[str, sb_blockchain.TransactionDict]] = [{
        "transaction":
            {"sender": sender, "receiver": receiver, "amount": amount,
             "method": method}
    }]
    data_casted: List[str | Dict[str, sb_blockchain.TransactionDict]] = (
        cast(List[str | Dict[str, sb_blockchain.TransactionDict]], data))
    blockchain.add_block(data=data_casted, difficulty=0)
# endregion

# region Terminate bot


async def terminate_bot() -> NoReturn:
    print("Closing bot...")
    await bot.close()
    print("Bot closed.")
    print("Shutting down the blockchain app...")
    waitress_process.send_signal(signal.SIGTERM)
    waitress_process.wait()
    """ print("Shutting down blockchain flask app...")
    try:
        requests.post("http://127.0.0.1:5000/shutdown")
    except Exception as e:
        print(e) """
    await asyncio.sleep(1)  # Give time for all tasks to finish
    print("The script will now exit.")
    sys_exit(1)
# endregion

# region Flask
if __name__ == "__main__":
    print("Starting blockchain flask app thread...")
    try:
        flask_thread = threading.Thread(target=start_flask_app_waitress)
        flask_thread.daemon = True  # Set the thread as a daemon thread
        flask_thread.start()
        print("Flask app thread started.")
    except Exception as e:
        print(f"Error starting Flask app thread: {e}")
    sleep(1)
# endregion

# region Init
print("Starting bot...")


@bot.event
async def on_ready() -> None:
    global sbcoin_emoji_id
    sbcoin_emoji_id = 1032063250478661672
    print("Bot started.")

    print(f"Initializing blockchain...")
    global blockchain
    try:
        blockchain = sb_blockchain.Blockchain()
        print(f"Blockchain initialized.")
    except Exception as e:
        print(f"Error initializing blockchain: {e}")
        return

    print("Initializing log...")
    global log
    log = Log(time_zone="Canada/Central")
    print("Log initialized.")

    print("Loading checkpoint...")
    global last_message_checkpointer
    last_message_checkpointer = LastMessageId()
    print("Checkpoint loaded.")

    await process_missed_messages()

    # Sync the commands to Discord
    print("Syncing commands...")
    try:
        await bot.tree.sync()
        print(f"Synced commands for bot {bot.user}.")
        print(f"Bot is ready!")
    except Exception as e:
        print(f"Error syncing commands: {e}")
# endregion


# region Message
@bot.event
async def on_message(message: Message) -> None:
    global last_message_checkpointer
    last_message_checkpointer.save(message.id)
# endregion


# region Reaction
@bot.event
async def on_raw_reaction_add(payload: RawReactionActionEvent) -> None:
    # TODO Add "if reaction.message.author.id != user.id" to prevent self-mining
    # `payload` is an instance of the RawReactionActionEvent class from the
    # discord.raw_models module that contains the data of the reaction event.
    global blockchain
    global sbcoin_emoji_id
    if payload.guild_id is None:
        return

    if payload.event_type == "REACTION_ADD":
        if payload.message_author_id is None:
            return
        if payload.emoji.id is None:
            return
        sender_user_id: int = payload.user_id
        receiver_user_id: int = payload.message_author_id
        await process_reaction(payload.emoji, sender_user_id, receiver_user_id)
# endregion

# region Balance


@bot.tree.command(name="balance", description="Check your balance")
@app_commands.describe(user="User to check the balance")
async def balance(interaction: Interaction, user: Member | None = None) -> None:
    """
    Check the balance of a user. If no user is specified, the balance of the
    user who invoked the command is checked.

    Args:
        interaction (Interaction): The interaction object representing the
        command invocation.

        user (str, optional): The user to check the balance. Defaults to None.
    """
    global blockchain
    user_to_check: Member | str
    if user is None:
        user_to_check = interaction.user.mention
        user_id: int = interaction.user.id
    else:
        user_to_check = user.mention
        user_id: int = user.id

    user_id_hash: str = sha256(str(user_id).encode()).hexdigest()
    balance: int | None = blockchain.get_balance(user=user_id_hash)
    if balance is None:
        await interaction.response.send_message(f"{user_to_check} has 0 "
                                                "SBCoins.")
    elif balance == 1:
        await interaction.response.send_message(f"{user_to_check} has 1 "
                                                "SBCoin.")
    else:
        await interaction.response.send_message(f"{user_to_check} has "
                                                f"{balance} SBCoins.")


# region Message
# Example slash command

@bot.tree.command(name="ping", description="Replies with Pong!")
async def ping(interaction: Interaction) -> None:
    """
    Replies with Pong! The response is visible only to the user who invoked the
    command.

    Args:
        interaction (Interaction): The interaction object representing the
        command invocation.
    """
    await interaction.response.send_message("Pong!", ephemeral=True)
# endregion

# TODO Track reaction removals
# TODO Add hide parameters to commands
# TODO Add transfer command
# TODO Add gamble command
# TODO Add help command

# region Main
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN is not set in the environment variables.")
# endregion
