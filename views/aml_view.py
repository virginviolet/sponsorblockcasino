# region Imports
from discord import Interaction, Member, User, Message, AllowedMentions
from discord.ui import View, Button
from core.global_state import Coin
# endregion

# region AML view


class AmlView(View):
    def __init__(self,
                 interaction: Interaction,
                 initial_message: str) -> None:
        """
        Initialize the AmlView instance.

        Args:
            interaction: The interaction instance.

        Attributes:
            interaction: The interaction instance.
        """
        super().__init__(timeout=60)
        invoker: User | Member = interaction.user
        self.invoker_id: int = invoker.id
        self.invoker_id: int = interaction.user.id
        self.interaction: Interaction = interaction
        self.initial_message: str = initial_message
        self.followup_message: Message | None = None
        self.approve_button: Button[View] = Button(
            disabled=False,
            label="Approve",
            custom_id="aml_approve"
        )
        self.approve_button.callback = lambda interaction: (
            self.on_button_click(
                interaction=interaction, button=self.approve_button))
        self.decline_button: Button[View] = Button(
            disabled=False,
            label="Decline",
            custom_id="aml_decline"
        )
        self.decline_button.callback = lambda interaction: (
            self.on_button_click(
                interaction=interaction, button=self.decline_button))
        self.add_item(self.approve_button)
        self.add_item(self.decline_button)
        self.approved: bool = False

    async def on_button_click(self,
                              interaction: Interaction,
                              button: Button[View]) -> None:
        """
        Handles the event when a button is clicked.

        Args:
            interaction: The interaction object.
        """
        clicker: User | Member = interaction.user
        clicker_id: int = clicker.id
        if clicker_id != self.invoker_id:
            await interaction.response.send_message(
                "This is not your AML terminal.",
                ephemeral=True)
        else:
            self.approve_button.disabled = True
            self.decline_button.disabled = True
            await interaction.response.edit_message(view=self)
            message_content: str = f"{self.initial_message}\n"
            if button == self.approve_button:
                message_content += (f"-# The {Coin} Bank has approved "
                                    "the transaction.")
                self.approved = True
            else:
                message_content += (f"-# The {Coin} Bank has declined "
                                    "the transaction.")
            if self.followup_message is None:
                await self.interaction.edit_original_response(
                    content=message_content, view=self,
                    allowed_mentions=AllowedMentions.none())
            else:
                message_id: int = self.followup_message.id
                await self.interaction.followup.edit_message(
                    message_id=message_id,
                    content=message_content, view=self,
                    allowed_mentions=AllowedMentions.none())
            self.stop()

    async def on_timeout(self) -> None:
        """
        Handles the timeout event for the view.

        This method is called when the user takes too long to respond.
        It disables the buttons and sends a message to the user indicating
        that they took too long and can run the command again when ready.
        """
        self.approve_button.disabled = True
        self.decline_button.disabled = True
        message_content: str = ("The AML officer has left the terminal.")
        if self.followup_message is None:
            await self.interaction.edit_original_response(
                content=message_content, view=self)
        else:
            message_id: int = self.followup_message.id
            await self.interaction.followup.edit_message(
                message_id=message_id,
                content=message_content, view=self)
        del message_content
# endregion
