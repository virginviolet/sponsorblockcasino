# region Imports
# Standard library

# Third party
from discord import (CategoryChannel, ForumChannel, Interaction, Member,
                     StageChannel, TextChannel, Thread, User, VoiceChannel,
                     app_commands)
from discord.abc import PrivateChannel
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)

# Local
import core.global_state as g
from models.user_save_data import UserSaveData
from utils.smart_send_interaction_message import smart_send_interaction_message
from .mining_main import mining_group
# endregion

# region settings

mining_updates_channel_string: str = (
    f"{g.mining_updates_channel_name}"
    if ((g.mining_updates_channel_name.startswith("#") and
         not " " in g.mining_updates_channel_name))
    else f"#{g.mining_updates_channel_name}"
)
mining_highlights_channel_string: str = (
    f"{g.mining_highlights_channel_name}"
    if (g.mining_highlights_channel_name.startswith("#") and
        not " " in g.mining_highlights_channel_name)
    else f"#{g.mining_highlights_channel_name}")


@mining_group.command(name="settings",
                      description="Configure your mining settings")
@app_commands.describe(disable_reaction_messages="Stop the bot from messaging "
                       "new players when you mine their messages")
@app_commands.describe(enable_network_mining_mention="Allow the bot to "
                       f"mention you in {mining_updates_channel_string}.")
@app_commands.describe(enable_mentions_in_highlights=(
                       "Allow the bot to mention you "
                       f"in {mining_highlights_channel_string}."))
async def settings(interaction: Interaction,
                   disable_reaction_messages: bool | None = None,
                   enable_network_mining_mention: bool | None = None,
                   enable_mentions_in_highlights: (
                       bool | None) = None) -> None:
    """
    Mining commands

    Args:
    interaction               -- The interaction object representing the
                                 command invocation.
    disable_reaction_messages -- Disable reaction messages
    """
    invoker: User | Member = interaction.user
    invoker_id: int = invoker.id
    invoker_name: str = invoker.name
    save_data: UserSaveData = UserSaveData(user_id=invoker_id,
                                           user_name=invoker_name)
    message_content: str
    has_sent_message: bool = False
    if (disable_reaction_messages is None and
            enable_network_mining_mention is None and
            enable_mentions_in_highlights is None):

        message_content = (
            "Your settings are as follows:\n"
            "**Disable reaction messages:** "
            f"{save_data.mining_messages_enabled}\n"
            "**Enable network mining mention:** "
            f"{save_data.network_mining_mentions_enabled}\n"
            "**Enable mentions in highlights:** "
            f"{save_data.network_mining_highlights_mentions_enabled}")
        await smart_send_interaction_message(interaction=interaction,
                                             content=message_content,
                                             has_sent_message=has_sent_message,
                                             ephemeral=True)
        del message_content
        has_sent_message = True
        return
    if disable_reaction_messages is not None:
        save_data.mining_messages_enabled = not disable_reaction_messages
        if disable_reaction_messages is True:
            message_content = ("I will no longer message new players "
                               "when you mine their messages.")
        else:
            message_content = ("I will message new players when you mine "
                               "their messages. Thank you for "
                               f"helping the {g.Coin} network grow!")
        await smart_send_interaction_message(interaction=interaction,
                                             content=message_content,
                                             has_sent_message=has_sent_message,
                                             ephemeral=True)
        del message_content
        has_sent_message = True

    if enable_network_mining_mention is not None:
        assert isinstance(g.bot, Bot), "bot is not initialized."
        mining_channel: (VoiceChannel | StageChannel | ForumChannel | TextChannel |
                         CategoryChannel | Thread | PrivateChannel |
                         None)
        if g.mining_updates_channel_id == 0:
            raise TypeError("mining_updates_channel_id is 0")
        mining_channel: (VoiceChannel | StageChannel | ForumChannel | TextChannel |
                         CategoryChannel | Thread | PrivateChannel |
                         None) = g.bot.get_channel(g.mining_updates_channel_id)
        mining_channel_mention: str
        if isinstance(mining_channel, PrivateChannel):
            raise TypeError("mining_channel is a PrivateChannel")
        elif mining_channel is None:
            highlights_channel_mention = "the network mining highlights channel"
            mining_channel_mention = "the network mining channel"
            print("mining_channel is None")
            raise TypeError("mining_channel is None")
        mining_channel_mention: str = mining_channel.mention
        save_data.network_mining_mentions_enabled = (
            enable_network_mining_mention)
        if enable_network_mining_mention is True:
            message_content = ("I will now mention you in "
                               f"{mining_channel_mention}.")
        else:
            message_content = ("I will no longer mention you in "
                               f"{mining_channel_mention}.")
        await smart_send_interaction_message(interaction=interaction,
                                             content=message_content,
                                             has_sent_message=has_sent_message,
                                             ephemeral=True)
        del message_content
        has_sent_message = True
    if enable_mentions_in_highlights is not None:
        assert isinstance(g.bot, Bot), "bot is not initialized."
        highlights_channel: (VoiceChannel | StageChannel | ForumChannel |
                             TextChannel | CategoryChannel | Thread | PrivateChannel |
                             None)
        if g.mining_highlights_channel_id == 0:
            raise TypeError("mining_highlights_channel_id is 0")
        highlights_channel = g.bot.get_channel(g.mining_highlights_channel_id)
        highlights_channel_mention: str
        if isinstance(highlights_channel, PrivateChannel):
            raise TypeError("highlights_channel is a PrivateChannel")
        elif highlights_channel is None:
            raise TypeError("highlights_channel is None")
        highlights_channel_mention = highlights_channel.mention
        save_data.network_mining_highlights_mentions_enabled = (
            enable_mentions_in_highlights)
        if enable_mentions_in_highlights is True:
            message_content = ("I will now mention you in "
                               f"{highlights_channel_mention}.")
        else:
            message_content = ("I will no longer mention you in "
                               f"{highlights_channel_mention}.")
        await smart_send_interaction_message(interaction=interaction,
                                             content=message_content,
                                             has_sent_message=has_sent_message,
                                             ephemeral=True)
        del message_content
        has_sent_message = True
# endregion
