# region Imports
# Standard library
from _collections_abc import dict_items
from typing import List, Dict, cast

# Third party
from discord import Interaction, Member, Role, User, app_commands
from discord.app_commands import Choice
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)
from sympy import (Float, Integer, Le, Eq, Gt, Piecewise, pretty,
                   simplify)  # pyright: ignore [reportUnknownVariableType]

# Local
import core.global_state as g
from models.slot_machine import SlotMachine
from .maintainer_main import maintainer_group
# endregion
# region /reels

assert g.bot is not None, "bot has not been initialized."
assert isinstance(g.bot, Bot), "bot has not been initialized."

add_or_remove_choices: List[Choice[str]] = [
    Choice(name="Add", value="add"),
    Choice(name="Remove", value="remove")
]
symbols_choices: List[Choice[str]] = [
    Choice(name="small_win", value="small_win"),
    Choice(name="medium_win", value="medium_win"),
    Choice(name="high_win", value="high_win"),
    Choice(name="jackpot", value="jackpot"),
    Choice(name="lose_wager", value="lose_wager")
]

reels_choices: List[Choice[str]] = [
    Choice(name="reel1", value="reel1"),
    Choice(name="reel2", value="reel2"),
    Choice(name="reel3", value="reel3")
]


@maintainer_group.command(name="reels",
                          description=("Design or inspect "
                                       f"the {g.Coin} Slot Machine reels"))
@app_commands.choices(add_or_remove_symbol=add_or_remove_choices)
@app_commands.describe(add_or_remove_symbol="Add or remove a symbol")
@app_commands.describe(symbol="The symbol to add or remove")
@app_commands.choices(symbol=symbols_choices)
@app_commands.describe(amount="Amount of symbols to add")
@app_commands.describe(reel="The reel to modify")
@app_commands.choices(reel=reels_choices)
@app_commands.describe(close_off="Close off the area so that others cannot "
                                 "see the reels")
async def reels(interaction: Interaction,
                add_or_remove_symbol: str | None = None,
                symbol: str | None = None,
                amount: int | None = None,
                reel: str | None = None,
                close_off: bool = True) -> None:
    """
    Design the slot machine reels by adding and removing symbols.
    After saving the changes, various statistics are calculated and displayed,
    namely:
    - The symbols and their amounts in each reel.
    - The total amount of symbol units in each reel.
    - The total amount of symbol units across all reels.
    - Probabilities of all possible outcomes in the game.
    - Expected total return.
    - Expected return.
    - RTP for different wagers.
    Only users with a role named "Administrator", "Admin",
    or "Slot Machine Technician" can utilize this command.

    Args:
        interaction: The interaction object representing the
        command invocation.

        add_symbol: add_symbol a symbol to the reels.
        Defaults to None.

        remove_symbol: Remove a symbol from the reels.
        Defaults to None.

        inspect: Doesn't do anything.
    """
    assert isinstance(g.slot_machine, SlotMachine), (
        "slot_machine has not been initialized.")
    # Check if user has the necessary role
    invoker: User | Member = interaction.user
    # IMPROVE Make a user-friendly command that just shows how many of each symbol there are (and their probabilities?)
    access_denied_message_content: str = ("Only slot machine technicians "
                                          "may look at the reels.")
    if not isinstance(invoker, Member):
        await interaction.response.send_message(
            access_denied_message_content, ephemeral=True)
        return
    invoker_roles: List[Role] = invoker.roles
    invoker_is_authorized: bool = False
    for role in invoker_roles:
        role_name: str = role.name
        role_name_lowercase: str = role_name.lower()
        invoker_role_allows_access: bool = (
            role_name_lowercase == "slot machine technician" or
            role_name_lowercase == "administrator" or
            role_name_lowercase == "admin")
        if invoker_role_allows_access:
            invoker_is_authorized = True
            break
    if not invoker_is_authorized:
        await interaction.response.send_message(
            access_denied_message_content, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=close_off)

    # Refresh reels config from file
    print("Reloading reels...")
    g.slot_machine.reels = g.slot_machine.load_reels()
    print("Reels reloaded.")

    # IMPROVE Add a set_symbol_amount parameter to change the value directly instead of adding or subtracting
    if (symbol or amount or reel) and not add_or_remove_symbol:
        print("add_or_remove_symbol is None.")
        message_content: str = (
            "You must specify whether you want to add or remove a symbol.")
        await interaction.followup.send(message_content,
                                        ephemeral=True)
        return
    if add_or_remove_symbol and not symbol in g.slot_machine.reels['reel1']:
        print(f"Invalid symbol '{symbol}'")
        await interaction.followup.send(f"Invalid symbol '{symbol}'",
                                        ephemeral=True)
        return
    elif (add_or_remove_symbol and reel and reel not in g.slot_machine.reels):
        print(f"Invalid reel '{reel}'")
        message_content: str = f"Invalid reel '{reel}'"
        await interaction.followup.send(message_content, ephemeral=True)
        return
    elif add_or_remove_symbol and reel:
        if amount is None:
            amount = 3
        elif amount % 3 != 0:
            await interaction.followup.send("The amount of symbols to add or "
                                            "remove must be a multiple of 3.",
                                            ephemeral=True)
            return
        adding_or_removing_label: str = (
            "Adding" if add_or_remove_symbol == "add" else "Removing")
        print(f"{adding_or_removing_label} symbol: {symbol}")
        print(f"Amount: {amount}")
        print(f"Reel: {reel}")
        if add_or_remove_symbol == "add":
            g.slot_machine.reels[reel][symbol] += amount
        else:
            g.slot_machine.reels[reel][symbol] -= amount
        print("Saving reels...")
        g.slot_machine.reels = g.slot_machine.reels
        print("Reels saved.")
    elif add_or_remove_symbol and not reel:
        if not symbol:
            # I wanted to move this to its own elif block to reduce nesting
            # (`if add_or_remove_symbol and not symbol`)
            # but the static type checker thought that 'symbol' could be None,
            # in the `add_or_remove_symbol and reel is None` block.
            # I still want to be able to run the command without parameters.
            print("No symbol specified.")
            await interaction.followup.send("No symbol specified.",
                                            ephemeral=True)
            return
        elif amount is None:
            amount = 3
        elif amount % 3 != 0:
            await interaction.followup.send(
                "If the `reels` parameter is not specified, the amount of"
                "symbols to add or remove must be a multiple of 3.",
                ephemeral=True)
            return
        per_reel_amount: int = int(amount / 3)
        adding_or_removing_label: str = (
            "Adding" if add_or_remove_symbol == "add" else "Removing")

        print(f"Adding symbol: {symbol}")
        print(f"Amount: {amount}")
        if add_or_remove_symbol == "add":
            g.slot_machine.reels['reel1'][symbol] += per_reel_amount
            g.slot_machine.reels['reel2'][symbol] += per_reel_amount
            g.slot_machine.reels['reel3'][symbol] += per_reel_amount
            print(f"Added {per_reel_amount} {symbol} to each reel.")
        elif add_or_remove_symbol == "remove":
            per_reel_amount: int = int(amount / 3)
            g.slot_machine.reels['reel1'][symbol] -= per_reel_amount
            g.slot_machine.reels['reel2'][symbol] -= per_reel_amount
            g.slot_machine.reels['reel3'][symbol] -= per_reel_amount
            print(f"Removed {per_reel_amount} {symbol} from each reel.")

        print("Saving reels...")
        g.slot_machine.reels = g.slot_machine.reels
        print(g.slot_machine.reels)
        print("Reels saved.")

    # TODO Report payouts
    amount_of_symbols: int = g.slot_machine.count_symbols()
    reel_amount_of_symbols: int
    reels_table: str = "### Reels\n"
    for reel_name, symbols in g.slot_machine.reels.items():
        reel_symbols: Dict[str, int] = cast(Dict[str, int], symbols)
        symbols_table: str = ""
        symbols_and_amounts: dict_items[str, int] = reel_symbols.items()
        for symbol, amount in symbols_and_amounts:
            symbols_table += f"{symbol}: {amount}\n"
        symbols_dict: Dict[str, int] = cast(Dict[str, int], symbols)
        reel_amount_of_symbols = sum(symbols_dict.values())
        reels_table += (f"**Reel \"{reel_name}\"**\n"
                        f"**Symbol**: **Amount**\n"
                        f"{symbols_table}"
                        "**Total**\n"
                        f"{reel_amount_of_symbols}\n\n")
    probabilities: Dict[str, Float] = g.slot_machine.probabilities
    probabilities_table: str = "**Outcome**: **Probability**\n"
    lowest_number_float = 0.0001
    lowest_number: Float = Float(lowest_number_float)
    probability_display: str = ""
    for symbol, probability in probabilities.items():
        if Le(probability, Float(0.0)):
            probability_display = "0%"
        elif Eq(probability, round(probability, Integer(4))):
            probability_display = f"{probability:.4%}"
        elif Gt(probability, lowest_number):
            probability_display = f"~{probability:.4%}"
        else:
            probability_display = f"<{lowest_number_float}%"
        probabilities_table += f"{symbol}: {probability_display}\n"

    ev: tuple[Piecewise, Piecewise] = (
        g.slot_machine.calculate_expected_value(silent=True))
    expected_return_ugly: Piecewise = ev[0]
    expected_return: str = (
        cast(str, pretty(expected_return_ugly))).replace("⋅", "")
    expected_total_return_ugly: Piecewise = ev[1]
    expected_total_return: str = (
        cast(str, pretty(expected_total_return_ugly,))).replace("⋅", "")
    wagers: List[int] = [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
        25, 50, 75, 99, 100, 500, 1000, 10000, 100000, 1000000]
    rtp_dict: Dict[int, str] = {}
    rtp_display: str | None = None
    rtp: Float
    for wager in wagers:
        rtp = (
            g.slot_machine.calculate_rtp(Integer(wager), silent=True))
        rtp_simple: Float = cast(Float, simplify(rtp))
        if rtp == round(rtp, Integer(4)):
            rtp_display = f"{rtp:.4%}"
        else:
            if Gt(rtp_simple, lowest_number):
                rtp_display = f"~{rtp:.4%}"
            else:
                rtp_display = f"<{str(lowest_number_float)}%"
        rtp_dict[wager] = rtp_display

    rtp_table: str = "**Wager**: **RTP**\n"
    for wager_sample, rtp_sample in rtp_dict.items():
        rtp_table += f"{wager_sample}: {rtp_sample}\n"

    message_content: str = ("### Reels\n"
                            f"{reels_table}\n"
                            "### Symbols total\n"
                            f"{amount_of_symbols}\n\n\n"
                            "### Probabilities\n"
                            f"{probabilities_table}\n\n"
                            "### Expected values\n"
                            "**Expected total return**\n"
                            f"{expected_total_return}\n\n"
                            "**Expected return**\n"
                            f"{expected_return}\n"
                            '-# "W" means wager\n\n'
                            "### RTP\n"
                            f"{rtp_table}")
    print(message_content)
    await interaction.followup.send(message_content, ephemeral=close_off)
    del message_content
# endregion
