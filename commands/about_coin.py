# region imports
# Third party
from discord import (Interaction, PartialEmoji, TextChannel, VoiceChannel,
                     CategoryChannel, ForumChannel, StageChannel, Thread)
from discord.abc import PrivateChannel
from discord.ext.commands import Bot  # type: ignore

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
    message_content: str = (f"## {g.Coin}\n"
                            f"{g.Coin} is a proof-of-yapping cryptocurrency "
                            f"that lives on the {g.blockchain_name}.\n"
                            f"To mine a {g.coin} for someone, react {coin_emoji} "
                            "to their message.\n"
                            "Check your balance by typing `/balance` in "
                            "the chat.\n"
                            "\n"
                            f"New players will be informed only once about {g.coin}. "
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
