# region Imports
from _collections_abc import dict_items
from typing import List, Dict, cast
from discord import Interaction, Member, Role, User, app_commands, utils
from discord.ext.commands import Bot  # type: ignore
from sympy import Float, Integer, Eq, Gt, simplify, Piecewise, pretty
from core.global_state import bot, slot_machine
from models.slot_machine import SlotMachine
from type_aliases import Reels
# endregion

# region /reels

assert bot is not None, "bot has not been initialized."
assert isinstance(bot, Bot), "bot has not been initialized."


@bot.tree.command(name="reels",
                  description="Design the slot machine reels")
@app_commands.describe(add_symbol="Add a symbol to the reels")
@app_commands.describe(amount="Amount of symbols to add")
@app_commands.describe(remove_symbol="Remove a symbol from the reels")
@app_commands.describe(reel="The reel to modify")
@app_commands.describe(inspect="Inspect the reels")
@app_commands.describe(close_off="Close off the area so that others cannot "
                       "see the reels")
async def reels(interaction: Interaction,
                add_symbol: str | None = None,
                remove_symbol: str | None = None,
                amount: int | None = None,
                reel: str | None = None,
                close_off: bool = True,
                inspect: bool | None = None) -> None:
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
    Only users with the "Administrator" or "Slot Machine Technician" role
    can utilize this command.

    Args:
        interaction: The interaction object representing the
        command invocation.

        add_symbol: add_symbol a symbol to the reels.
        Defaults to None.

        remove_symbol: Remove a symbol from the reels.
        Defaults to None.

        inspect: Doesn't do anything.
    """
    assert isinstance(slot_machine, SlotMachine), (
        "slot_machine has not been initialized.")
    await interaction.response.defer(ephemeral=close_off)
    # Check if user has the necessary role
    invoker: User | Member = interaction.user
    invoker_roles: List[Role] = cast(Member, invoker).roles
    administrator_role: Role | None = (
        utils.get(invoker_roles, name="Administrator"))
    technician_role: Role | None = (
        utils.get(invoker_roles, name="Slot Machine Technician"))
    if technician_role is None and administrator_role is None:
        # TODO Maybe let other users see the reels
        message_content: str = ("Only slot machine technicians "
                                "may look at the reels.")
        await interaction.followup.send(message_content, ephemeral=True)
        del message_content
        return
    if amount is None:
        if reel is None:
            amount = 3
        else:
            amount = 1
    # BUG Refreshing the reels config from file is not working (have to restart instead)
    # Refresh reels config from file
    slot_machine.reels = slot_machine.load_reels()
    new_reels: Reels = slot_machine.reels
    if add_symbol and remove_symbol:
        await interaction.followup.send("You can only add or remove a "
                                        "symbol at a time.",
                                        ephemeral=True)
        return
    if add_symbol and reel is None:
        if amount % 3 != 0:
            await interaction.followup.send("The amount of symbols to "
                                            "add must be a multiple "
                                            "of 3.",
                                            ephemeral=True)
            return
    elif add_symbol and reel:
        print(f"Adding symbol: {add_symbol}")
        print(f"Amount: {amount}")
        print(f"Reel: {reel}")
        if (reel in slot_machine.reels and
                add_symbol in slot_machine.reels[reel]):
            slot_machine.reels[reel][add_symbol] += amount
        else:
            print(f"ERROR: Invalid reel or symbol '{reel}' or '{add_symbol}'")
    if add_symbol:
        print(f"Adding symbol: {add_symbol}")
        print(f"Amount: {amount}")
        if add_symbol in slot_machine.reels['reel1']:
            per_reel_amount: int = int(amount / 3)
            new_reels['reel1'][add_symbol] += per_reel_amount
            new_reels['reel2'][add_symbol] += per_reel_amount
            new_reels['reel3'][add_symbol] += per_reel_amount

            slot_machine.reels = new_reels
            print(f"Added {per_reel_amount} {add_symbol} to each reel.")
        else:
            print(f"ERROR: Invalid symbol '{add_symbol}'")
        print(slot_machine.reels)
        # if amount
    elif remove_symbol and reel:
        print(f"Removing symbol: {remove_symbol}")
        print(f"Amount: {amount}")
        print(f"Reel: {reel}")
        if (reel in slot_machine.reels and
                remove_symbol in slot_machine.reels[reel]):
            slot_machine.reels[reel][remove_symbol] -= amount
        else:
            print(f"ERROR: Invalid reel '{reel}' or symbol '{remove_symbol}'")
    elif remove_symbol:
        print(f"Removing symbol: {remove_symbol}")
        print(f"Amount: {amount}")
        if remove_symbol in slot_machine.reels['reel1']:
            per_reel_amount: int = int(amount / 3)
            new_reels['reel1'][remove_symbol] -= per_reel_amount
            new_reels['reel2'][remove_symbol] -= per_reel_amount
            new_reels['reel3'][remove_symbol] -= per_reel_amount

            slot_machine.reels = new_reels
            print(f"Removed {per_reel_amount} {remove_symbol} from each reel.")
        else:
            print(f"ERROR: Invalid symbol '{remove_symbol}'")
        print(slot_machine.reels)

    print("Saving reels...")

    slot_machine.reels = new_reels
    new_reels = slot_machine.reels
    # print(f"Reels: {slot_machine.configuration}")
    print(f"Probabilities saved.")

    # TODO Report payouts
    amount_of_symbols: int = slot_machine.count_symbols()
    reel_amount_of_symbols: int
    reels_table: str = "### Reels\n"
    for reel_name, symbols in new_reels.items():
        reel_symbols: Dict[str, int] = cast(Dict[str, int], symbols)
        symbols_table: str = ""
        symbols_and_amounts: dict_items[str, int] = reel_symbols.items()
        for symbol, amount in symbols_and_amounts:
            symbols_table += f"{symbol}: {amount}\n"
        symbols_dict: Dict[str, int] = cast(Dict[str, int], symbols)
        reel_amount_of_symbols = sum(symbols_dict.values())
        reels_table += (f"**Reel {reel_name}**\n"
                        f"**Symbol**: **Amount**\n"
                        f"{symbols_table}"
                        "**Total**\n"
                        f"{reel_amount_of_symbols}\n\n")
    probabilities: Dict[str, Float] = slot_machine.probabilities
    probabilities_table: str = "**Outcome**: **Probability**\n"
    lowest_number_float = 0.0001
    lowest_number: Float = Float(lowest_number_float)
    probability_display: str = ""
    for symbol, probability in probabilities.items():
        if Eq(probability, round(probability, Integer(4))):
            probability_display = f"{probability:.4%}"
        elif Gt(probability, lowest_number):
            probability_display = f"~{probability:.4%}"
        else:
            probability_display = f"<{lowest_number_float}%"
        probabilities_table += f"{symbol}: {probability_display}\n"

    ev: tuple[Piecewise, Piecewise] = slot_machine.calculate_expected_value()
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
            slot_machine.calculate_rtp(Integer(wager)))
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
