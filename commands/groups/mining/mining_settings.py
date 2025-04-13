# region Imports
# Standard library

# Third party
from discord import (Interaction, Member, User, app_commands)

# Local
import core.global_state as g
from models.user_save_data import UserSaveData
from .mining_main import mining_group
# endregion
 
# region settings


@mining_group.command(name="settings",
                      description="Configure mining settings")
@app_commands.describe(disable_reaction_messages="Stop the bot from messaging "
                       "new players when you mine their messages")
async def settings(interaction: Interaction,
                   disable_reaction_messages: bool) -> None:
    """
    Mining commands

    Args:
    interaction              -- The interaction object representing the
                                command invocation.
    disable_reaction_messages -- Disable reaction messages
    """
    invoker: User | Member = interaction.user
    invoker_id: int = invoker.id
    invoker_name: str = invoker.name
    save_data: UserSaveData = UserSaveData(user_id=invoker_id,
                                           user_name=invoker_name)
    save_data.mining_messages_enabled = not disable_reaction_messages
    del save_data
    message_content: str
    if disable_reaction_messages is True:
        message_content = ("I will no longer message new players "
                           "when you mine their messages.")
    else:
        message_content: str = ("I will message new players when you mine "
                                "their messages. Thank you for "
                                f"helping the {g.Coin} network grow!")
    await interaction.response.send_message(
        message_content, ephemeral=True)
    del message_content
    return

# endregion
