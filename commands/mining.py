# region Imports
from typing import List, cast
from discord import (Interaction, Member, PartialEmoji, User, app_commands,
                     AllowedMentions)
from discord.ext.commands import Bot  # type: ignore
from core.global_state import bot, Coin, coins, coin_emoji_id, coin_emoji_name
from models.user_save_data import UserSaveData
from utils.formatting import format_coin_label
# endregion

# region /mining

# assert bot is not None, "bot has not been initialized."
assert isinstance(bot, Bot), "bot has not been initialized."


@bot.tree.command(name="mining",
                  description="Configure mining settings")
@app_commands.describe(disable_reaction_messages="Stop the bot from messaging "
                       "new players when you mine their messages")
@app_commands.describe(stats="Show your mining stats")
@app_commands.describe(user="User to display mining stats for")
@app_commands.describe(incognito="Set whether the output of this command "
                       "should be visible only to you")
async def mining(interaction: Interaction,
                 disable_reaction_messages: bool | None = None,
                 stats: bool | None = None,
                 user: User | Member | None = None,
                 incognito: bool | None = None) -> None:
    """
    Command to configure mining settings.

    Args:
    interaction              -- The interaction object representing the
                                command invocation.
    disable_reaction_messages -- Disable reaction messages
    """
    should_use_ephemeral: bool
    invoker: User | Member = interaction.user
    if ((disable_reaction_messages is not None) and
        (user is not None) and
            (user != invoker)):
        message_content: str = ("You cannot set the mining settings for "
                                "someone else.")
        await interaction.response.send_message(
            message_content, ephemeral=True)
        del message_content
        return
    if (disable_reaction_messages is not None) and (stats is not None):
        message_content: str = ("You cannot set the mining settings and "
                                "view stats at the same time.")
        await interaction.response.send_message(
            message_content, ephemeral=True)
        return
    if disable_reaction_messages is not None:
        invoker_id: int = invoker.id
        invoker_name: str = invoker.name
        save_data: UserSaveData = UserSaveData(user_id=invoker_id,
                                               user_name=invoker_name)
        save_data.mining_messages_enabled = not disable_reaction_messages
        del save_data
        message_content: str
        if disable_reaction_messages is True:
            message_content = ("I will no longer message new players "
                               "when you mine their messages.")
        else:
            message_content: str = ("I will message new players when you mine "
                                    "their messages. Thank you for "
                                    f"helping the {Coin} network grow!")
        if incognito is False:
            should_use_ephemeral = False
        else:
            should_use_ephemeral = True
        await interaction.response.send_message(
            message_content, ephemeral=should_use_ephemeral)
        del message_content
        return
    elif stats:
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
            name=coin_emoji_name, id=coin_emoji_id)
        coin_label: str = format_coin_label(messages_mined_count)
        if messages_mined_count == 0 and user_parameter_used:
            message_content = (
                f"{user_to_check_mention} has not mined any {coins} yet.")
        elif messages_mined_count == 0:
            message_content = (f"You have not mined any {coins} yet. "
                               f"To mine a {coins} for someone, "
                               f"react {coin_emoji} to their message.")
        elif user_parameter_used:
            message_content = (
                f"{user_to_check_mention} has mined {messages_mined_count} "
                f"{coin_label} for others.")
        else:
            message_content = (
                f"You have mined {messages_mined_count} {coin_label} "
                "for others. Keep up the good work!")
        if incognito is True:
            should_use_ephemeral = True
        else:
            should_use_ephemeral = False
        await interaction.response.send_message(
            message_content, ephemeral=should_use_ephemeral,
            allowed_mentions=AllowedMentions.none())
        del message_content
        return
    elif user:
        message_content: str = ("The `user` parameter is meant to be used "
                                "with the `stats` parameter.")
        await interaction.response.send_message(
            message_content, ephemeral=True)
        del message_content
        return
    elif incognito:
        message_content: str = ("The `incognito` parameter is meant to be used "
                                "with the `stats` "
                                "or `disable_reaction_messages` parameter.")
        await interaction.response.send_message(
            message_content, ephemeral=True)
        return
    else:
        message_content: str = (
            "You must provide a parameter to this command.")
        await interaction.response.send_message(message_content, ephemeral=True)
        del message_content
        return
# endregion
