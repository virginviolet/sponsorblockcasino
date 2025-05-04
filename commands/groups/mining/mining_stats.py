# region Imports
# Standard library
from typing import List, cast

# Third party
from discord import (Interaction, Member, PartialEmoji, User,
                     AllowedMentions, app_commands)

# Local
import core.global_state as g
from models.user_save_data import UserSaveData
from utils.formatting import format_coin_label
from .mining_main import mining_group
# endregion

# region stats

@mining_group.command(name="stats",
                      description="Show your mining stats")
@app_commands.describe(user="User to display mining stats for")
@app_commands.describe(incognito="Set whether to show the stats only to you")
async def stats(interaction: Interaction,
                       user: User | Member | None = None,
                       incognito: bool | None = None) -> None:
    user_to_check: User | Member
    user_parameter_used: bool = user is not None
    if user_parameter_used:
        user_to_check = user
    else:
        invoker: User | Member = interaction.user
        user_to_check = invoker
    user_to_check_id: int = user_to_check.id
    user_to_check_name: str = user_to_check.name
    user_to_check_mention: str = user_to_check.mention
    save_data: UserSaveData = UserSaveData(user_id=user_to_check_id,
                                           user_name=user_to_check_name)
    messages_mined: List[int] = (
        cast(List[int], save_data.load("messages_mined")))
    messages_mined_count: int = len(messages_mined)
    message_content: str
    coin_emoji = PartialEmoji(
        name=g.coin_emoji_name, id=g.coin_emoji_id)
    coin_label: str = format_coin_label(messages_mined_count)
    if messages_mined_count == 0 and user_parameter_used:
        message_content = (
            f"{user_to_check_mention} has not mined any {g.coins} yet.")
    elif messages_mined_count == 0:
        message_content = (f"You have not mined any {g.coins} yet. "
                           f"To mine a {g.coins} for someone, "
                           f"react {coin_emoji} to their message.")
    elif user_parameter_used:
        message_content = (
            f"{user_to_check_mention} has mined {messages_mined_count} "
            f"{coin_label} for others.")
    else:
        message_content = (
            f"You have mined {messages_mined_count:,} {coin_label} for "
            "others. Keep up the good work!").replace(",", "\N{THIN SPACE}")
    if incognito is True:
        should_use_ephemeral = True
    else:
        should_use_ephemeral = False
    await interaction.response.send_message(
        message_content, ephemeral=should_use_ephemeral,
        allowed_mentions=AllowedMentions.none())
    del message_content
    return
# endregion
