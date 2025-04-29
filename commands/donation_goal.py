# region Imports
# Standard library

# Third party
from discord import AllowedMentions, Interaction

# Local
import core.global_state as g
from utils.formatting import format_coin_label
# endregion



# region /donation_goal
assert g.bot is not None, (
    "g.bot has not been initialized.")

@g.bot.tree.command(
    name="donation_goal",
    description=(
        f"See the {g.Coin} Casino's current donation goal")
)
async def donation_goal(
    interaction: Interaction,
    ephemeral: bool | None = None) -> None:
    """Command to show the current donation goal."""
    should_use_ephemeral: bool = False if ephemeral is None else ephemeral
    if g.donation_goal is None:
        await interaction.response.send_message(
           "Currently, there are no donation goals. Thank God!",
            ephemeral=should_use_ephemeral)
        return
    
    fraction_reached: float = (
        g.donation_goal.donated_amount / g.donation_goal.target_amount)
    coin_label: str = format_coin_label(g.donation_goal.target_amount)
    message_content: str = (
        f"Donation goal for {g.donation_goal.donation_recipient_mention}:\n"
        f"## {g.donation_goal.goal_description}\n"
        f"{g.donation_goal.donated_amount}/"
        f"{g.donation_goal.target_amount} {coin_label} "
        f"({fraction_reached:.0%})\n")
    if (interaction.user.id == g.administrator_id and
        g.donation_goal.reward_setting is not None):
        f"Reward: {g.donation_goal.reward_setting}\n"
    
    if g.donation_goal.reward_text is not None and ephemeral is not None:
        message_content += f"-# Reward: \"{g.donation_goal.reward_text}\"\n"
    if g.donation_goal.reward_setting is not None and ephemeral is not None:
        message_content += (
            "-# Reward setting: "
            f"`{g.donation_goal.reward_setting} = {g.donation_goal.reward_value}`\n")
    if interaction.user.id == g.administrator_id and ephemeral is not None:
        message_content += (
            "-# Goal reached message: "
            f"\"{g.donation_goal.goal_reached_message_content}\"\n")
    message_content += (
        "-# Type "
        f"`/transfer user:{g.donation_goal.donation_recipient_mention}`"
        " to donate.\n")
    await interaction.response.send_message(
        message_content, ephemeral=should_use_ephemeral,
        allowed_mentions=AllowedMentions.none())
# endregion