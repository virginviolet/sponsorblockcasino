# region Imports
# Standard library
from typing import Any, cast

# Third party
from numpy import ndarray
import pandas as pd
from discord import Interaction, Member, User, app_commands

# Local
import core.global_state as g
from commands.leaderboard import leaderboard_group
from utils.formatting import format_coin_label
from utils.smart_send_interaction_message import smart_send_interaction_message
# endregion

# region sponsor


@leaderboard_group.command(
    name="sponsor",
    description=f"Show the top sponsors of the {g.Coin} Casino.")
@app_commands.describe(
    private="Whether to show the leaderboard only to you.")
async def sponsor(interaction: Interaction,
                   private: bool = False) -> None:
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
    has_sent_message: bool = False
    invoker: User | Member = interaction.user
    invoker_name: str = invoker.name
    try:
        casino_house: User = await g.bot.fetch_user(g.casino_house_id)
    except Exception as e:
        print(f"Error fetching casino house: {e}")
        await interaction.response.send_message(
            "Error fetching casino house. Please try again later.",
            ephemeral=True)
        return
    casino_username: str = casino_house.name
    transactions_decrypted["Sender"] = transactions_decrypted[
        "Sender"]
    transactions_decrypted["Receiver"] = transactions_decrypted[
        "Receiver"]
    transactions_decrypted["Receiver (normalized)"] = (
        transactions_decrypted["Receiver"].astype(str).str.strip().str.lower()
    )
    donations: pd.DataFrame = transactions_decrypted[
        (transactions_decrypted["Receiver (normalized)"]
         == casino_username.lower()) &
        (transactions_decrypted[
            "Method"
        ].isin(  # pyright: ignore[reportUnknownMemberType]
            ["transfer", "transfer_aml"]))]
    donators: dict[str, int] = {}
    donators_extracted: pd.Series[str | float] = donations["Sender"]
    unique_senders: ndarray[Any, Any] = (
        donators_extracted \
            .unique())  # pyright: ignore[reportUnknownMemberType]
    for sender in unique_senders:
        total_amount: int = 0
        user_donations: pd.DataFrame = cast(pd.DataFrame, donations[
            donations["Sender"] == sender])
        user_donations_amounts: pd.Series[str] = user_donations["Amount"]
        for donation in user_donations_amounts:
            total_amount += int(donation)
        if total_amount != 0:
            donators[sender] = total_amount
    donators = dict(sorted(
        donators.items(), key=lambda item: item[1], reverse=True))
    message_content: str = f"## {g.Coin} Casino's top sponsors\n"
    for i, (user_name, amount) in enumerate(donators.items(), start=1):
        coin_label: str = format_coin_label(amount)
        entry: str = ""
        if amount > 0:
            entry = f"{i}. "
        if user_name == invoker_name:
            entry += (
                f"**{user_name}**\n"
                f"-# {amount:,} {coin_label}\n"
                "\n").replace(",", "\N{THIN SPACE}")
        else:
            entry += (
                f"{user_name}\n"
                f"-# {amount:,} {coin_label}\n"
                "\n").replace(",", "\N{THIN SPACE}")
        message_content += entry
        if len(message_content) >= 2000 - 100:
            await smart_send_interaction_message(
                interaction, message_content, has_sent_message, private)
            has_sent_message = True
            message_content = ""
    if message_content != "":
        await smart_send_interaction_message(
            interaction, message_content, has_sent_message, private)
# endregion
