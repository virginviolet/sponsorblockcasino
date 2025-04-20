# region Imports
# Standard library
from hashlib import sha256

# Third party
from discord import Interaction, Member, app_commands, AllowedMentions
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)

# Local
import core.global_state as g
from utils.formatting import format_coin_label
from sponsorblockchain.models.blockchain import Blockchain

# region /balance
assert isinstance(g.bot, Bot), "bot has not been initialized."


@g.bot.tree.command(name="balance", description="Check your balance")
@app_commands.describe(user="User to check the balance")
@app_commands.describe(incognito="Do not display the balance publicly")
async def balance(interaction: Interaction,
                  user: Member | None = None,
                  incognito: bool = False) -> None:
    """
    Check the balance of a user. If no user is specified, the balance of the
    user who invoked the command is checked.

    Args:
        interaction: The interaction object representing the command invocation.

        user: The user to check the balance. Defaults to None.
    """
    from core.global_state import coins, blockchain
    assert isinstance(blockchain, Blockchain)
    user_to_check: str
    if user is None:
        user_to_check = interaction.user.mention
        user_id: int = interaction.user.id
    else:
        user_to_check = user.mention
        user_id: int = user.id

    # print(f"Getting balance for user {user_to_check} ({user_id})...")
    user_id_hash: str = sha256(str(user_id).encode()).hexdigest()
    balance: int | None = blockchain.get_balance(user=user_id_hash)
    message_content: str = ""
    if balance is None and user is None:
        message_content = f"You have 0 {coins}."
    elif balance is None:
        message_content = f"{user_to_check} has 0 " f"{coins}."
    elif user is None:
        coin_label: str = format_coin_label(balance)
        message_content = (f"You have {balance:,} {coin_label}."
                           ).replace(",", "\N{THIN SPACE}")
    else:
        coin_label: str = format_coin_label(balance)
        message_content = (f"{user_to_check} has {balance:,} {coin_label}."
                           ).replace(",", "\N{THIN SPACE}")
    await interaction.response.send_message(
        message_content,
        ephemeral=incognito, allowed_mentions=AllowedMentions.none())
    del user_id
    del balance
    del message_content
# endregion
