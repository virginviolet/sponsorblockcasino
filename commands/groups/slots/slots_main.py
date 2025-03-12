# region Imports
# Third party
from discord.ext.commands import Bot  # type: ignore
from discord import app_commands

# Local
import core.global_state as g
assert isinstance(g.bot, Bot), "bot has not been initialized."
# endregion

# region Slots group
slots_group = app_commands.Group(
    name="slots", description="Play the slot machine.")
# endregion
