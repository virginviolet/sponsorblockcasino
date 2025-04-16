# region imports
# Third party
from discord import (Interaction, PartialEmoji, TextChannel, VoiceChannel,
                     CategoryChannel, ForumChannel, StageChannel, Thread)
from discord.abc import PrivateChannel
# pyright: ignore [reportMissingTypeStubs]
from discord.ext.commands import Bot

# Local
import core.global_state as g
# endregion

# region /about_coin
assert isinstance(g.bot, Bot), "bot is not initialized."


@g.bot.tree.command(name=f"about_{g.coin.lower()}",
                    description=f"About {g.coin}")
async def about_coin(interaction: Interaction) -> None:
    """
    Command to display information about the coin.

    Args:
    interaction -- The interaction object representing the
                     command invocation.
     """
    assert isinstance(g.bot, Bot), "bot is not initialized."
    coin_emoji = PartialEmoji(name=g.coin_emoji_name, id=g.coin_emoji_id)
    casino_channel: (VoiceChannel | StageChannel | ForumChannel |
                     TextChannel | CategoryChannel | Thread |
                     PrivateChannel |
                     None) = g.bot.get_channel(g.casino_channel_id)
    if isinstance(casino_channel, PrivateChannel):
        raise ValueError("casino_channel is a private channel.")
    elif casino_channel is None:
        raise ValueError("casino_channel is None.")
    casino_channel_mention: str = casino_channel.mention
    # TODO Make /transfer clickable
    mining_channel: (TextChannel | VoiceChannel | StageChannel |
                     ForumChannel | CategoryChannel | Thread |
                     PrivateChannel |
                     None) = g.bot.get_channel(g.mining_updates_channel_id)
    if isinstance(mining_channel, PrivateChannel):
        raise ValueError("mining_channel is a private channel.")
    elif mining_channel is None:
        raise ValueError("mining_channel is None.")
    mining_channel_mention: str = mining_channel.mention
    mining_highlights_channel: (TextChannel | VoiceChannel | StageChannel |
                                ForumChannel | CategoryChannel | Thread |
                                PrivateChannel |
                                None) = g.bot.get_channel(
        g.mining_highlights_channel_id)
    if isinstance(mining_highlights_channel, PrivateChannel):
        raise ValueError("mining_highlights_channel is a private channel.")
    if mining_highlights_channel is None:
        raise ValueError("mining_highlights_channel is None.")
    mining_highlights_channel_mention: str = (
        mining_highlights_channel.mention)
    message_1_content: str = (f"## {g.Coin}\n"
                              f"**{g.Coin}** is a "
                              "proof-of-yapping cryptocurrency that lives on "
                              f"the {g.blockchain_name}.\n"
                              "### Mining\n"
                              f"To mine a {g.coin} for someone, "
                              f"react {coin_emoji} to their message.\n"
                              "Check your balance by typing `/balance` in "
                              "the chat.\n"
                              "### Mining settings\n"
                              f"New players will be informed only once "
                              f"about {g.coin}. "
                              "But if you prefer that the bot does not reply to "
                              "new players when you mine a coin for them, "
                              "type\n"
                              "`/mining settings "
                              "disable_reaction_messages: True`.\n")
    message_2_content: str = (f"### Network mining\n"
                              f"Mining is not only beneficial for the "
                              f"one who wrote the message, but also for the "
                              "miners. In other words, when you mine for "
                              f"someone, you stand a chance earn some {g.coins} "
                              "yourself. This is called network mining.\n"
                              "It works like this:\n"
                              f"The first time a message gets a {coin_emoji} "
                              f"reaction, the message author gets one {g.coin}. "
                              "The contributor (the user who added the reaction) "
                              f"gets 0 {g.coins} this time.\n"
                              f"The second time a message gets a {coin_emoji} "
                              f"reaction, the message author gets 2 {g.coins} "
                              f"and the first contributor gets 1 {g.coin}.\n"
                              f"The new contributor gets 0 {g.coins}.\n"
                              f"The third time a message gets a {coin_emoji} "
                              f"reaction, the message author gets 3 {g.coins}, "
                              f"the first contributor gets 2 {g.coins}, the "
                              f"second contributor gets 1 {g.coin}, and the "
                              f"new contributor gets 0 {g.coins}.\n"
                              "And so on.\n"
                              "The earlier you are to react, the more you may "
                              "earn.\n"
                              "Another way to put it: each time a message gets "
                              f"a {coin_emoji} reaction, each participant "
                              "get a number of coins equal to "
                              "the number of contributors minus the "
                              "participant's position in the list of "
                              "participants (the message author has position 0, "
                              "the first contributor has position 1, the second "
                              "has position 2, and so on). More formally: the "
                              "amount of coins you receive is\n"
                              "*n* - *i*, where *n* is the number of "
                              "contributors, and *i* is your position in the "
                              "list.\n"
                              "The total amount of coins mined is always a "
                              "so-called [triangular number]"
                              "(https://en.wikipedia.org/wiki/Triangular_number"
                              ").\n"
                              "When a message gets two or more reactions, the "
                              "bot will send a message in "
                              f"{mining_channel_mention}, "
                              "reporting on the progress.\n"
                              "If a message gets 5 or more reactions, the bot "
                              "will send a message in "
                              f"{mining_highlights_channel_mention}.\n"
                              "If you want to get notified of mining updates "
                              "that concern you, you can type\n"
                              "`/mining settings "
                              "enable_network_mining_mention: True`.\n"
                              "If you want notifications for "
                              f"{mining_highlights_channel_mention}, type\n"
                              "`/mining settings "
                              "enable_mentions_in_highlights: True`.\n")
    message_3_content: str = ("### Transfers\n"
                              f"You can transfer {g.coins} to someone else "
                              "by typing `/transfer`.\n"
                              f"### {g.coin} Casino\n"
                              "You should come visit "
                              f"the {casino_channel_mention} some time. You can "
                              "play on the slot machines there with "
                              "the `/slots insert_coins` command.\n"
                              "If you want to know more about how "
                              "the slot machine game works,\n"
                              "type `/slots show_help`.")
    await interaction.response.send_message(message_1_content, ephemeral=True)
    await interaction.followup.send(message_2_content, ephemeral=True)
    await interaction.followup.send(message_3_content, ephemeral=True)
    del message_1_content
# endregion
