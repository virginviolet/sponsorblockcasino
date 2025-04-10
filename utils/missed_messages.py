# region Imports
# Standard Library
from typing import Dict, List

# Third party 
from discord import Member, Emoji, PartialEmoji, User
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
from utils.process_reaction import process_reaction
# endregion
# region Missed msgs


async def process_missed_messages(limit: int | None = None) -> None:
    """
    This function iterates through all guilds and their text channels to fetch
    messages that were sent while the bot was offline. It processes reactions to
    these messages and updates checkpoints to keep track of the last processed
    message in each channel.

    This does not process reactions to messages older than the last checkpoint
    (i.e. older than the last message sent before the bot went offline). That
    would require keeping track of every single message and reactions on the
    server in a database.
    Parameters:
        limit (int, optional): Limit the maximum number of messages to fetch per
        channel. Defaults to None.
    Global Variables:
        all_channel_checkpoints (dict): A dictionary storing checkpoints for

        each channel.
    """
    missed_messages_processed_message: str = "Missed messages processed."
    assert isinstance(g.bot, Bot), "bot has not been initialized."
    print("Processing missed messages...")

    for guild in g.bot.guilds:
        print("Fetching messages from "
              f"guild: {guild.name} ({guild.id})...")
        for channel in guild.text_channels:
            channel_id: int = channel.id
            channel_name: str = channel.name
            print("Fetching messages from "
                  f"channel: {channel_name} ({channel_id})...")
            channel_checkpoints: List[Dict[str, int]] | None = (
                g.all_channel_checkpoints[channel.id].load())
            if channel_checkpoints is not None:
                print(f"Channel checkpoints loaded.")
            else:
                print("No checkpoints could be loaded.")
            new_channel_messages_found: int = 0
            fresh_last_message_id: int | None = None
            checkpoint_reached: bool = False
            # Fetch messages from the channel (reverse chronological order)
            try:
                async for message in channel.history(limit=limit):
                    message_id: int = message.id
                    if new_channel_messages_found == 0:
                        # The first message found will be the last message sent
                        # This will be used as the checkpoint
                        fresh_last_message_id = message_id
                    # print(f"{message.author}: "
                    #       f"{message.content} ({message_id}).")
                    if channel_checkpoints is not None:
                        for checkpoint in channel_checkpoints:
                            if message_id == checkpoint["last_message_id"]:
                                print("Channel checkpoint reached.")
                                checkpoint_reached = True
                                break
                        if checkpoint_reached:
                            break
                        new_channel_messages_found += 1
                        sender: Member | User
                        receiver: User | Member
                        for reaction in message.reactions:
                            async for user in reaction.users():
                                # print("Reaction found: "
                                #       f"{reaction.emoji}: {user}.")
                                # print(f"Message ID: {message_id}.")
                                # print(f"{message.author}: {message.content}")
                                sender = user
                                receiver = message.author
                                emoji: PartialEmoji | Emoji | str = (
                                    reaction.emoji)
                                await process_reaction(message_id=message_id,
                                                       emoji=emoji,
                                                       sender=sender,
                                                       receiver=receiver,
                                                       channel_id=channel_id,
                                                       channel=channel,
                                                       sender_message=message,
                                                       greet_new_players=False)
                    del message_id
            except Exception as e:
                channel_name: str = channel.name
                print("ERROR: Error fetching messages "
                      f"from channel {channel_name} ({channel.id}): {e}")
            print("Messages from "
                  f"channel {channel.name} ({channel.id}) fetched.")
            if fresh_last_message_id is None:
                print("WARNING: No channel messages found.")
            else:
                if new_channel_messages_found > 0:
                    print(f"Saving checkpoint: {fresh_last_message_id}")
                    g.all_channel_checkpoints[channel.id].save(
                        fresh_last_message_id)
                else:
                    print("Will not save checkpoint for this channel because "
                          "no new messages were found.")
        print(f"Messages from guild {guild.id} ({guild}) fetched.")
    print(missed_messages_processed_message)
    del missed_messages_processed_message

# endregion
