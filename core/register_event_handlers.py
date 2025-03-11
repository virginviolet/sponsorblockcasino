from discord.ext.commands import Bot  # type: ignore
from core.global_state import bot
from event_handlers.on_ready import on_ready
from event_handlers.message import on_message
from event_handlers.reaction import on_raw_reaction_add
from commands.balance import balance
from commands.about_coin import about_coin
from commands.groups.aml import aml_group
from commands.mining import mining
from commands.reels import reels
from commands.slots import slots
from commands.transfer import transfer
from core.global_state import bot

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

def register_commands() -> None:
    """
    Registers all commands for the bot.
    """
    print("Registering commands...")
    assert isinstance(bot, Bot), "bot is not initialized"
    
    # Command groups
    bot.tree.add_command(aml_group)

    # Standalone commands
    bot.tree.add_command(about_coin)
    bot.tree.add_command(balance)
    bot.tree.add_command(mining)
    bot.tree.add_command(reels)
    bot.tree.add_command(slots)
    bot.tree.add_command(transfer)
    print("Commands registered.")
