# region Imports
# Third party
from discord import (Interaction, Member, User, TextChannel, VoiceChannel,
                     app_commands, CategoryChannel, ForumChannel, StageChannel,
                     DMChannel, GroupChannel, Thread)
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)

# Local
import core.global_state as g
from utils.blockchain_utils import transfer_coins
# endregion
# region /transfer
# assert bot is not None, "bot has not been initialized."
assert isinstance(g.bot, Bot), "bot has not been initialized."


@g.bot.tree.command(name="transfer",
                    description=f"Transfer {g.coins} to another user")
@app_commands.describe(amount=f"Amount of {g.coins} to transfer",
                       user=f"User to transfer the {g.coins} to",
                       purpose="Purpose of the transfer")
async def transfer(interaction: Interaction,
                   amount: int,
                   user: Member,
                   purpose: str | None = None) -> None:
    """
    Transfer a specified amount of coins to another user.

    Args:
        interaction: The interaction object representing the command invocation.
    """
    sender: User | Member = interaction.user
    sender_id: int = sender.id
    receiver: Member = user
    receiver_id: int = receiver.id
    channel: (
        VoiceChannel | StageChannel | TextChannel | ForumChannel |
        CategoryChannel | Thread | DMChannel | GroupChannel |
        None) = interaction.channel
    if channel is None:
        raise Exception("ERROR: channel is None.")
    channel_id: int = channel.id
    await transfer_coins(sender=sender,
                         receiver=receiver,
                         amount=amount,
                         purpose=purpose,
                         method="transfer",
                         channel_id=channel_id,
                         interaction=interaction,)
    del sender, sender_id, receiver, receiver_id, amount
# endregion
