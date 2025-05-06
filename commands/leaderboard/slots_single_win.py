# region Imports
# Standard library
from typing import List

# Third party
from discord import Interaction, Member, User, app_commands
# from discord.utils import format_dt

# Local
import core.global_state as g
from schemas.data_classes import SlotsHighScoreEntry
from utils.formatting import format_coin_label
from utils.smart_send_interaction_message import smart_send_interaction_message
from .leaderboard_main import leaderboard_slots_group
# endregion

# region single_win


@leaderboard_slots_group.command(
    name="single_win",
    description=("Show the leaderboard for the highest single wins "
                 f"ever achieved the {g.Coin} Slot Machine."))
@app_commands.describe(
    private=("Whether to show the donation goal only to you."))
async def single_win(interaction: Interaction,
                     private: bool = False) -> None:
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
            (g.donation_goal.reward_setting_key
                == "leaderboard_slots_highest_win_blocked")):
            message_content = (
                f"The {g.Coin} Slot Machine \"highest win\" leaderboard "
                "will be unlocked once the donation goal is met.\n"
                "-# Type `/donation_goal` to check the current progress.")
            private = False
        else:
            message_content = (
                f"The {g.Coin} Slot Machine \"highest win\" leaderboard "
                "is currently disabled. Please try again later.")
        await interaction.response.send_message(message_content,
                                                ephemeral=private)
        return

    high_scores_unsorted: List[SlotsHighScoreEntry] = (
        g.slot_machine_high_scores.high_scores.highest_wins.entries)
    high_scores: list[SlotsHighScoreEntry] = sorted(
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
                interaction, message_content, has_sent_message, private)
            has_sent_message = True
            message_content = ""
    if message_content != "":
        await smart_send_interaction_message(
            interaction, message_content, has_sent_message, private)
# endregion
