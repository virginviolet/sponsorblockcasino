# region Imports
# Standard library
from typing import cast

# Third party
from discord import Interaction, app_commands
from discord.ext.commands import Bot  # type: ignore
from sympy import Float, Integer, simplify

# Local
import core.global_state as g
from models.slot_machine import SlotMachine
from utils.formatting import format_coin_label
from .slots_main import slots_group
# endregion

# region rtp


@slots_group.command(name="rtp",
                     description="Show the return to player percentage for "
                     "a given stake")
@app_commands.describe(stake="The stake to calculate the RTP for")
@app_commands.describe(private_room=(
    "Whether you want to book a private room or not"))
async def rtp(interaction: Interaction,
              stake: int,
              private_room: bool = True) -> None:
    """
    Show the return to player (RTP) percentage for a given wager.

    Parameters:
        interaction: The interaction object representing the command invocation.
        stake: The wager to calculate the RTP for.
        private_room: Whether to book a private room or not. Defaults to False.

    Returns:
        None

    Raises:
        AssertionError: If g.slot_machine has not been initialized.

    This command calculates the RTP percentage for the given stake and sends a
    message with the result. If the stake is zero, the RTP is displayed as "0%".
    If the RTP can be simplified to a value greater than 0.0001, it is displayed
    with four decimal places. Otherwise, it is displayed as less than 0.0001%.
    The message can be sent either publicly or privately based on the
    private_room parameter.
    """

    assert isinstance(g.slot_machine, SlotMachine), (
        "g.slot_machine has not been initialized.")
    if stake == 0:
        rtp_display = f"0%"
    else:
        wager = Integer(stake)
        rtp_fraction: Float = g.slot_machine.calculate_rtp(wager)
        rtp_simple: Float = cast(Float, simplify(rtp_fraction))
        lowest_number_float = 0.0001
        lowest_number: Float = Float(lowest_number_float)
        rtp_display: str
        if rtp_fraction == round(rtp_fraction, Integer(4)):
            rtp_display = f"{rtp_fraction:.4%}"
        else:
            if rtp_simple > lowest_number:
                rtp_display = f"~{rtp_fraction:.4%}"
            else:
                rtp_display = f"<{lowest_number_float}%"
    coin_label: str = format_coin_label(stake)
    message_content: str = g.slot_machine.make_message(
        f"-# RTP (stake={stake} {coin_label}): {rtp_display}")
    await interaction.response.send_message(message_content,
                                            ephemeral=private_room)
    del coin_label
    del message_content
    return
# endregion
