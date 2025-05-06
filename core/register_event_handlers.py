# region Imports
# Third party
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)

# Local
import core.global_state as g
from commands.maintainer.maintainer_main import maintainer_group
from commands.slots.slots_main import slots_group
from commands.mining.mining_main import mining_group
from commands.leaderboard.leaderboard_main import leaderboard_group
from event_handlers.on_ready import on_ready
from event_handlers.message import on_message
from event_handlers.reaction import on_raw_reaction_add
# endregion

# region Events
def register_event_handlers() -> None:
    """
    Registers all event handlers for the bot.
    """
    print("Registering event handlers...")
    assert isinstance(g.bot, Bot), "bot has not been initialized."
    g.bot.event(on_ready)
    g.bot.event(on_message)
    g.bot.event(on_raw_reaction_add)
    print("Event handlers registered.")
# endregion

# region Commands
def register_commands() -> None:
    """
    Registers all commands for the bot.
    """
    print("Registering commands...")
    assert isinstance(g.bot, Bot), "bot is not initialized"
    
    # Command groups
    g.bot.tree.add_command(leaderboard_group)
    g.bot.tree.add_command(maintainer_group)
    g.bot.tree.add_command(mining_group)
    g.bot.tree.add_command(slots_group)
    print("Commands registered.")
# endregion