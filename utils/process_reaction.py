# region Imports
# Standard Library
from typing import List

# Third party
from discord import (Member, Message, Emoji, PartialEmoji, User, TextChannel,
                     VoiceChannel, CategoryChannel, ForumChannel, StageChannel,
                     Thread, Guild, AllowedMentions)
from discord.abc import PrivateChannel
from discord.ext.commands import Bot  # type: ignore
from discord.reaction import Reaction

# Local
import core.global_state as g
from core.terminate_bot import terminate_bot
from sponsorblockchain.models.blockchain import Blockchain
from models.log import Log
from models.user_save_data import UserSaveData
from utils.blockchain_utils import (add_block_transaction,
                                    get_last_block_timestamp)
from utils.formatting import format_coin_label
# endregion

# region Coin reaction


async def process_reaction(message_id: int,
                           emoji: PartialEmoji | Emoji | str,
                           sender: Member | User,
                           channel_id: int,
                           receiver: Member | User | None = None,
                           receiver_id: int | None = None,
                           greet_new_players: bool = True) -> None:
    """
    Processes a reaction event to mine a coin for a receiver.

    Args:
        emoji: The emoji used in the reaction.
        sender: The user who added the reaction.
        receiver: The user who receives the coin. Defaults to None.
        receiver_id: The ID of the user who receives the coin. Defaults to None.
    """
    assert isinstance(g.bot, Bot), "g.bot has not been initialized."
    assert isinstance(g.blockchain, Blockchain), (
        "g.blockchain has not been initialized.")
    assert isinstance(g.log, Log), "g.log has not been initialized."
    emoji_id: int | str | None = 0
    match emoji:
        case Emoji():
            emoji_id = emoji.id
        case PartialEmoji() if emoji.id is not None:
            emoji_id = emoji.id
        case PartialEmoji():
            return
        case str():
            return
    if emoji_id != g.coin_emoji_id:
        return

    if receiver is None:
        # Get receiver from id
        if receiver_id is not None:
            receiver = await g.bot.fetch_user(receiver_id)
        else:
            raise ValueError("Receiver is None.")
    else:
        receiver_id = receiver.id
    sender_id: int = sender.id

    if sender_id == receiver_id:
        return

    # Check if the user has mined the message already
    sender_name: str = sender.name
    save_data: UserSaveData = UserSaveData(
        user_id=sender_id, user_name=sender_name)
    message_mined_data: str | List[int] | bool | float | None = (
        save_data.load("messages_mined"))
    message_mined: List[int] = (
        message_mined_data if isinstance(message_mined_data, list) else [])
    if message_id in message_mined:
        return

    # Add the message ID to the list of mined messages
    # To prevent cheating, it's probably safer to do this here,
    # before adding the block
    message_mined.append(message_id)
    save_data.save(key="messages_mined", value=message_mined)

    receiver_name: str = receiver.name
    channel: (VoiceChannel | StageChannel | ForumChannel | TextChannel |
              CategoryChannel | Thread | PrivateChannel | None) = None
    last_block_timestamp: float | None = None
    mined_message: str
    if g.network_mining_enabled is False:
        print(f"{sender} ({sender_id}) is mining 1 {g.coin} "
              f"for {receiver} ({receiver_id})...")
        await add_block_transaction(blockchain=g.blockchain,
                                    sender=sender,
                                    receiver=receiver,
                                    amount=1,
                                    method="reaction"
                                    )

        # Set variables for logging
        last_block_timestamp = get_last_block_timestamp()
        mined_message = (f"{sender} ({sender_id}) mined 1 {g.coin} "
                         f"for {receiver} ({receiver_id}).")
    else:
        channel = g.bot.get_channel(channel_id)
        if channel is None:
            raise ValueError("ERROR: Could not process reaction because "
                             "channel is None.")
        if not isinstance(channel, (VoiceChannel, TextChannel, Thread)):
            print("WARNING: "
                  f"Skipping reaction because channel is {type(channel)}.")
            return
        print("--------------------")
        print(f"Miner {sender} ({sender_id}) is mining for "
              f"{receiver} ({receiver_id}) "
              f"(message {message_id})...")
        coin_reacters: List[Member | User] = []
        try:
            message: Message = await channel.fetch_message(message_id)
        except Exception as e:
            raise ValueError("ERROR: "
                             f"Could not fetch message {message_id}: {e}")
        earnings: dict[Member | User, int] = {}
        reactions: List[Reaction] = message.reactions
        for reaction in reactions:
            reaction_emoji: PartialEmoji | Emoji | str = reaction.emoji
            if not isinstance(reaction_emoji, (Emoji, PartialEmoji)):
                continue
            reaction_emoji_id: int | None = reaction_emoji.id
            if reaction_emoji_id == g.coin_emoji_id:
                coin_reacters = [user async for user in reaction.users()]
                break
        # Remove the message author from the list of miners if they reacted
        for miner in coin_reacters:
            miner_id: int = miner.id
            if miner_id == receiver_id:
                coin_reacters.remove(miner)
        reacters_count: int = len(coin_reacters)
        for i, miner in enumerate(reversed(coin_reacters)):
            miner_id: int = miner.id
            coins_to_give: int = reacters_count - i - 1
            if coins_to_give > 0:
                earnings[miner] = coins_to_give
        earnings[receiver] = reacters_count

        # Add blocks
        for earner, coins in earnings.items():
            earner_id: int = earner.id
            miner_name: str = earner.name
            coin_label: str = format_coin_label(coins)
            if earner_id != receiver_id:
                print(f"Miner {miner_name} ({earner_id}) is "
                      f"earning {coins} {coin_label} for having mined from "
                      f"the same message earlier (message {message_id})...")
            else:
                print(f"Author {receiver_name} ({receiver_id}) is "
                      f"earning {coins} {coin_label} on their message "
                      f"(message {message_id})...")
            await add_block_transaction(blockchain=g.blockchain,
                                        sender=sender,
                                        receiver=earner,
                                        amount=coins,
                                        method="reaction")
            # Log the mining
            last_block_timestamp = get_last_block_timestamp()
            if last_block_timestamp is None:
                print("ERROR: Could not get last block timestamp.")
                await terminate_bot()
            earned_message: str
            if earner_id != receiver_id:
                earned_message = (f"Miner {miner_name} ({earner_id}) earned "
                                  f"{coins} {coin_label} for having mined "
                                  "from the same message earlier "
                                  f"(message {message_id}).")
            else:
                earned_message = (f"Author {receiver_name} ({receiver_id}) "
                                  f"earned {coins} {coin_label} for their "
                                  f"message (message {message_id}).")
            g.log.log(line=earned_message, timestamp=last_block_timestamp)
            del earned_message
        mined_message = (f"Miner {sender_name} ({sender_id}) has mined "
                         f"for {receiver_name} ({receiver_id}) "
                         f"(message {message_id}).")
        print("--------------------")

    # Log the mining
    if last_block_timestamp is None:
        print("ERROR: Could not get last block timestamp.")
        await terminate_bot()
    try:
        g.log.log(line=mined_message, timestamp=last_block_timestamp)
        # Remove variables with common names to prevent accidental use
        del last_block_timestamp
    except Exception as e:
        print(f"ERROR: Error logging mining: {e}")
        await terminate_bot()

    chain_validity: bool | None = None
    try:
        print("Validating blockchain...")
        chain_validity = g.blockchain.is_chain_valid()
    except Exception as e:
        # TODO Revert blockchain to previous state
        print(f"ERROR: Error validating blockchain: {e}")
        chain_validity = False

    if chain_validity is False:
        await terminate_bot()

    # Inform receiver about if it's the first time they receive a coin
    if not greet_new_players:
        return
    if ((g.coin == "coin") or
        (g.coin_emoji_id == 0) or
        (g.coin_emoji_name == "") or
            (g.casino_channel_id == 0)):
        print("WARNING: Skipping reaction message because "
              "bot configuration is incomplete.")
        print(f"coin_emoji_id: {g.coin_emoji_id}")
        print(f"coin_emoji_name: {g.coin_emoji_name}")
        print(f"casino_channel_id: {g.casino_channel_id}")
        print(f"casino_channel: {g.casino_channel_id}")
        return
    save_data: UserSaveData = UserSaveData(
        user_id=sender_id, user_name=sender_name)
    mining_messages_enabled: bool = save_data.mining_messages_enabled
    about_command_formatted: str | None = (
        g.about_command_formatted)
    if about_command_formatted is None:
        error_message = ("ERROR: `about_command_formatted` is None. This "
                         "usually means that the commands have not been "
                         "synced with Discord yet.")
        raise ValueError(error_message)
    if not mining_messages_enabled:
        return
    save_data_receiver: UserSaveData = UserSaveData(
        user_id=receiver_id, user_name=receiver_name)
    del receiver_name
    informed_about_coin_reactions: bool = (
        save_data_receiver.reaction_message_received)
    if informed_about_coin_reactions:
        return
    casino_channel: (VoiceChannel | StageChannel | ForumChannel |
                     TextChannel | CategoryChannel | Thread |
                     PrivateChannel |
                     None) = g.bot.get_channel(g.casino_channel_id)

    if channel is None:
        channel = g.bot.get_channel(channel_id)
    if channel is None:
        raise ValueError("ERROR: Could not process reaction because "
                         "channel is None.")
    if not isinstance(channel, (VoiceChannel, TextChannel, Thread)):
        print("WARNING: "
              f"Skipping reaction because channel is {type(channel)}.")
        return
    user_message: Message = await channel.fetch_message(message_id)
    if isinstance(casino_channel, PrivateChannel):
        raise ValueError("ERROR: casino_channel is a private channel.")
    elif casino_channel is None:
        raise ValueError("ERROR: casino_channel is None.")
    # Check if the receiver has permission to read messages in the channel
    # (if not, the bot will not reply to them and the user's save data will
    # not be changed)
    # The permissions_for() method only works for Member objects,
    # not User objects, so we need to get the Member object if the receiver
    # is a User.
    receiver_member: Member | None
    if isinstance(receiver, Member):
        receiver_member = receiver
    else:
        # receiver is a User
        # Try to get member object from the guild
        if hasattr(channel, "guild"):
            guild: Guild = channel.guild
            receiver_member = guild.get_member(receiver_id)
            # If not in cache, fetch from API
            if receiver_member is None:
                receiver_member = await guild.fetch_member(receiver_id)
        else:
            receiver_member = None
    if receiver_member is None:
        print("WARNING: Could not get member object for receiver.")
        return
    receiver_has_permissions_to_channel: bool = (
        channel.permissions_for(receiver_member).view_channel and
        channel.permissions_for(receiver_member).read_messages)
    if not receiver_has_permissions_to_channel:
        print(f"Will not consider replying to {receiver} because "
              f"they do not have permission to channel {channel}.")
        return
    sender_mention: str = sender.mention
    message_content: str = (f"-# {sender_mention} has "
                            f"mined a {g.coin} for you! "
                            f"Enter {about_command_formatted} "
                            "in the chat box to learn more.")
    await user_message.reply(message_content,
                             allowed_mentions=AllowedMentions.none())
    del user_message
    del message_content
    del channel
    del channel_id
    del sender_mention
    save_data_receiver.reaction_message_received = True
# endregion
