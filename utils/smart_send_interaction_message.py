# region Imports
# Third party
from discord import Interaction
# endregion

# region Function


async def smart_send_interaction_message(interaction: Interaction,
                                         content: str,
                                         has_sent_message: bool,
                                         ephemeral: bool = False) -> None:
    if not has_sent_message:
        await interaction.response.send_message(content, ephemeral=ephemeral)
    else:
        await interaction.followup.send(content, ephemeral=ephemeral)
    del content
# endregion
