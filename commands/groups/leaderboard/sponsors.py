# region Imports
# Standard library
from typing import Any, cast

# Third party
from numpy import ndarray
import pandas as pd
from discord import Interaction, Member, User, app_commands

# Local
import core.global_state as g
from commands.groups.leaderboard import leaderboard_group
from utils.formatting import format_coin_label
from utils.smart_send_interaction_message import smart_send_interaction_message
# endregion

# region sponsors


@leaderboard_group.command(
    name="sponsors",
    description=f"See who's the {g.Coin} Casnio's top sponsors")
@app_commands.describe(
    ephemeral="Whether to send the message as ephemeral")
async def sponsors(interaction: Interaction,
                   ephemeral: bool = False) -> None:
    """
    Command to show the top sponsors of the casino.
    """
    assert g.bot, (
        "Bot is not initialized.")
    assert g.decrypted_transactions_spreadsheet, (
        "Decrypted transactions spreadsheet is not initialized.")
    g.decrypted_transactions_spreadsheet.decrypt()

    transactions_decrypted: pd.DataFrame = (
        pd.read_csv(  # pyright: ignore[reportUnknownMemberType]
            g.decrypted_transactions_spreadsheet.decrypted_spreadsheet_path,
            sep="\t", dtype={"Sender": str, "Receiver": str, "Method": str,
                             "Amount": str}))
    print("Decrypted transactions:\n"
          f"{transactions_decrypted}")
    has_sent_message: bool = False
    invoker: User | Member = interaction.user
    invoker_name: str = invoker.name
    casino_house: User = await g.bot.fetch_user(g.casino_house_id)
    casino_username: str = casino_house.name
    print(f"Casino house: '{casino_username}'")
    transactions_decrypted["Sender"] = transactions_decrypted[
        "Sender"].astype(str).str.strip()
    transactions_decrypted["Receiver"] = transactions_decrypted[
        "Receiver"].astype(str).str.strip()
    sponsors_extracted: pd.DataFrame = transactions_decrypted[
        (transactions_decrypted["Receiver"] == casino_username) &
        ((transactions_decrypted["Method"] == "transfer") |
         (transactions_decrypted["Method"] == "transfer_aml"))]
    print("Sponsors extracted:\n"
          f"{sponsors_extracted}")
    sponsors: dict[str, int] = {}
    senders_extracted: pd.Series[str | float] = sponsors_extracted["Sender"]
    print("Senders extracted:\n"
          f"{senders_extracted}")
    unique_senders: ndarray[Any, Any] = (
        senders_extracted.unique())  # pyright: ignore[reportUnknownMemberType]
    print("Unique senders:\n"
          f"{unique_senders}")
    for sponsor in unique_senders:
        total_amount: int = 0
        donations: pd.DataFrame = cast(pd.DataFrame, sponsors_extracted[
            sponsors_extracted["Sender"] == sponsor])
        donations_amounts: pd.Series[str] = donations["Amount"]
        for donation in donations_amounts:
            total_amount += int(donation)
        if total_amount != 0:
            sponsors[sponsor] = total_amount
    sponsors = dict(sorted(
        sponsors.items(), key=lambda item: item[1], reverse=True))
    print("Sponsors:\n"
          f"{sponsors}")
    message_content: str = f"## {g.Coin} Casino's top sponsors\n"
    for i, (user_name, amount) in enumerate(sponsors.items(), start=1):
        coin_label: str = format_coin_label(amount)
        entry: str = ""
        if amount > 0:
            entry = f"{i}. "
        if user_name == invoker_name:
            entry += (
                f"**{user_name}**\n"
                f"-# {amount} {coin_label}\n"
                "\n")
        else:
            entry += (
                f"{user_name}\n"
                f"-# {amount} {coin_label}\n"
                "\n")
        print(f"Entry:\n"
              f"{entry}")
        message_content += entry
        if len(message_content) >= 2000 - 100:
            await smart_send_interaction_message(
                interaction, message_content, has_sent_message, ephemeral)
            has_sent_message = True
            message_content = ""
    if message_content != "":
        await smart_send_interaction_message(
            interaction, message_content, has_sent_message, ephemeral)
# endregion
