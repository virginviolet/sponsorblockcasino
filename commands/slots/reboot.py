# region Imports
# Standard library
import asyncio
import math
from time import time

# Third party
from discord import Interaction, app_commands, User, Member

# Local
import core.global_state as g
from bot_configuration import invoke_bot_configuration
from models.message_mining_registry import MessageMiningRegistryManager
from models.slot_machine import SlotMachine
from models.slot_machine_high_scores import SlotMachineHighScores
from models.grifter_suppliers import GrifterSuppliers
from models.transfers_waiting_approval import TransfersWaitingApproval
from .slots_main import slots_group
from .slots_utils import remove_from_active_players
# endregion

# region reboot


@slots_group.command(name="reboot",
                     description="Restart the slot machine")
@app_commands.describe(private_room=(
    "Whether you want to book a private room or not"))
async def reboot(interaction: Interaction,
                 private_room: bool = False) -> None:
    """
    Refresh configuration and reinitialize classes, and remove the invoker
    from the active players list if they are stuck in it.
    Parameters:
        interaction: The interaction object representing the command invocation.
        private_room: Whether to book a private room or not. Defaults to None.
    Raises:
        AssertionError: If g.slot_machine has not been initialized.
    Returns:
        None
    """
    assert isinstance(g.slot_machine, SlotMachine), (
        "g.slot_machine has not been initialized")
    message_content: str
    message_content = g.slot_machine.make_message(
        f"-# The {g.Coin} Slot Machine is restarting...")
    await interaction.response.send_message(message_content,
                                            ephemeral=private_room)
    await asyncio.sleep(4)
    # Refresh configuration and reinitialize classes
    invoke_bot_configuration()
    g.slot_machine = SlotMachine()
    g.grifter_suppliers = GrifterSuppliers()
    g.transfers_waiting_approval = TransfersWaitingApproval()
    g.message_mining_registry = MessageMiningRegistryManager()
    g.slot_machine_high_scores = SlotMachineHighScores()

    # Remove invoker from active players in case they are stuck in it
    # Multiple checks are put in place to prevent cheating
    bootup_message: str = f"-# Welcome to the {g.Coin} Casino!"
    current_time: float = time()
    user: User | Member = interaction.user
    user_id: int = user.id
    when_player_added_to_active_players: float | None = (
        g.active_slot_machine_players.get(user_id))
    if when_player_added_to_active_players is not None:
        seconds_since_added: float = (
            current_time - when_player_added_to_active_players)
        del current_time
        min_wait_time_to_unstuck: int = g.starting_bonus_timeout * 2 - 3
        print(f"User {user_id} has been in active players for "
              f"{seconds_since_added} seconds. Minimum wait time to "
              f"unstuck: {min_wait_time_to_unstuck} seconds.")
        if seconds_since_added < min_wait_time_to_unstuck:
            wait_time: int = (
                math.ceil(min_wait_time_to_unstuck - seconds_since_added))
            print(f"Waiting for {wait_time} seconds "
                  f"to unstuck user {user_id}.")
            await asyncio.sleep(wait_time)
        when_player_added_double_check: float | None = (
            g.active_slot_machine_players.get(user_id))
        if when_player_added_double_check is not None:
            when_added_unchanged: bool = (
                when_player_added_double_check ==
                when_player_added_to_active_players)
            if when_added_unchanged:
                # If the timestamp has changed, that means that the user
                # has run /slots while the machine is "rebooting",
                # which could indicate that they are trying to cheat.
                # If their ID is still in the dictionary and the timestamp
                # hasn't changed,
                # remove the user from the dictionary
                user_name: str = user.name
                await remove_from_active_players(interaction, user_id)
                print(f"User {user_name} ({user_id}) removed from "
                      "active players.")
                del user_name
            else:
                print("Timestamp changed. "
                      "Will not remove user from active players.")
                bootup_message = (f"Cheating is illegal.\n"
                                  f"-# Do not use the {g.Coin} Slot Machine "
                                  "during reboot.")
        else:
            print("User not in active players anymore.")
    else:
        print("User not in active players.")
    message_content = g.slot_machine.make_message(bootup_message)
    await interaction.edit_original_response(content=message_content)
    del message_content
    return
# endregion
