# region Imports
# Standard library
from typing import List

# Third party
from discord import app_commands
from discord.app_commands import AppCommand
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
from models.checkpoints import start_checkpoints
from utils.missed_messages import process_missed_messages
# endregion

# region On ready
# assert bot is not None, "bot has not been initialized."
assert isinstance(g.bot, Bot), "g.bot has not been initialized."


@g.bot.event
async def on_ready() -> None:
    """
    Event handler that is called when the bot is ready.
    This function performs the following actions:
    - Prints a message indicating that the bot has started.
    - Initializes global checkpoints for all channels.
    - Attempts to sync the bot's commands with Discord and prints the result.
    If an error occurs during the command sync process, it catches the exception
    and prints an error message.
    """
    assert isinstance(g.bot, Bot), "g.bot has not been initialized."
    print("Bot started.")
    g.all_channel_checkpoints = (
        await start_checkpoints(limit=g.per_channel_checkpoint_limit))
    await process_missed_messages(limit=50)

    # global guild_ids
    # guild_ids = load_guild_ids()
    # print(f"Guild IDs: {guild_ids}")
    for guild in g.bot.guilds:
        print(f"- {guild.name} ({guild.id})")

    # Sync the commands to Discord
    print("Syncing global commands...")
    try:
        global_commands: List[app_commands.AppCommand] = await g.bot.tree.sync()
        print(f"Synced commands for bot {g.bot.user}.")
        print(f"Fetching command IDs...")
        about_command: AppCommand | None = None
        command_name: str
        for command in global_commands:
            command_name = command.name
            if command_name == f"about_{g.coin.lower()}":
                about_command = command
                break
        print("Command IDs fetched.")

        if about_command is None:
            print("ERROR: Could not find the about command. "
                  "Using string instead.")
            g.about_command_formatted = f"about_{g.coin.lower()}"
        else:
            g.about_command_formatted = about_command.mention
        print(f"Bot is ready!")
    except Exception as e:
        raise Exception(f"ERROR: Error syncing commands: {e}")
# endregion
