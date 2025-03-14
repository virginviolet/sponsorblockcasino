# region Imports
# Third party
from discord.ext.commands import Bot  # type: ignore
from discord import app_commands
# endregion

# region Slots group
slots_group = app_commands.Group(
    name="slots", description="Play the slot machine.")
# endregion
