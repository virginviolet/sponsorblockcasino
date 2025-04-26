# region Imports
# Standard library
from typing import Any, cast

# Third party
from numpy import ndarray
import pandas as pd
from discord import Interaction, Member, User, app_commands

# Local
import core.global_state as g
from commands.groups.leaderboard import leaderboard_slots_group
from utils.formatting import format_coin_label
from utils.smart_send_interaction_message import smart_send_interaction_message
# endregion

# region single_win


@leaderboard_slots_group.command(
    name="single_win",
    description=(
        f"See who has won the highest amount on the {g.Coin} Slot Machine"))
@app_commands.describe(
    ephemeral="Whether to send the message as ephemeral")
async def single_win(interaction: Interaction,
                     ephemeral: bool = False) -> None:
    """
    Command to show the single win (net win) leaderboard of the slots.
    """
    assert g.bot, (
        "Bot is not initialized.")
    assert g.decrypted_transactions_spreadsheet, (
        "Decrypted transactions spreadsheet is not initialized.")
    g.decrypted_transactions_spreadsheet.decrypt()
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)

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
    transactions_decrypted["Sender (normalized)"] = (
        transactions_decrypted["Sender"].astype(str).str.strip().str.lower()
    )
    slot_outcomes: pd.DataFrame = transactions_decrypted[
        (transactions_decrypted["Method"]
         == "slot_machine") &
        (transactions_decrypted["Sender (normalized)"]
         == casino_username.lower())]
    gamblers: dict[str, int] = {}
    gamblers_extracted: pd.Series[str | float] = slot_outcomes["Receiver"]
    unique_gamblers: ndarray[Any, Any] = (
        gamblers_extracted
        .unique())  # pyright: ignore[reportUnknownMemberType]
    for gambler in unique_gamblers:
        user_wins: pd.DataFrame = cast(pd.DataFrame, slot_outcomes[
            slot_outcomes["Receiver"] == gambler])
        highest_win: int = 0
        for _, row in (  # pyright: ignore[reportUnknownVariableType]
            user_wins.iterrows()):  # pyright: ignore[reportUnknownMemberType]
            amount_str: str = cast(str, row["Amount"])
            try:
                amount: int = int(amount_str)
                if amount > highest_win:
                    highest_win = amount
            except ValueError:
                print(f"ValueError: {row['Amount']}")
        if highest_win != 0:
            gamblers[gambler] = int(highest_win)
    gamblers = dict(sorted(
        gamblers.items(), key=lambda item: item[1], reverse=True))
    message_content: str = (f"## {g.Coin} Slot Machine leaderboard "
                            "\N{EN DASH} Single win\n")
    for i, (user_name, amount) in enumerate(gamblers.items(), start=1):
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
        has_sent_message = True
        if len(message_content) >= 2000 - 100:
            await smart_send_interaction_message(
                interaction, message_content, has_sent_message, ephemeral)
            has_sent_message = True
            message_content = ""
    if message_content != "":
        await smart_send_interaction_message(
            interaction, message_content, has_sent_message, ephemeral)
# endregion
