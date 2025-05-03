# region Imports
# Third party
from discord import Interaction, app_commands

# Local
import core.global_state as g
from models.slot_machine import SlotMachine
from utils.formatting import format_coin_label
from .slots_main import slots_group
# endregion

# region jackpot


@slots_group.command(name="jackpot",
                     description="Check the current jackpot amount")
@app_commands.describe(private_room=(
    "Whether you want to book a private room or not"))
async def jackpot(interaction: Interaction,
                  private_room: bool = False) -> None:
    """
    Check the current jackpot amount.

    Parameters:
        interaction: The interaction object that triggered the command.
        private_room: Whether to send message as ephemeral. Defaults to None.

    Raises:
        AssertionError: If g.slot_machine has not been initialized.

    Returns:
        None
    """
    assert isinstance(g.slot_machine, SlotMachine), (
        "g.slot_machine has not been initialized.")
    # Check the jackpot amount
    jackpot_pool: int = g.slot_machine.jackpot
    coin_label: str = format_coin_label(jackpot_pool)
    message_header: str = g.slot_machine.header
    message_content: str = (
        f"{message_header}\n"
        f"-# JACKPOT: "
        f"{jackpot_pool:,} {coin_label}.").replace(",", "\N{THIN SPACE}")
    del coin_label
    await interaction.response.send_message(message_content,
                                            ephemeral=private_room)
    del message_content
    return
# endregion
