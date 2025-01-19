import sb_blockchain
import threading
import subprocess
import signal
import asyncio
from time import sleep
from discord import Intents, Interaction, Member, Message, Client, Reaction, User, Emoji, PartialEmoji, app_commands
from discord.ext import commands
from os import environ as os_environ, getenv
from dotenv import load_dotenv
from hashlib import sha256
from sys import exit as sys_exit
from typing import Dict, List, NoReturn, TextIO, cast

# region Functions


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

print("Starting bot...")

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


@bot.event
async def on_ready() -> None:
    # region Init
    print("Bot started.")
    print(f"Initializing blockchain...")
    global blockchain
    try:
        blockchain = sb_blockchain.Blockchain()
        print(f"Blockchain initialized.")
    except Exception as e:
        print(f"Error initializing blockchain: {e}")
        return
    # Sync the commands to Discord
    print("Syncing commands...")
    try:
        await bot.tree.sync()
        print(f"Synced commands for bot {bot.user}.")
        print(f"Bot is ready!")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    # endregion

# region Reaction


@bot.event
async def on_reaction_add(reaction: Reaction, user: User) -> None:
    # TODO Add "if reaction.message.author.id != user.id" to prevent self-mining
    global blockchain
    SBCOIN_EMOJI_ID = 1032063250478661672
    SENDER_USER_ID: int = user.id
    RECEIVER_USER_ID: int = reaction.message.author.id
    SENDER_USER_ID_HASH: str = sha256(str(SENDER_USER_ID).encode()).hexdigest()
    RECEIVER_USER_ID_HASH: str = sha256(
        str(RECEIVER_USER_ID).encode()).hexdigest()
    reaction_emoji: PartialEmoji | Emoji | str = reaction.emoji
    reaction_emoji_id: int | str | None = 0
    match reaction_emoji:
        case Emoji():
            reaction_emoji_id = reaction_emoji.id
        case PartialEmoji() if reaction_emoji.id is not None:
            reaction_emoji_id = reaction_emoji.id
        case PartialEmoji():
            return
        case str():
            return
    if reaction_emoji_id == SBCOIN_EMOJI_ID:
        print(f"{reaction.message.author.name} mined 1 SBCoin for {user.name}.")
        print("Adding transaction to blockchain...")
        try:
            add_block_transaction(
                blockchain=blockchain,
                sender=SENDER_USER_ID_HASH,
                receiver=RECEIVER_USER_ID_HASH,
                amount=1,
                method="reaction"
            )
            print("Transaction added to blockchain.")
            print("Validating blockchain...")
            chain_validity: bool = blockchain.is_chain_valid()
            if chain_validity is False:
                # TODO Revert blockchain to previous state
                print(f"Error validating blockchain. Shutting down bot.")
                await terminate_bot()

        except Exception as e:
            print(f"Error adding transaction to blockchain: {e}")

    # This must be at the end to process commands
    await bot.process_commands(reaction.message)
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
    else:
        user_to_check = user.mention

    user_id: int = interaction.user.id
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

# TODO Add logging
# TODO Add send command
# TODO Add gamble command
# TODO Add help command

# region Main
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN is not set in the environment variables.")
# endregion
