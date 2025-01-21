import sb_blockchain
import threading
import subprocess
import signal
import asyncio
import json
import pytz
import random
from time import sleep, time
from datetime import datetime
from discord import Intents, Interaction, Member, Message, Client, Emoji, PartialEmoji, User, app_commands
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

# region Checkpoints

class ChannelCheckpoints:
    def __init__(self,
                 guild_name: str,
                 guild_id: int,
                 name: str,
                 id: int,
                 number: int = 10) -> None:
        self.number: int = number
        self.directory: str = (
            f"data/checkpoints/{guild_name}_{guild_id}/{name}_{id}")
        self.file_name: str = f"{self.directory}/channel_checkpoints.json"
        self.entry_count: int = self.count_lines()
        self.last_message_ids: List[Dict[str, int]] | None = self.load()

    def count_lines(self) -> int:
        if not exists(self.file_name):
            return 0
        
        with open(self.file_name, "r") as file:
            count: int = sum(1 for _ in file)
            return count
        
    def create(self) -> None:
        with open(self.file_name, "w"):
            pass

    def save(self, message_id: int) -> None:
        if not exists(self.file_name):
            self.create()

        # print(f"Saving checkpoint: {message_id}")
        with open(self.file_name, "a") as file:
            file.write("\n" + json.dumps({"last_message_id": message_id}))
        self.entry_count += 1
        # self.entry_count = self.count_lines()

        if self.entry_count > self.number:
            self.remove_first_line()
            self.entry_count -= 1

    def remove_first_line(self) -> None:
        with open(self.file_name, "r") as file:
            lines: List[str] = file.readlines()
        with open(self.file_name, "w") as file:
            file.writelines(lines[1:])

    def load(self) -> List[Dict[str, int]] | None:
        if not exists(self.file_name):
            return None

        with open(self.file_name, "r") as file:
            checkpoints: List[Dict[str,int]] | None = []
            for line in file:
                checkpoint: Dict[str, int] = (
                    {k: int(v) for k, v in json.loads(line).items()})
                checkpoints.append(checkpoint)
                return checkpoints


class AllGuildChannelsCheckpoints:
    def __init__(self, guild_checkpoints: Dict[int, GuildCheckpoints] = {}) -> None:
        self.guild_checkpoints: Dict[int, GuildCheckpoints] = guild_checkpoints


class GuildCheckpoints:
    def __init__(self, guild_name: str, guild_id: int, channels: List[Dict[int,str]] = []) -> None:
        self.guild_name: str = guild_name
        self.guild_id: int = guild_id
        self.channels: List[Dict[int, str]] = channels
        self.channel_checkpoints: dict[int, ChannelCheckpoints] = {}

    def start_channel_checkpoints(self) -> None:
        for channel in self.channels:
            channel_id: int = channel["id"]
            channel_name: str = channel["name"]
            channel_checkpoints: ChannelCheckpoints = ChannelCheckpoints(guild_name=self.guild_name, guild_id=self.guild_id, name=channel_name, id=channel_id)
            self.channel_checkpoints[channel_id] = channel_checkpoints


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

# region Bot config
class BotConfiguration:
    def __init__(self, file_name: str = "data/bot_configuration.json") -> None:
        self.file_name: str = file_name
        self.configuration: Dict[str, str] = self.read()
        self.coin: str = self.configuration["COIN"]
        self.coins: str = self.configuration["COINS"]
        self.coin_emoji_id: int = int(self.configuration["COIN_EMOJI_ID"])
        if self.coin_emoji_id == 0:
            print("WARNING: COIN_EMOJI_ID has not set in bot_configuration.json nor "
                  "in the environment variables.")
        self.administrator_id: int = int(self.configuration["ADMINISTRATOR_ID"])
        if self.administrator_id == 0:
            print("WARNING: ADMINISTRATOR_ID has not set in bot_configuration.json nor "
                  "in the environment variables.")

    def create(self) -> None:
        configuration: Dict[str, str] = {
            "COIN": "coin",
            "COINS": "coins",
            "COIN_EMOJI_ID": "0",
            "ADMINISTRATOR_ID": "0"
        }
        with open(self.file_name, "w") as f:
            f.write(json.dumps(configuration))
    
    def read(self) -> Dict[str, str]:
        if not exists(self.file_name):
            self.create()
        
        with open(self.file_name, "r") as f:
            configuration: Dict[str, str] = json.loads(f.read())
            # Override the configuration with environment variables
            if os_environ.get("COIN"):
                configuration["coin"] = os_environ.get("COIN", "")
            if os_environ.get("COINS"):
                configuration["coins"] = os_environ.get("COINS", "")
            if os_environ.get("COIN_EMOJI_ID"):
                configuration["COIN_EMOJI_ID"] = os_environ.get("COIN_EMOJI_ID", "")
            if os_environ.get("ADMINISTRATOR_ID"):
                configuration["ADMINISTRATOR_ID"] = os_environ.get("ADMINISTRATOR_ID", "")
            return configuration
            
            
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

# region CP start

def start_checkpoints():
    all_checkpoints: dict[str, GuildCheckpoints] = {}
    print("Starting checkpoints...")
    channel_id: int = 0
    channel_name: str = ""
    for guild in bot.guilds:
        guild_id: int = guild.id
        guild_name: str = guild.name
        print(f"Guild: {guild_name} ({guild_id})")
        guild_checkpoints: GuildCheckpoints = GuildCheckpoints(guild_name=guild_name, guild_id=guild_id)
        for channel in guild.text_channels:
            channel_id = channel.id
            channel_name = channel.name
            print(f"Channel: {channel_name} ({channel_id})")
            channel_checkpoints: ChannelCheckpoints = ChannelCheckpoints(guild_name=guild_name, guild_id=guild_id, name=channel_name, id=channel_id)
            guild_checkpoints.channel_checkpoints[channel_id] = channel_checkpoints
    print("Checkpoints started.")
    return all_checkpoints


# region Missed msgs


async def process_missed_messages() -> None:
    '''
    Process messages that were sent since the bot was last online.
    This does not process reaction to messages older than the last checkpoint
    (i.e. older than the last message sent before the bot went offline). That
    would require keeping track of every single message and reactions on the
    server in a database.
    '''
    checkpoints: List[Dict[str, int]] | None = checkpoints_machine.last_message_ids
    print(f"Checkpoints: {checkpoints}")
    missed_messages_processed_message: str = "Missed messages processed."
    print("Processing missed messages...")
    if checkpoints is None:
        print("No checkpoints could be loaded.")
    else:
        print(f"Checkpoints loaded: {checkpoints}")

    message_id: int | None = None
    for guild in bot.guilds:
        print(f"Fetching messages from guild: {guild} ({guild.id})...")
        for channel in guild.text_channels:
            print("Fetching messages from "
                  f"channel: {channel} ({channel.id})...")
            async for message in channel.history(limit=None):
                # print(f"{message.author}: {message.content} ({message_id}).")
                if checkpoints is not None:
                    for checkpoint in checkpoints:
                        message_id = message.id
                        # print(f"Checkpoint: {checkpoint}")
                        # input("Press Enter to continue...")
                        # print(f"last_message_id: {checkpoint['last_message_id']}")
                        if message_id == checkpoint["last_message_id"]:
                            print("Checkpoint reached.")
                            print(missed_messages_processed_message)
                            checkpoints_machine.save(message.id)
                            return
                    for reaction in message.reactions:
                        async for user in reaction.users():
                            message_id = message.id
                            # print(f"Reaction found: {reaction.emoji}: {user}.")
                            # print(f"Message ID: {message_id}.")
                            # print(f"{message.author}: {message.content}")
                            sender: Member | User = user
                            receiver: User | Member = message.author
                            emoji: PartialEmoji | Emoji | str = reaction.emoji
                            # await process_reaction(emoji, sender, receiver)
            print(f"Messages from channel {channel.id} ({channel}) fetched.")
        print(f"Messages from guild {guild.id} ({guild}) fetched.")
    if message_id is not None:
        print(f"Saving checkpoint: {message_id}")
        checkpoints_machine.save(message_id)
    else:
        print(f"ERROR: Could not save checkpoint because message_id is None.")
    print(missed_messages_processed_message)

# endregion

# region Process react


async def process_reaction(emoji: PartialEmoji | Emoji | str,
                           sender: Member | User,
                           receiver: Member | User | None = None,
                           receiver_id: int | None = None) -> None:

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
    if emoji_id == COIN_EMOJI_ID:
        
        if receiver is None:
            # Get receiver from id
            if receiver_id is not None:
                receiver = await bot.fetch_user(receiver_id)
            else:
                print("ERROR: Receiver is None.")
                return
        else:
            receiver_id = receiver.id
        
        sender_id: int = sender.id

        print(f"{sender} ({sender_id}) is mining 1 {COIN} "
              f"for {receiver} ({receiver_id})...")
        await add_block_transaction(
            blockchain=blockchain,
            sender = sender,
            receiver = receiver,
            amount=1,
            method="reaction"
        )
    

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
                mined_message: str = (f"{sender} ({sender_id}) mined 1 {COIN} "
                                        f"for {receiver} ({receiver_id}).")
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


async def add_block_transaction(
    blockchain: sb_blockchain.Blockchain,
    sender: Member | User,
    receiver: Member | User,
    amount: int,
    method: str
) -> None:
    sender_id_unhashed: int = sender.id
    receiver_id_unhashed: int = receiver.id
    sender_id_hash: str = (
        sha256(str(sender_id_unhashed).encode()).hexdigest())
    receiver_id_hash: str = (
        sha256(str(receiver_id_unhashed).encode()).hexdigest())
    print("Adding transaction to blockchain...")
    try:
        data: List[Dict[str, sb_blockchain.TransactionDict]] = [{
            "transaction":
                {"sender": sender_id_hash, "receiver": receiver_id_hash, "amount": amount,
                "method": method}
        }]
        data_casted: List[str | Dict[str, sb_blockchain.TransactionDict]] = (
            cast(List[str | Dict[str, sb_blockchain.TransactionDict]], data))
        blockchain.add_block(data=data_casted, difficulty=0)
    except Exception as e:
        print(f"Error adding transaction to blockchain: {e}")
        await terminate_bot()
    print("Transaction added to blockchain.")
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

    print(f"Initializing blockchain...")
    try:
        blockchain = sb_blockchain.Blockchain()
        print(f"Blockchain initialized.")
    except Exception as e:
        print(f"Error initializing blockchain: {e}")
        print("This script will be terminated.")
        sys_exit(1)
# endregion

# region Init
print("Starting bot...")

print("Loading bot configuration...")
configuration = BotConfiguration()
COIN: str = configuration.coin
COINS: str = configuration.coins
COIN_EMOJI_ID: int = configuration.coin_emoji_id
ADMINISTRATOR_ID: int = configuration.administrator_id
print("Bot configuration loaded.")

print("Initializing log...")
log = Log(time_zone="Canada/Central")
print("Log initialized.")

print("Loading checkpoint...")
checkpoints_machine = ChannelCheckpoints(number=2)
print("Checkpoint loaded.")

@bot.event
async def on_ready() -> None:
    print("Bot started.")

    global channel_checkpoints
    channel_checkpoints: Dict[str, ChannelCheckpoints] = start_checkpoints()

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
    guild_id: int = message.guild.id
    channel_id: int = message.channel.id
    channel_checkpoints{}
    checkpoints_machine.save(guild=guild_id, channel=channel_id, message_id=message.id)
# endregion


# region Reaction
@bot.event
async def on_raw_reaction_add(payload: RawReactionActionEvent) -> None:
    # TODO Add "if reaction.message.author.id != user.id" to prevent self-mining
    # `payload` is an instance of the RawReactionActionEvent class from the
    # discord.raw_models module that contains the data of the reaction event.
    if payload.guild_id is None:
        return

    if payload.event_type == "REACTION_ADD":
        if payload.message_author_id is None:
            return
        if payload.emoji.id is None:
            return
        sender: Member | None = payload.member
        if sender is None:
            print("ERROR: Sender is None.")
            return
        receiver_user_id: int = payload.message_author_id
        await process_reaction(emoji=payload.emoji,
                               sender=sender,
                               receiver_id=receiver_user_id)
# endregion


@bot.tree.command(name="transfer",
                  description=f"Transfer {COINS} to another user")
@app_commands.describe(amount=f"Amount of {COINS} to transfer",
                       user=f"User to transfer the {COINS} to")
async def transfer(interaction: Interaction, amount: int, user: Member) -> None:
    """
    Transfer a specified amount of coins to another user.

    Args:
        interaction (Interaction): The interaction object representing the
        command invocation.
    """
    sender: User | Member = interaction.user
    sender_id: int = sender.id
    receiver: Member = user
    receiver_id: int = receiver.id
    print(f"User {sender_id} is requesting to transfer {amount} {COINS} to "
          f"user {receiver_id}...")
    balance: int | None = None
    try:
        balance = blockchain.get_balance(user_unhashed=sender_id)
    except Exception as e:
        print(f"Error getting balance for user {sender} ({sender_id}): {e}")
        administrator: str = (await bot.fetch_user(ADMINISTRATOR_ID)).mention
        await interaction.response.send_message("Error getting balance."
                                                f"{administrator} pls fix.")
    if balance is None:
        print(f"Balance is None for user {sender} ({sender_id}).")
        await interaction.response.send_message(f"You have 0 {COINS}.")
        return
    if balance < amount:
        print(f"{sender} ({sender_id}) does not have enough {COINS} to "
              f"transfer {amount} to {sender} ({sender_id}). "
              f"Balance: {balance}.")
        await interaction.response.send_message(f"You do not have enough "
                                                f"{COINS}. You have {balance} "
                                                f"{COINS}.")
        return
    await add_block_transaction(
        blockchain=blockchain,
        sender=sender,
        receiver=receiver,
        amount=amount,
        method="transfer"
    )
    last_block: sb_blockchain.Block | None = blockchain.get_last_block()
    if last_block is None:
        print("ERROR: Last block is None.")
        administrator: str = (await bot.fetch_user(ADMINISTRATOR_ID)).mention
        await interaction.response.send_message("Error transferring coins. "
                                                f"{administrator} pls fix.")
        await terminate_bot()
    timestamp: float = last_block.timestamp
    log.log(line=f"{sender} ({sender_id}) transferred {amount} {COINS} "
            f"to {receiver} ({receiver_id}).",
                timestamp=timestamp)
    await interaction.response.send_message(f"{sender.mention} transferred "
                                            f"{amount} {COINS} "
                                            f"to {receiver.mention}.")

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
                                                f"{COINS}.")
    elif balance == 1:
        await interaction.response.send_message(f"{user_to_check} has 1 "
                                                f"{COIN}.")
    else:
        await interaction.response.send_message(f"{user_to_check} has "
                                                f"{balance} {COINS}.")

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

# TODO Prevent self-mining
# TODO Track reaction removals
# TODO Add "hide" parameters to commands
# TODO Add transfer command
# TODO Add gamble command
# TODO Add help command

# region Main
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN is not set in the environment variables.")
# endregion
