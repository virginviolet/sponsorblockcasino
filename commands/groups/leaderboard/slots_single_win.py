# region Imports
# Standard library
from typing import List

# Third party
from discord import Interaction, Member, User, app_commands
# from discord.utils import format_dt

# Local
import core.global_state as g
from commands.groups.leaderboard import leaderboard_slots_group
from schemas.pydantic_models import SlotsHighScoreWinEntry
from utils.formatting import format_coin_label
from utils.smart_send_interaction_message import smart_send_interaction_message
# endregion

# region single_win


@leaderboard_slots_group.command(
    name="single_win",
    description=(
        f"See who has won the highest amount on the {g.Coin} Slot Machine"))
@app_commands.describe(
    ephemeral="Whether to send the message as ephemeral")
async def single_win(interaction: Interaction,
                     ephemeral: bool = False) -> None:
    """
    Command to show the single win leaderboard of the slot machine.
    """
    assert g.bot, (
        "Bot is not initialized.")
    assert g.slot_machine_high_scores, (
        "Slot machine high scores are not initialized.")
    if g.leaderboard_slots_highest_win_blocked is True:
        message_content: str
        if ((g.donation_goal is not None) and
            (g.donation_goal.reward_setting
                == "leaderboard_slots_highest_win_blocked")):
            message_content = (
                f"The {g.Coin} Slot Machine \"highest win\" leaderboard "
                "will be unlocked once the donation goal is achieved.\n"
                "-# Type `/donation_goal` to check the current progress.")
            ephemeral = False
        else:
            message_content = (
                f"The {g.Coin} Slot Machine \"highest win\" leaderboard "
                "is currently disabled. Please try again later.")
        await interaction.response.send_message(message_content,
                                                ephemeral=ephemeral)
        return

    high_scores_unsorted: List[SlotsHighScoreWinEntry] = (
        g.slot_machine_high_scores.high_scores.highest_wins.entries)
    high_scores: list[SlotsHighScoreWinEntry] = sorted(
        high_scores_unsorted, key=lambda x: (-x.win_money, x.created_at))
    message_content: str = (f"## {g.Coin} Slot Machine leaderboard "
                            "\N{EN DASH} Single win\n")
    invoker: User | Member = interaction.user
    invoker_name: str = invoker.name
    has_sent_message = False
    rank: int = 0
    for entry in high_scores:
        rank += 1
        coin_label: str = format_coin_label(entry.win_money)
        message_entry: str = f"{rank}. "
        if entry.user.name == invoker_name:
            message_entry += f"**{entry.user.name}**\n"
        else:
            message_entry += f"{entry.user.name}\n"
        # dt: datetime = datetime.fromtimestamp(entry.created_at)
        # dt_formatted: str = format_dt(dt)
        message_entry += (
            # f"-# {dt_formatted}\n"
            f"-# {entry.win_money:,} {coin_label}\n"
            "\n").replace(",", "\N{THIN SPACE}")
        message_content += message_entry
        if len(message_content) >= 2000 - 100:
            await smart_send_interaction_message(
                interaction, message_content, has_sent_message, ephemeral)
            has_sent_message = True
            message_content = ""
    if message_content != "":
        await smart_send_interaction_message(
            interaction, message_content, has_sent_message, ephemeral)
# endregion
