# region Imports
# Third party
from discord.ext.commands import Bot  # type: ignore

# Local
from commands.groups.aml import aml_group
from core.global_state import bot
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
    assert isinstance(bot, Bot), "bot has not been initialized."
    bot.event(on_ready)
    bot.event(on_message)
    bot.event(on_raw_reaction_add)
    print("Event handlers registered.")
# endregion

# region Commands
def register_commands() -> None:
    """
    Registers all commands for the bot.
    """
    print("Registering commands...")
    assert isinstance(bot, Bot), "bot is not initialized"
    
    # Command groups
    bot.tree.add_command(aml_group)
    print("Commands registered.")
# endregion