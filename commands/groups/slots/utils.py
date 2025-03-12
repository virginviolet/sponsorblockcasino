# region Imports
# Standard library

# Third party
from discord import Interaction, Role
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
from utils.roles import get_cybersecurity_officer_role
# endregion

# region Remove player


async def remove_from_active_players(interaction: Interaction,
                                     user_id: int) -> None:
    print(f"Removing user {user_id} from active players...")
    try:
        g.active_slot_machine_players.pop(user_id)
    except Exception as e:
        # Users who tries to cheat might trip this exception
        # and get reported to the IT Security Officer
        it_security_officer_role: Role | None = (
            get_cybersecurity_officer_role(interaction))
        message_content: str
        if it_security_officer_role is None:
            console_role_is_none_message: str = (
                f"ERROR: Could not get the {g.Coin} Security Officer role.")
            print(console_role_is_none_message)
            message_content = "Suspicious activity detected."
        else:
            it_security_officer_mention: str = (
                it_security_officer_role.mention)
            message_content = (f"{it_security_officer_mention} "
                               "Suspicious activity detected.")
        await interaction.followup.send(message_content)
        custom_exception_text: str = (
            f"ERROR: Could not remove user {user_id} from "
            f"g.active_slot_machine_players: {e}")
        raise type(e)(custom_exception_text)
# endregion
