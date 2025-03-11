# region imports
from discord import (Interaction, PartialEmoji, TextChannel, VoiceChannel,
                     CategoryChannel, ForumChannel, StageChannel, Thread)
from discord.abc import PrivateChannel
from discord.ext.commands import Bot  # type: ignore
from core.global_state import (bot, Coin, coin, coin_emoji_id, coin_emoji_name,
                               casino_channel_id, blockchain_name)
# endregion

# region /about_coin
assert bot is not None, "bot is None."
assert isinstance(bot, Bot), "bot is not initialized."


@bot.tree.command(name=f"about_{coin.lower()}",
                  description=f"About {coin}")
async def about_coin(interaction: Interaction) -> None:
    """
    Command to display information about the coin.

    Args:
    interaction -- The interaction object representing the
                     command invocation.
     """
    coin_emoji = PartialEmoji(name=coin_emoji_name, id=coin_emoji_id)
    casino_channel: (VoiceChannel | StageChannel | ForumChannel |
                     TextChannel | CategoryChannel | Thread |
                     PrivateChannel |
                     None) = bot.get_channel(casino_channel_id)
    if isinstance(casino_channel, PrivateChannel):
        raise ValueError("casino_channel is a private channel.")
    elif casino_channel is None:
        raise ValueError("casino_channel is None.")
    casino_channel_mention: str = casino_channel.mention
    message_content: str = (f"## {Coin}\n"
                            f"{Coin} is a proof-of-yapping cryptocurrency "
                            f"that lives on the {blockchain_name}.\n"
                            f"To mine a {coin} for someone, react {coin_emoji} "
                            "to their message.\n"
                            "Check your balance by typing `/balance` in "
                            "the chat.\n"
                            "\n"
                            f"New players will be informed only once about {coin}. "
                            "But if you prefer that the bot does not reply to "
                            "new players when you mine their messages, type\n"
                            "`/mining disable_reaction_messages: True`.\n"
                            "\n"
                            f"You should come visit the {casino_channel_mention} "
                            "some time. You can play on the slot machines "
                            "there with the `/slots` command.\n"
                            "If you want to know more about the slot machines, "
                            "type `/slots show_help: True`.")
    await interaction.response.send_message(message_content, ephemeral=True)
    del message_content
# endregion
