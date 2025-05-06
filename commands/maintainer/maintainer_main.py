# region Imports
# Third party
from discord import app_commands
# endregion

# region Maintainer group
maintainer_group = app_commands.Group(
    name="maintainer", description="Bot maintainer commands")

maintainer_donation_goal_group = app_commands.Group(
    name="donation_goal", description="Donation goal commands",
    parent=maintainer_group)
# endregion
