# region Imports
# Third party
from discord import app_commands
# endregion

# region Slots group
leaderboard_group = app_commands.Group(
    name="leaderboard", description="See who's the best")

leaderboard_slots_group = app_commands.Group(
    name="slots", description="Slots leaderboard", parent=leaderboard_group)
# endregion
