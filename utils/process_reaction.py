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
        receiver_id: The ID of the user who receives the coin. Defaults
            to None.
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

    # Common variables (1/3)
    sender_id: int = sender.id

    if sender_id == receiver_id:
        return

    # Common variables (2/3)
    sender_name: str = sender.name
    sender_save_data: UserSaveData = UserSaveData(
        user_id=sender_id, user_name=sender_name)

    # Check if the user has mined for the message already
    message_mined_data: str | List[int] | bool | float | None = (
        sender_save_data.load("messages_mined"))
    message_mined: List[int] = (
        message_mined_data if isinstance(message_mined_data, list) else [])
    if message_id in message_mined:
        return

    # Common variables (3/3)
    receiver_name: str = receiver.name
    channel: (VoiceChannel | StageChannel | ForumChannel | TextChannel |
              CategoryChannel | Thread | PrivateChannel | None) = None
    last_block_timestamp: float | None = None
    log_messages: dict[float | None, str] = {}
    mined_for_log_message: str
    user_message: Message | None = None

    # Add the message ID to the list of messages mined for
    # Doing this before rather than after the transaction
    # as an anti-cheating precaution
    message_mined.append(message_id)
    sender_save_data.save(key="messages_mined", value=message_mined)

    if g.network_mining_enabled is False:
        print(f"{sender} ({sender_id}) is mining 1 {g.coin} "
              f"for {receiver} ({receiver_id})...")

        await add_block_transaction(blockchain=g.blockchain,
                                    sender=sender,
                                    receiver=receiver,
                                    amount=1,
                                    method="reaction")

        # Set variables for logging
        last_block_timestamp = get_last_block_timestamp()
        mined_for_log_message = (f"{sender} ({sender_id}) mined 1 {g.coin} "
                                 f"for {receiver} ({receiver_id}).")
        log_messages[last_block_timestamp] = mined_for_log_message
        del last_block_timestamp
        del mined_for_log_message
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

        # Find any existing miners for the message
        coin_reacters: List[Member | User] = []
        try:
            user_message = await channel.fetch_message(message_id)
        except Exception as e:
            raise ValueError("ERROR: "
                             f"Could not fetch message {message_id}: {e}")
        reactions: List[Reaction] = user_message.reactions
        for reaction in reactions:
            reaction_emoji: PartialEmoji | Emoji | str = reaction.emoji
            if not isinstance(reaction_emoji, (Emoji, PartialEmoji)):
                continue
            reaction_emoji_id: int | None = reaction_emoji.id
            if reaction_emoji_id == g.coin_emoji_id:
                # FIXME
                # Sorted by ~~most recent first~~ user id
                coin_reacters = [user async for user in reaction.users()]
                break
        reacters_count: int = len(coin_reacters)
        prior_reacters_count: int = reacters_count

        # Create dictionary for immediate payouts
        earnings: dict[Member | User, int] = {}
        # Add the message author as the first entry
        # (they should get the most coins)
        earnings[receiver] = 0
        # Iterate reversed so that the first reacter comes first
        for miner in reversed(coin_reacters):
            miner_id: int = miner.id
            if miner_id == receiver_id:
                # Skip the message author from the list of miners
                # in case they reacted to their own message
                reacters_count -= 1
                continue
            elif miner_id == sender_id:
                prior_reacters_count -= 1
            earnings[miner] = 0
        # Add values to the keys in the earnings dictionary
        for i, participant in enumerate(earnings.keys()):
            participant_id: int = participant.id
            # Each subsequent reacter gets one less coin than the previous one
            # The most recent one (the "sender") gets 0 coins
            coins_to_give: int = reacters_count - i
            earnings[participant] = coins_to_give

        # Add blocks and set variables for logging
        for i, (participant, coins) in enumerate(earnings.items()):
            # Add block
            if coins <= 0:
                continue
            participant_id: int = participant.id
            miner_name: str = participant.name
            coin_label: str = format_coin_label(coins)
            if participant_id == receiver_id:
                print(f"{sender_name} ({sender_id}) is mining "
                      f"for {receiver_name}, and "
                      f"author {receiver_name} ({receiver_id}) is "
                      f"earning {coins} {coin_label} "
                      f"(message {message_id})...")
            else:
                print(f"{sender_name} ({sender_id}) is mining "
                      f"for {receiver_name}, and "
                      f"miner #{i} {miner_name} ({participant_id}) "
                      f"is earning {coins} {coin_label} from having mined for "
                      f"the same message earlier (message {message_id}).")
            await add_block_transaction(blockchain=g.blockchain,
                                        sender=sender,
                                        receiver=participant,
                                        amount=coins,
                                        method="reaction")

            # Set variables for logging
            last_block_timestamp = get_last_block_timestamp()
            if last_block_timestamp is None:
                print("ERROR: Could not get last block timestamp.")
                await terminate_bot()
            earned_message: str
            if participant_id == receiver_id:
                earned_message = (
                    f"{sender_name} ({sender_id}) mined for {receiver_name}, "
                    f"and author {receiver_name} ({receiver_id}) "
                    f"earned {coins} {coin_label} (message {message_id}).")
            else:
                earned_message = (
                    f"{sender_name} ({sender_id}) mined for {receiver_name}, "
                    f"and miner #{i} {miner_name} ({participant_id}) "
                    f"earned {coins} {coin_label} from having mined for the "
                    f"same message earlier (message {message_id}).")
            log_messages[last_block_timestamp] = earned_message
            del last_block_timestamp
            del earned_message

        # Make an update in the mining updates channel
        mining_channel: (VoiceChannel | StageChannel | ForumChannel |
                         TextChannel | CategoryChannel | Thread |
                         PrivateChannel |
                         None) = g.bot.get_channel(g.mining_updates_channel_id)
        if mining_channel is None:
            print("WARNING: Will not send mining update "
                  "because mining_channel is None.")
        elif not isinstance(
                mining_channel, (VoiceChannel, TextChannel, Thread)):
            print("WARNING: Will not send mining update "
                  f"because mining_channel is {type(mining_channel)}.")
        else:
            # Calculate how many coins the coins each miner has earned from
            # the message since the message's first reaction
            earnings_since_start: dict[Member | User, int] = {}
            earnings_since_start = {
                participant: 0 for participant in earnings.keys()}
            participants = list(earnings.keys())
            for reaction in range(len(earnings.keys())):
                for i in range(reaction):
                    participant: Member | User = participants[i]
                    coins_to_give: int = reaction - i
                    earnings_since_start[participant] += coins_to_give
            earnings_since_start_total: int = (
                sum(earnings_since_start.values()))
            # Set content for the mining update message
            coin_label: str = (
                format_coin_label(earnings_since_start_total))
            participants_table: str = ""
            for i, (participant, participant_coins) in enumerate(
                    earnings.items()):
                participant_mention: str = participant.mention
                coins_since_start: int = earnings_since_start[participant]
                participant_id: int = participant.id
                title: str = "Author" if participant_id == receiver_id else (
                    f"Miner #{i}")
                participants_table += (
                    f"{title}: {participant_mention}: "
                    f"{coins_since_start} (+{participant_coins})\n")
            receiver_mention: str = receiver.mention
            mining_update_message_content: str = (
                f"A total of {earnings_since_start_total} {coin_label} "
                f"has been mined for {receiver_mention}'s message!\n"
                f"{participants_table}")
            del coin_label
            print(f"coin_reacters: {[(r.name, r.id) for r in coin_reacters]}")
            print(f"earnings: {[(e.name, c) for e, c in earnings.items()]}")
            print(f"earnings_since_start: {[(e.name, c) for e, c in earnings_since_start.items()]}")
            print(f"earnings_since_start_total: {earnings_since_start_total}")
            print(f"participants_table: {participants_table}")
            await user_message.forward(mining_channel)
            await mining_channel.send(mining_update_message_content,
                                      allowed_mentions=AllowedMentions.none())

    # Log the mining
    for timestamp, log_message in log_messages.items():
        if timestamp is None:
            print("ERROR: Could not get last block timestamp.")
            await terminate_bot()
        try:
            g.log.log(line=log_message, timestamp=timestamp)
            # Remove variables with common names to prevent accidental use
            del timestamp
        except Exception as e:
            print(f"ERROR: Error logging mining: {e}")
            await terminate_bot()

    # Validate the blockchain
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

    if g.network_mining_enabled is True:
        print(f"Miner {sender_name} ({sender_id}) has mined "
              f"for {receiver_name} ({receiver_id}) (message {message_id}).")
        print("--------------------")

    # Inform receiver about the coin if it's the first time they receive a coin
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
    mining_messages_enabled: bool = sender_save_data.mining_messages_enabled
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
    if user_message is None:
        user_message = await channel.fetch_message(message_id)
    if isinstance(casino_channel, PrivateChannel):
        raise ValueError("ERROR: casino_channel is a private channel.")
    elif casino_channel is None:
        raise ValueError("ERROR: casino_channel is None.")
    # Check if the receiver has permission to read messages in the channel
    # (if not, the bot will not reply to them and the user's save data will
    # not be changed)
    #
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
