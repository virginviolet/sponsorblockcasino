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
# endregion

# region holder


@leaderboard_group.command(
    name="holder",
    description=f"Show the top {g.coin} holders")
@app_commands.describe(
    private="Whether to show the leaderboard only to you")
async def holder(interaction: Interaction,
                  private: bool = False) -> None:
    """
    Command to show the top holders of the coin.
    """
    assert g.bot, (
        "Bot is not initialized.")
    assert g.decrypted_transactions_spreadsheet, (
        "Decrypted transactions spreadsheet is not initialized.")
    if g.leaderboard_holder_blocked:
        if (g.donation_goal is not None and
                g.donation_goal.reward_setting_key
                == "leaderboard_holder_blocked"):
            message_content = (
                f"The {g.coin} holder leaderboard "
                "will be unlocked once the donation goal is met.\n"
                "-# Use `/donation_goal` to check the current progress.")
            private = False
        else:
            message_content = (
                f"The {g.coin} holder leaderboard "
                "is currently disabled. Please try again later.")
        await interaction.response.send_message(message_content,
                                                ephemeral=private)
        return
    await interaction.response.defer(thinking=True, ephemeral=private)
    g.decrypted_transactions_spreadsheet.decrypt()

    transactions_decrypted: pd.DataFrame = (
        pd.read_csv(  # pyright: ignore[reportUnknownMemberType]
            g.decrypted_transactions_spreadsheet.decrypted_spreadsheet_path,
            sep="\t", dtype={"Sender": str, "Receiver": str, "Method": str,
                             "Amount": str}))
    invoker: User | Member = interaction.user
    invoker_name: str = invoker.name
    transactions_decrypted["Sender"] = transactions_decrypted["Sender"]
    transactions_decrypted["Receiver"] = transactions_decrypted["Receiver"]
    transactions_decrypted["Receiver (normalized)"] = (
        transactions_decrypted["Receiver"].astype(str).str.strip().str.lower()
    )
    holder: dict[str, int] = {}
    senders_extracted: pd.Series[str | float] = (
        transactions_decrypted["Sender"])
    unique_senders: ndarray[Any, Any] = (
        senders_extracted
        .unique())  # pyright: ignore[reportUnknownMemberType]
    for sender in unique_senders:
        balance: int = 0
        user_receipts: (  # pyright: ignore[reportUnknownVariableType]
            pd.Series[str]) = transactions_decrypted[
            (transactions_decrypted["Receiver"] == sender)
        ]["Amount"]
        for receipt in (  # pyright: ignore[reportUnknownVariableType]
            user_receipts):
            receipt: str = cast(str, receipt)
            balance += int(receipt)
        user_remittances: (  # pyright: ignore[reportUnknownVariableType]
            pd.Series[str]) = transactions_decrypted[
            (transactions_decrypted["Sender"] == sender) &
            (transactions_decrypted["Method"] != "reaction") &
            (transactions_decrypted["Method"] != "reaction_network")
        ]["Amount"]
        for remittance in (  # pyright: ignore[reportUnknownVariableType]
            user_remittances):
            remittance: str = cast(str, remittance)
            balance -= int(remittance)
        if balance != 0:
            holder[sender] = balance
    holder = dict(sorted(
        holder.items(), key=lambda item: item[1], reverse=True))
    message_content: str = f"## Top {g.coin} holders\n"
    for i, (user_name, amount) in enumerate(holder.items(), start=1):
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
            await interaction.followup.send(
                message_content, ephemeral=private)
            message_content = ""
    if message_content != "":
        await interaction.followup.send(
            message_content, ephemeral=private)
# endregion
