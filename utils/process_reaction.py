# region Imports
# Standard Library
from random import shuffle
from typing import List, Literal, Sequence

# Third party
from discord import (Member, Message, Emoji, PartialEmoji, Permissions, User,
                     TextChannel, VoiceChannel, CategoryChannel, ForumChannel,
                     StageChannel, Thread, Guild, AllowedMentions)
from discord.abc import PrivateChannel
from discord.ext.commands import Bot  # type: ignore
from discord.reaction import Reaction

# Local
from sponsorblockcasino_types import ReactionUser
import core.global_state as g
from core.terminate_bot import terminate_bot
from models.log import Log
from models.message_mining_registry import MessageMiningRegistryManager
from models.user_save_data import UserSaveData
from utils.blockchain_utils import (add_block_transaction,
                                    get_last_block_timestamp)
from utils.formatting import format_coin_label
# endregion

# region Coin reaction


async def process_reaction(message_id: int,
                           emoji: PartialEmoji | Emoji | str,
                           reacter: Member | User,
                           channel_id: int,
                           reacter_message: Message | None = None,
                           channel: (VoiceChannel | StageChannel |
                                     ForumChannel | TextChannel |
                                     CategoryChannel | Thread |
                                     PrivateChannel | None) = None,
                           message_author: Member | User | None = None,
                           message_author_id: int | None = None,
                           timestamp: float | None = None,
                           greet_new_players: bool = True) -> None:
    """
    Processes a reaction event to possibly mine a coin for a message author.

    Args:
        emoji: The emoji used in the reaction.
        reacter: The user who added the reaction.
        message_author: The user who receives the coin. Defaults to None.
        message_author_id: The ID of the user who receives the coin. Defaults
            to None.
    """
    # TODO Update docstring
    # region Assertions
    assert isinstance(g.bot, Bot), "g.bot has not been initialized."
    assert g.blockchain is not None and hasattr(
        g.blockchain, "add_block"), (
            "g.blockchain has not been initialized.")
    assert isinstance(g.log, Log), "g.log has not been initialized."
    assert isinstance(g.message_mining_registry,
                      MessageMiningRegistryManager), (
        "g.message_mining_registry has not been initialized.")
    # endregion

    # region Checks & variables
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

    if message_author is None:
        # Get message author from id
        if message_author_id is not None:
            message_author = await g.bot.fetch_user(message_author_id)
        else:
            raise ValueError("message_author_id is None.")
    else:
        message_author_id = message_author.id

    # Common variables (1/3)
    reacter_id: int = reacter.id

    if reacter_id == message_author_id:
        return

    # Common variables (2/3)
    reacter_name: str = reacter.name
    reacter_save_data: UserSaveData = UserSaveData(
        user_id=reacter_id, user_name=reacter_name)

    # Check if the user has mined for the message already
    message_mined_data: str | List[int] | bool | float | None = (
        reacter_save_data.load("messages_mined"))
    message_mined: List[int] = (
        message_mined_data if isinstance(message_mined_data, list) else [])
    if message_id in message_mined:
        return

    # Common variables (3/3)
    message_author_name: str = message_author.name
    if channel is None:
        channel = g.bot.get_channel(channel_id)
    last_block_timestamp: float | None = None
    log_messages: dict[float | None, str] = {}
    reacter_mention: str = reacter.mention
    reacter_global_name: str | None = reacter.global_name
    mined_for_log_message: str
    bot_channel_permissions: Permissions | None = None
    bot_can_read_history: bool | None = None
    bot_can_read_messages: bool | None = None

    if channel is None:
        raise ValueError("ERROR: Could not process reaction because "
                         "channel is None.")
    if not isinstance(channel, (VoiceChannel, TextChannel, Thread)):
        print("WARNING: "
              f"Skipping reaction because channel is {type(channel)}.")
        return

    if reacter_message is None:
        # TODO Check which permissions are needed to fetch a message
        bot_channel_permissions = channel.permissions_for(channel.guild.me)
        bot_can_read_history = bot_channel_permissions.read_message_history
        if not bot_can_read_history:
            print("WARNING: Will not send reaction message "
                  "because bot does not have permission to read message "
                  f"history in channel {channel}.")
            return
        bot_can_read_messages = bot_channel_permissions.read_messages
        if not bot_can_read_messages:
            print("WARNING: Will not send reaction message "
                  "because bot does not have permission to read messages "
                  f"in channel {channel}.")
            return
        try:
            reacter_message = await channel.fetch_message(message_id)
        except Exception as e:
            raise ValueError("ERROR: "
                             f"Could not fetch message {message_id}: {e}")
    # endregion

    # region Register
    # Add the message ID to the user's list of messages mined for
    # Doing this before rather than after the transaction
    # as an anti-cheating precaution
    message_mined.append(message_id)
    reacter_save_data.save(key="messages_mined", value=message_mined)
    # endregion

    if g.network_mining_enabled is False:
        # region Classic mining
        print(f"{reacter} ({reacter_id}) is mining 1 {g.coin} "
              f"for {message_author} ({message_author_id})...")

        await add_block_transaction(blockchain=g.blockchain,
                                    sender=reacter,
                                    receiver=message_author,
                                    amount=1,
                                    method="reaction")

        # Set variables for logging
        last_block_timestamp = get_last_block_timestamp()
        mined_for_log_message = (f"{reacter} ({reacter_id}) mined 1 {g.coin} "
                                 f"for {message_author} "
                                 f"({message_author_id}).")
        log_messages[last_block_timestamp] = mined_for_log_message
        del last_block_timestamp
        del mined_for_log_message
        # endregion
    else:
        # region Network mining
        print("--------------------")
        print(f"Contributor {reacter} ({reacter_id}) is mining for "
              f"{message_author} ({message_author_id}) "
              f"(message {message_id})...")

        # Find any existing miners for the message
        coin_reacters: List[Member | User | ReactionUser] = []
        coin_reacters_from_registry: List[ReactionUser] = (
            g.message_mining_registry.get_reacters(message_id, sort=True))
        # Add reactions missing from the registry
        # They are sorted by user ID in descending order and cannot be
        # sorted chronologically (at least with Discord.py 2.5.2)
        # As missing reactions likely are from before the network mining
        # update, we place them before the new miner
        reactions: List[Reaction] = reacter_message.reactions
        coin_reacters_from_discord: List[Member | User | ReactionUser] = []
        for reaction in reactions:
            reaction_emoji: PartialEmoji | Emoji | str = reaction.emoji
            if not isinstance(reaction_emoji, (Emoji, PartialEmoji)):
                continue
            reaction_emoji_id: int | None = reaction_emoji.id
            if reaction_emoji_id == g.coin_emoji_id:
                coin_reacters_ids: List[int] = [
                    r.id for r in coin_reacters_from_registry]
                async for user in reaction.users():
                    user_id: int = user.id
                    if ((user_id not in coin_reacters_ids) and
                        (user_id != message_author_id) and
                            (user_id != reacter_id)):
                        coin_reacters_from_discord.append(user)
                break
        # Randomize the order of the old reacters
        # (otherwise the ones with lowest user ids would get most coins,
        # which would be unfair if it doesn't correlate with the order they
        # reacted in)
        shuffle(coin_reacters_from_discord)
        # Add them to the mining registry so that the order can be preserved
        # (otherwise the reacters are shuffled anew each time a new reaction
        # is added, which would actually be fair, but it would also be
        # confusing for the users)
        message_timestamp: float = reacter_message.created_at.timestamp()
        if timestamp is None:
            raise ValueError("ERROR: Timestamp is None.")
        coin_reacters_from_discord_count: int = len(coin_reacters_from_discord)
        for i, coin_reacter in enumerate(coin_reacters_from_discord):
            coin_reacter_id: int = coin_reacter.id
            coin_reacter_name: str = coin_reacter.name
            coin_reacter_global_name: str | None = coin_reacter.global_name
            coin_reacter_mention: str = coin_reacter.mention
            # Subtract 1 second from the message timestamp
            # for each coin reacter
            # so that the order is preserved
            seconds_to_subtract: float = coin_reacters_from_discord_count - i
            reaction_timestamp: float = timestamp - seconds_to_subtract
            g.message_mining_registry.add_reaction(
                message_id=message_id,
                message_timestamp=message_timestamp,
                message_author_id=message_author_id,
                message_author_name=message_author_name,
                channel_id=channel_id,
                user_id=coin_reacter_id,
                user_name=coin_reacter_name,
                user_global_name=coin_reacter_global_name,
                user_mention=coin_reacter_mention,
                created_at=reaction_timestamp)
        # Add the current reaction to the message mining registry
        g.message_mining_registry.add_reaction(
            message_id=message_id,
            message_timestamp=message_timestamp,
            message_author_id=message_author_id,
            message_author_name=message_author_name,
            channel_id=channel_id,
            user_id=reacter_id,
            user_name=reacter_name,
            user_global_name=reacter_global_name,
            user_mention=reacter_mention,
            created_at=timestamp)
        reacter_reaction_user: ReactionUser = ReactionUser(
            global_name=reacter_global_name,
            id=reacter_id,
            name=reacter_name,
            mention=reacter_mention)
        # Only in the edge case that there are existing reacters
        # for the message in the registry _and_ we discover new ones with
        # discord.py does it matter which which list we append first.
        # Because time does not go backwards, the existing
        # reacters in the registry are likely to have an older timestamp than
        # the ones we just discovered with discord.py and added to the registry
        # with a very new timestamp. Therefore, we append the ones that were
        # already in the registry first.
        # Otherwise, the order will not be the same next time someone reacts
        # and the get_reacters method sorts them for us.
        coin_reacters.extend(coin_reacters_from_registry)
        coin_reacters.extend(coin_reacters_from_discord)
        coin_reacters.append(reacter_reaction_user)
        coin_reacters_from_registry.append(reacter_reaction_user)

        reacters_count: int = len(coin_reacters)

        # Create dictionary for immediate handout of coins
        earnings: dict[Member | User | ReactionUser, int] = {}
        # Add the message author as the first entry
        # (they should get the most coins)
        earnings[message_author] = 0
        for miner in coin_reacters:
            earnings[miner] = 0
        # Add values to the keys in the earnings dictionary
        for i, participant in enumerate(earnings.keys()):
            participant_id: int = participant.id
            # Each subsequent reacter gets one less coin than the previous one
            # The most recent one (the "reacter") gets 0 coins
            coins_to_give: int = reacters_count - i
            earnings[participant] = coins_to_give

        # Add transaction blocks and set variables for logging
        for i, (participant, coins) in enumerate(earnings.items()):
            # Add block
            if coins <= 0:
                continue
            participant_id: int = participant.id
            participant_name: str = participant.name
            coin_label: str = format_coin_label(coins)
            method: Literal["reaction", "reaction_network"]
            if participant_id == message_author_id:
                method = "reaction"
                print(f"{reacter_name} ({reacter_id}) is mining "
                      f"for {message_author_name}, and "
                      f"author {message_author_name} ({message_author_id}) is "
                      f"earning {coins} {coin_label} "
                      f"(message {message_id})...")
            else:
                method = "reaction_network"
                print(f"{reacter_name} ({reacter_id}) is mining "
                      f"for {message_author_name}, and "
                      f"miner #{i} {participant_name} ({participant_id}) "
                      f"is earning {coins} {coin_label} from having mined for "
                      f"the same message earlier (message {message_id}).")
            await add_block_transaction(blockchain=g.blockchain,
                                        sender=reacter,
                                        receiver=participant,
                                        amount=coins,
                                        method=method)

            # Set variables for logging
            last_block_timestamp = get_last_block_timestamp()
            if last_block_timestamp is None:
                print("ERROR: Could not get last block timestamp.")
                await terminate_bot()
            earned_message: str
            if participant_id == message_author_id:
                earned_message = (
                    f"{reacter_name} ({reacter_id}) mined "
                    f"for {message_author_name}, "
                    f"and author {message_author_name} ({message_author_id}) "
                    f"earned {coins} {coin_label} (message {message_id}).")
            else:
                earned_message = (
                    f"{reacter_name} ({reacter_id}) mined "
                    f"for {message_author_name}, "
                    f"and miner #{i} {participant_name} ({participant_id}) "
                    f"earned {coins} {coin_label} from having mined for the "
                    f"same message earlier (message {message_id}).")
            log_messages[last_block_timestamp] = earned_message
            del last_block_timestamp
            del earned_message

        allowed_network_mining_mentions_seq: (
            Sequence[Member | User | ReactionUser]) = []
        allowed_network_mining_highlights_mentions_seq: (
            Sequence[Member | User | ReactionUser]) = []
        allowed_network_mining_mentions: AllowedMentions = (
            AllowedMentions.none())
        allowed_network_mining_highlights_mentions: AllowedMentions = (
            AllowedMentions.none())
        forwarded_reacter_message: Message | None = None
        mining_update_message_content: str | None = None
        if reacters_count > 1:
            # Make an update in the mining updates channel
            mining_channel: (VoiceChannel | StageChannel | ForumChannel |
                             TextChannel | CategoryChannel | Thread |
                             PrivateChannel |
                             None) = g.bot.get_channel(
                g.mining_updates_channel_id)
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
                earnings_since_start: (
                    dict[Member | User | ReactionUser, int]) = {}
                earnings_since_start = {
                    participant: 0 for participant in earnings.keys()}
                participants = list(earnings.keys())
                for reaction in range(len(earnings.keys())):
                    for i in range(reaction):
                        participant: Member | User | ReactionUser = (
                            participants[i])
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
                    participant_id: int = participant.id
                    participant_save_data: UserSaveData = UserSaveData(
                        user_id=participant.id,
                        user_name=participant.name)
                    participant_mention_preference: bool = (
                        participant_save_data
                        .network_mining_mentions_enabled)
                    if ((participant_mention_preference is True) and
                            (participant_id != reacter_id)):
                        allowed_network_mining_mentions_seq.append(participant)
                    participant_highlights_mention_preference: bool = (
                        participant_save_data
                        .network_mining_highlights_mentions_enabled)
                    if ((participant_highlights_mention_preference is True) and
                            (participant_id != reacter_id)):
                        allowed_network_mining_highlights_mentions_seq.append(
                            participant)
                    participant_mention: str = participant.mention
                    coins_since_start: int = earnings_since_start[participant]
                    participant_id: int = participant.id
                    title: str = ("Author"
                                  if participant_id == message_author_id
                                  else f"Contributor #{i}")
                    participants_table += (
                        f"{title}: {participant_mention}: "
                        f"{coins_since_start} (+{participant_coins})\n")
                # The type checker expects the value of the users parameter
                # to be a boolean or a sequence of snowflakes. In reality, it
                # does not need to be a proper snowflake, as long as it has
                # an "id" attribute. Adding diagnostic suppression is the
                # easiest solution.
                allowed_network_mining_mentions = (
                    AllowedMentions(
                        users=(
                            allowed_network_mining_mentions_seq
                        )  # pyright: ignore[reportArgumentType]
                    ))
                allowed_network_mining_highlights_mentions = (
                    AllowedMentions(
                        users=(allowed_network_mining_highlights_mentions_seq
                               )  # pyright: ignore[reportArgumentType]
                    ))
                message_author_mention: str = message_author.mention
                mining_update_message_content = (
                    f"A total of {earnings_since_start_total} {coin_label} "
                    f"has been mined for {message_author_mention}'s message!\n"
                    f"{participants_table}")
                del coin_label
                forwarded_reacter_message = (
                    await reacter_message.forward(mining_channel))
                await mining_channel.send(
                    mining_update_message_content,
                    allowed_mentions=(
                        allowed_network_mining_mentions))
        if reacters_count >= 5:
            highlights_channel: (VoiceChannel | StageChannel |
                                 ForumChannel | TextChannel |
                                 CategoryChannel | Thread |
                                 PrivateChannel |
                                 None) = g.bot.get_channel(
                g.mining_highlights_channel_id)
            if highlights_channel is None:
                print("WARNING: Will not forward mining update "
                      "to highlights_channel because highlights_channel is "
                      "None.")
            elif not isinstance(
                    highlights_channel, (VoiceChannel, TextChannel, Thread)):
                print("WARNING: Will not forward mining update "
                      f"to highlights_channel because highlights_channel is "
                      f"{type(highlights_channel)}.")
            elif forwarded_reacter_message is None:
                print("WARNING: Will not forward mining update "
                      "to highlights_channel because "
                      "forwarded_reacter_message is None.")
            elif mining_update_message_content is None:
                print("WARNING: Will not forward mining update "
                      "to highlights_channel because "
                      "mining_update_message_content is None.")
            else:
                await forwarded_reacter_message.forward(highlights_channel)
                await highlights_channel.send(
                    mining_update_message_content,
                    allowed_mentions=(
                        allowed_network_mining_highlights_mentions))

    # region Finalize mining
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
        print(f"Contributor {reacter_name} ({reacter_id}) has mined "
              f"for {message_author_name} ({message_author_id}) "
              f"(message {message_id}).")
        print("--------------------")
    # endregion

    # region Info message
    # Inform message_author about the coin
    # if it's the first time they receive a coin
    if not greet_new_players:
        return
    if g.reaction_messages_enabled is False:
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
    mining_messages_enabled: bool = reacter_save_data.mining_messages_enabled
    about_command_formatted: str | None = (
        g.about_command_formatted)
    if about_command_formatted is None:
        error_message = ("ERROR: `about_command_formatted` is None. This "
                         "usually means that the commands have not been "
                         "synced with Discord yet.")
        raise ValueError(error_message)
    if not mining_messages_enabled:
        return
    save_data_message_author: UserSaveData = UserSaveData(
        user_id=message_author_id, user_name=message_author_name)
    del message_author_name
    informed_about_coin_reactions: bool = (
        save_data_message_author.reaction_message_received)
    if informed_about_coin_reactions:
        return
    casino_channel: (VoiceChannel | StageChannel | ForumChannel |
                     TextChannel | CategoryChannel | Thread |
                     PrivateChannel |
                     None) = g.bot.get_channel(g.casino_channel_id)
    if isinstance(casino_channel, PrivateChannel):
        raise ValueError("ERROR: casino_channel is a private channel.")
    elif casino_channel is None:
        raise ValueError("ERROR: casino_channel is None.")

    if bot_channel_permissions is None:
        # TODO Check which permissions are needed to send a message
        bot_channel_permissions = channel.permissions_for(channel.guild.me)
    bot_can_read_history = bot_channel_permissions.read_message_history
    if not bot_can_read_history:
        print("WARNING: Will not send reaction message "
              "because bot does not have permission to read message "
              f"history in channel {channel}.")
        return
    bot_can_read_messages = bot_channel_permissions.read_messages
    if not bot_can_read_messages:
        print("WARNING: Will not send reaction message "
              "because bot does not have permission to read messages "
              f"in channel {channel}.")
        return
    bot_can_send_messages: bool
    if isinstance(channel, Thread):
        bot_can_send_messages = (
            channel.permissions_for(
                channel.guild.me).send_messages_in_threads)
        if not bot_can_send_messages:
            print("WARNING: Will not send reaction message "
                  "because bot does not have permission to send messages "
                  f"in threads in channel {channel}.")
            return
    else:
        bot_can_send_messages: bool = (
            channel.permissions_for(channel.guild.me).send_messages)
        if not bot_can_send_messages:
            print("WARNING: Will not send reaction message "
                  "because bot does not have permission to send messages "
                  f"in channel {channel}.")
            return
    try:
        user_message: Message = await channel.fetch_message(message_id)
    except Exception as e:
        raise ValueError(
            f"Could not fetch message {message_id} from "
            f"channel {channel}: {e}")
    # Check if the message author has permission to read messages in
    # the channel
    # (if not, the bot will not reply to them and the user's save data will
    # not be changed)
    # The permissions_for() method only works for Member objects,
    # not User objects, so we need to get the Member object if
    # the message author is a User.
    message_author_member: Member | None
    if isinstance(message_author, Member):
        message_author_member = message_author
    else:
        # message_author is a User
        # Try to get member object from the guild
        if hasattr(channel, "guild"):
            guild: Guild = channel.guild
            message_author_member = guild.get_member(message_author_id)
            # If not in cache, fetch from API
            if message_author_member is None:
                message_author_member = (
                    await guild.fetch_member(message_author_id))
        else:
            message_author_member = None
    if message_author_member is None:
        print("WARNING: Could not get member object for message author.")
        return
    author_can_read_messages: bool = (
        channel.permissions_for(message_author_member).view_channel and
        channel.permissions_for(message_author_member).read_messages)
    if not author_can_read_messages:
        print(f"Will not consider replying to {message_author} because "
              f"they do not have permission to channel {channel}.")
        return
    reacter_mention: str = reacter.mention
    message_content: str = (f"-# {reacter_mention} has "
                            f"mined a {g.coin} for you! "
                            f"Enter {about_command_formatted} "
                            "in the chat box to learn more.")
    try:
        await user_message.reply(message_content,
                                 allowed_mentions=AllowedMentions.none())
        del user_message
        del message_content
        del channel
        del channel_id
        del reacter_mention
        save_data_message_author.reaction_message_received = True
    except Exception as e:
        raise ValueError(
            f"Could not send reaction message to {message_author}: {e}")
# endregion
