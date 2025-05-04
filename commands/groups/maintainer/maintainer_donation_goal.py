# region Imports
# Standard library
from datetime import datetime
from time import time
from typing import List

# Third party
from discord import AllowedMentions, Interaction, Member, User, app_commands
from discord.utils import time_snowflake

# Local
import core.global_state as g
from commands.groups.maintainer.maintainer_main import (
    maintainer_donation_goal_group)
from schemas.pydantic_models import DonationGoal
from utils.formatting import format_coin_label
# endregion

# region donation_goal


@maintainer_donation_goal_group.command(
    name="add",
    description=f"Add a {g.coin} donation goal"
)
@app_commands.describe(
    donation_recipient="The user who will receive the donations",
    target_amount="The target amount of the donation goal",
    starting_amount="The initial amount already donated",
    goal_description="A description of the donation goal",
    goal_reached_message="A message to send when the goal is reached",
    reward_setting="A bot setting to change when the goal is reached",
    reward_setting_value="The value to set the reward setting to",
    silent="Whether to show the success message only to you")
async def donation_goal_add(
    interaction: Interaction,
    donation_recipient: User | Member,
    target_amount: int,
    starting_amount: int = 0,
    goal_description: str | None = None,
    goal_reached_message: str | None = None,
    reward_setting: str | None = None,
    reward_setting_value: bool | None = None,
    silent: bool | None = None,
) -> None:
    """Add a donation goal for the casino."""
    # Check if the user is a maintainer
    # TODO Use coin bot developer role or maintainer role instead of administrator id
    # IMPROVE Make persistent; save goal to file
    assert g.bot is not None, (
        "g.bot has not been initialized.")
    if interaction.user.id != g.administrator_id:
        await interaction.response.send_message(
            "You are not authorized to set donation goals.",
            ephemeral=True)
        return

    if target_amount <= 0:
        await interaction.response.send_message(
            "Amount must be greater than 0.", ephemeral=True)
        return
    elif target_amount > 10000000:
        await interaction.response.send_message(
            "Amount must be less than 10 million.", ephemeral=True)
        return
    if starting_amount < 0:
        await interaction.response.send_message(
            "Starting amount must be greater than or equal to 0.",
            ephemeral=True)
        return
    elif starting_amount >= target_amount:
        await interaction.response.send_message(
            "Starting amount must be less than target amount.",
            ephemeral=True)
        return

    if reward_setting_value is not None and reward_setting is None:
        await interaction.response.send_message(
            "Reward value is set, but reward setting is not.",
            ephemeral=True)
        return
    elif reward_setting is not None and reward_setting_value is None:
        await interaction.response.send_message(
            "Reward setting is set, but reward value is not.",
            ephemeral=True)
        return

    g.donation_goal = DonationGoal(
        created_at=time(),
        goal_description=goal_description,
        donation_recipient_id=donation_recipient.id,
        donation_recipient_name=donation_recipient.name,
        donation_recipient_mention=donation_recipient.mention,
        id=time_snowflake(datetime.now()),
        donated_amount=starting_amount,
        target_amount=target_amount,
        reward_setting_key=reward_setting,
        reward_setting_value=reward_setting_value,
        goal_reached_message_content=goal_reached_message)

    fraction_reached: float = (
        starting_amount / target_amount)
    goal_summary_for_console: str = (
        f"{goal_description}\n"
        f"{starting_amount}/"
        f"{target_amount} {format_coin_label(target_amount)} "
        f"({fraction_reached:.0%})")
    goal_summary_for_message: str = (
        f"## {goal_summary_for_console}")
    if reward_setting is not None and silent is not None:
        goal_summary_for_console += (
            f"\nReward setting: `{reward_setting} = {reward_setting_value}`")
        goal_summary_for_message += (
            f"\n-# **Reward setting**: `{reward_setting} = {reward_setting_value}`")
    if goal_reached_message is not None and silent is not None:
        goal_summary_for_console += (
            f"\nGoal reached message: \"{goal_reached_message}\"")
        goal_summary_for_message += (
            f"\n-# **Goal reached message**: \"{goal_reached_message}\"")
    print_message_content: str = (
        f"{interaction.user.name} ({interaction.user.id}) added a "
        "donation goal "
        f"for {donation_recipient.name} ({donation_recipient.id}):\n"
        f"{goal_summary_for_console}")
    print(print_message_content)
    message_content: str = (
        f"Donation goal added for {donation_recipient.mention}:\n"
        f"{goal_summary_for_message}\n"
        "-# Type `/transfer` to donate.")
    should_use_ephemeral: bool = False if silent is None else silent
    await interaction.response.send_message(
        message_content, ephemeral=should_use_ephemeral,
        allowed_mentions=AllowedMentions.none())


@donation_goal_add.autocomplete("reward_setting")
async def donation_goal_add_reward_autocomplete(
    interaction: Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """Autocomplete for the reward_setting argument."""
    choices: List[app_commands.Choice[str]] = [
        app_commands.Choice(
            name="leaderboard_slots_highest_win_blocked",
            value="leaderboard_slots_highest_win_blocked"),
        app_commands.Choice(
            name="leaderboard_slots_highest_wager_blocked",
            value="leaderboard_slots_highest_wager_blocked"),
        app_commands.Choice(
            name="leaderboard_holders_blocked",
            value="leaderboard_holders_blocked"),
    ]
    return choices


@app_commands.describe(
    silent="Whether to show the success message only to you.")
@maintainer_donation_goal_group.command(
    name="remove",
    description=f"Remove the {g.coin} donation goal, if any")
async def donation_goal_remove(
    interaction: Interaction,
    silent: bool = False,
) -> None:
    """Remove the donation goal for the casino."""
    # Check if the user is a maintainer
    # TODO Use coin bot developer role or maintainer role instead of administrator id
    assert g.bot is not None, (
        "g.bot has not been initialized.")
    if interaction.user.id != g.administrator_id:
        await interaction.response.send_message(
            "You are not authorized to remove donation goals.",
            ephemeral=silent)
        return
    if g.donation_goal is None:
        await interaction.response.send_message(
            "There is no donation goal to remove.",
            ephemeral=silent)
        return
    try:
        g.donation_goal = None
        print(f"{interaction.user.name} ({interaction.user.id}) removed the "
              "donation goal.")
    except Exception as e:
        error_message_content: str = (
            "The donation goal could not be removed.")
        await interaction.response.send_message(
            error_message_content, ephemeral=silent)
        # raise with error message
        raise RuntimeError(error_message_content) from e
    await interaction.response.send_message(
        "The donation goal has been removed.",
        ephemeral=silent)


# @donation_goal_add.autocomplete("reward_value")
# async def donation_goal_add_reward_value_autocomplete(
#     interaction: Interaction,
#     current: str,
#     reward_setting: str | None = None,
# ) -> List[app_commands.Choice[str]]:
#     """Autocomplete for the reward_value argument."""
#     choices: List[app_commands.Choice[str]] = []
#     if reward_setting == "leaderboard_slots_highest_win_blocked":
#         choices = [
#             app_commands.Choice(name="True", value="True"),
#             app_commands.Choice(name="False", value="False"),
#         ]
#     return choices
# endregion
