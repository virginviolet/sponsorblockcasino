# region Imports
# Standard library
from typing import List

# Third party
from discord import (Guild, Member, Message, MessageInteraction, User,
                     TextChannel, VoiceChannel)
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
from models.checkpoints import ChannelCheckpoints
from models.grifter_suppliers import GrifterSuppliers
# endregion

# region Message
assert isinstance(g.bot, Bot), "bot is not initialized"

@g.bot.event
async def on_message(message: Message) -> None:
    """
    Handles incoming messages and saves channel checkpoints.
    If the channel ID of the incoming message is already in the global
    `all_channel_checkpoints` dictionary, it saves the message ID to the
    corresponding checkpoint. If the channel ID is not in the dictionary,
    it creates a new `ChannelCheckpoints` instance for the channel and adds
    it to the dictionary.
    Args:
        message (Message): The incoming message object.
    Returns:
        None
    """
    assert isinstance(g.bot, Bot), "bot is not initialized"
    g.all_channel_checkpoints = (
        g.all_channel_checkpoints)
    assert isinstance(g.grifter_suppliers, GrifterSuppliers)
    channel_id: int = message.channel.id

    if channel_id in g.all_channel_checkpoints:
        message_id: int = message.id
        g.all_channel_checkpoints[channel_id].save(message_id)
        del message_id
    else:
        # If a channel is created while the bot is running, we will likely end
        # up here.
        # Add a new instance of ChannelCheckpoints to
        # the all_channel_checkpoints dictionary for this new channel.
        guild: Guild | None = message.guild
        if guild is None:
            # TODO Ensure checkpoints work threads
            # print("ERROR: Guild is None.")
            # administrator: str = (
            #     (await bot.fetch_user(administrator_id)).mention)
            # await message.channel.send("An error occurred. "
            #                            f"{administrator} pls fix.")
            raise Exception("Guild is None.")
        guild_name: str = guild.name
        guild_id: int = guild.id
        channel = message.channel
        if ((isinstance(channel, TextChannel)) or
                isinstance(channel, VoiceChannel)):
            channel_name: str = channel.name
            g.all_channel_checkpoints[channel_id] = ChannelCheckpoints(
                guild_name=guild_name,
                guild_id=guild_id,
                channel_name=channel_name,
                channel_id=channel_id
            )
        else:
            # print("ERROR: Channel is not a text channel or voice channel.")
            # administrator: str = (
            #     (await g.bot.fetch_user(ADMINISTRATOR_ID)).mention)
            # await message.channel.send("An error occurred. "
            #                            f"{administrator} pls fix.")
            return

    # Look for GrifterSwap messages
    message_author: User | Member = message.author
    message_author_id: int = message_author.id
    del message_author
    if message_author_id != g.grifter_swap_id:
        return
    if message.reference is None:
        return
    referenced_message_id: int | None = message.reference.message_id
    if referenced_message_id is None:
        return
    referenced_message: Message = await message.channel.fetch_message(
        referenced_message_id)
    referenced_message_text: str = referenced_message.content
    if referenced_message_text.startswith("!suppliers"):
        users_mentioned: List[int] = message.raw_mentions
        await g.grifter_suppliers.replace(g.bot, users_mentioned)
        del users_mentioned
        return
    referenced_message_author: User | Member = referenced_message.author
    referenced_message_author_id: int = referenced_message_author.id
    message_text: str = message.content
    user_supplied_grifter_sbcoin: bool = (
        "Added" in message_text and
        "sent" in referenced_message_text and
        referenced_message_author_id == g.sbcoin_id)

    user_supplied_grifter_this_coin: bool = (
        "Added" in message_text and
        "transferred" in referenced_message_text and
        referenced_message_author_id == g.casino_house_id)

    if user_supplied_grifter_sbcoin or user_supplied_grifter_this_coin:
        # get the cached message in order to get the command invoker
        referenced_message_full: Message = (
            await message.channel.fetch_message(referenced_message_id))
        del referenced_message_id
        referenced_message_full_interaction: MessageInteraction | None = (
            referenced_message_full.interaction)
        if referenced_message_full_interaction is None:
            return
        referenced_message_full_invoker: User | Member = (
            referenced_message_full_interaction.user)
        await g.grifter_suppliers.add(referenced_message_full_invoker)
# endregion
