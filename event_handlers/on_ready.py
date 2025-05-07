# region Imports
# Standard library
from typing import List

# Third party
from discord import app_commands
from discord.app_commands import AppCommand, AppCommandGroup, Argument
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)

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
    If an error occurs during the command sync process, it catches the
    exception and prints an error message.
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
        global_commands: List[app_commands.AppCommand] = (
            await g.bot.tree.sync())
        print(f"Synced commands for bot {g.bot.user}.")
        print(f"Fetching command IDs...")
        about_command: AppCommand | None = None
        leaderboard_slots_single_win: AppCommandGroup | None = None
        leaderboard_slots_highest_wager: AppCommandGroup | None = None
        leaderboard_command_group: app_commands.AppCommand | None = None
        command_name: str
        for command in global_commands:
            command_name = command.name
            if command_name == f"about_{g.coin.lower()}":
                about_command = command
            elif command_name == "leaderboard":
                leaderboard_command_group = command
            if (about_command is not None and
                    leaderboard_command_group is not None):
                break
        if leaderboard_command_group is None:
            print("ERROR: Could not find the leaderboard command group.")
        else:
            leaderboard_command_options: List[Argument | AppCommandGroup] = (
                leaderboard_command_group.options)
            slots_command_options: List[Argument |
                                        AppCommandGroup] | None = None
            for command_option in leaderboard_command_options:
                if isinstance(command_option, AppCommandGroup):
                    command_name: str = command_option.name
                    if command_name == "slots":
                        slots_command_options = command_option.options
                        break
            if slots_command_options is None:
                print("ERROR: "
                      "Could not find the leaderboard slots command group.")
            else:
                for command_option in slots_command_options:
                    if isinstance(command_option, AppCommandGroup):
                        command_name: str = (
                            command_option.name)
                        if command_name == "single_win":
                            leaderboard_slots_single_win = command_option
                        elif (command_name == "stake" or
                              command_name == "highest_stake"):
                            leaderboard_slots_highest_wager = command_option
                        if (leaderboard_slots_single_win is not None and
                                leaderboard_slots_highest_wager is not None):
                            break
                    if (leaderboard_slots_single_win is not None and
                            leaderboard_slots_highest_wager is not None):
                        break
        print("Command IDs fetched.")

        if about_command is None:
            print("ERROR: Could not find the about command. "
                  "Using string instead.")
            g.about_command_formatted = f"about_{g.coin.lower()}"
        else:
            g.about_command_formatted = about_command.mention

        if leaderboard_slots_single_win is None:
            print("ERROR: Could not find the leaderboard slots "
                  "highest win command. Using string instead.")
            g.leaderboard_slots_single_win_formatted = (
                "/leaderboard slots single_win")
        else:
            g.leaderboard_slots_single_win_formatted = (
                leaderboard_slots_single_win.mention)

        if leaderboard_slots_highest_wager is None:
            print("ERROR: Could not find the leaderboard slots "
                  "highest wager command. Using string instead.")
            g.leaderboard_slots_wager_formatted = (
                "/leaderboard slots highest_stake")
        else:
            g.leaderboard_slots_wager_formatted = (
                leaderboard_slots_highest_wager.mention)

        print(f"Bot is ready!")
    except Exception as e:
        raise Exception(f"ERROR: Error syncing commands: {e}")
# endregion
