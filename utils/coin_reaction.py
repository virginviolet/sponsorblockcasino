# region Imports
# Standard Library
from typing import List

# Third party
from discord import (Member, Message, Emoji, PartialEmoji, User, TextChannel,
                     VoiceChannel, CategoryChannel, ForumChannel, StageChannel,
                     Thread, AllowedMentions)
from discord.abc import PrivateChannel
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)

# Local
import core.global_state as g
from core.terminate_bot import terminate_bot
from models.log import Log
from models.user_save_data import UserSaveData
from utils.blockchain_utils import (add_block_transaction,
                                    get_last_block_timestamp)

# region Coin reaction


async def process_reaction(bot: Bot,
                           message_id: int,
                           emoji: PartialEmoji | Emoji | str,
                           sender: Member | User,
                           receiver: Member | User | None = None,
                           receiver_id: int | None = None,
                           channel_id: int | None = None) -> None:
    """
    Processes a reaction event to mine a g.coin for a receiver.

    Args:
        emoji: The emoji used in the reaction.
        sender: The user who sent the reaction.
        receiver: The user who receives the g.coin. Defaults to None.
        receiver_id: The ID of the user who receives the g.coin. Defaults
            to None.
    """

    assert g.log is not None, (
        "g.log must be initialized before calling process_reaction")
    assert isinstance(g.log, Log), (
        "g.log must be initialized before calling process_reaction")
    
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
    if emoji_id == g.coin_emoji_id:
        if receiver is None:
            # Get receiver from id
            if receiver_id is not None:
                receiver = await bot.fetch_user(receiver_id)
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
        message_mined.append(message_id)
        save_data.save(key="messages_mined", value=message_mined)

        print(f"{sender} ({sender_id}) is mining 1 {g.coin} "
              f"for {receiver} ({receiver_id})...")
        if g.blockchain is None:
            raise ValueError("ERROR: g.blockchain is None.")
        await add_block_transaction(blockchain=g.blockchain,
                                    sender=sender,
                                    receiver=receiver,
                                    amount=1,
                                    method="reaction"
        )

        # Log the mining
        last_block_timestamp: float | None = get_last_block_timestamp()
        if last_block_timestamp is None:
            print("ERROR: Could not get last block timestamp.")
            await terminate_bot()

        assert g.log is not None, (
            "g.log must be initialized before calling process_reaction")
        try:
            mined_message: str = (f"{sender} ({sender_id}) mined 1 {g.coin} "
                                  f"for {receiver} ({receiver_id}).")
            g.log.log(line=mined_message, timestamp=last_block_timestamp)
            # Remove variables with common names to prevent accidental use
            del mined_message
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

        # Inform receiver if it's the first time they receive a coin
        # Do not pass the channel_id if you do not want to send message
        # (like perhaps when scraping old messages)
        if channel_id is None:
            return
        if ((g.coin == "coin") or
            (g.coin_emoji_id == 0) or
            (g.coin_emoji_name == "") or
                (g.casino_channel_id == 0)):
            print("WARNING: Skipping reaction message because "
                  "bot configuration is incomplete.")
            print(f"g.coin_emoji_id: {g.coin_emoji_id}")
            print(f"g.coin_emoji_name: {g.coin_emoji_name}")
            print(f"g.casino_channel_id: {g.casino_channel_id}")
            print(f"casino_channel: {g.casino_channel_id}")
            return
        save_data: UserSaveData = UserSaveData(
            user_id=sender_id, user_name=sender_name)
        mining_messages_enabled: bool = save_data.mining_messages_enabled
        if g.about_command_formatted is None:
            error_message = ("ERROR: `about_command_mention` is None. This "
                             "usually means that the commands have not been ")
            raise ValueError(error_message)
        if not mining_messages_enabled:
            return
        receiver_name: str = receiver.name
        save_data_receiver: UserSaveData = UserSaveData(
            user_id=receiver_id, user_name=receiver_name)
        del receiver_name
        informed_about_coin_reactions: bool = (
            save_data_receiver.reaction_message_received)
        if informed_about_coin_reactions:
            return
        channel: (VoiceChannel | StageChannel | ForumChannel | TextChannel |
                  CategoryChannel | Thread | PrivateChannel | None) = (
            bot.get_channel(channel_id))
        if not isinstance(channel, (VoiceChannel, TextChannel, Thread)):
            return
        casino_channel: (VoiceChannel | StageChannel | ForumChannel |
                         TextChannel | CategoryChannel | Thread |
                         PrivateChannel |
                         None) = bot.get_channel(g.casino_channel_id)
        user_message: Message = await channel.fetch_message(message_id)
        if isinstance(casino_channel, PrivateChannel):
            raise ValueError("ERROR: casino_channel is a private channel.")
        elif casino_channel is None:
            raise ValueError("ERROR: casino_channel is None.")
        sender_mention: str = sender.mention
        message_content: str = (f"-# {sender_mention} has "
                                f"mined a {g.coin} for you! "
                                f"Enter {g.about_command_formatted} "
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
