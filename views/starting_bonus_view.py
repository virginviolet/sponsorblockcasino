# region Imports
# Standard Library
import random
from typing import Dict

# Third party
from discord import Interaction, Member, User
from discord.ui import Item, View, Button
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
from core.terminate_bot import terminate_bot
from models.log import Log
from models.user_save_data import UserSaveData
from utils.blockchain_utils import (add_block_transaction,
                                    get_last_block_timestamp)
from sponsorblockchain.models.blockchain import Blockchain
# endregion

# region Bonus die button


class StartingBonusView(View):
    """
    A view for handling the starting bonus die roll interaction for the Casino.
    This view presents a button to the user, allowing them to roll a die to
    receive a starting bonus.
    The view ensures that only the user who invoked the interaction can roll
    the die.

    Methods:
        on_button_click(interaction):
            Handles the event when a button is clicked.
        on_timeout:
            Handles the timeout event for the view. Disables the die button and
            sends a message to the user indicating that they took too long and
            can run the command again when ready.
        """

    def __init__(self,
                 invoker: User | Member,
                 starting_bonus_awards: Dict[int, int],
                 save_data: UserSaveData,
                 interaction: Interaction) -> None:
        """
        Initializes the StartingBonusView instance, used for the starting bonus
        die button.

        Args:
            invoker: The user or member who invoked the bot.
            starting_bonus_awards: A dictionary containing
                        the starting bonus awards.
            save_data: The save data for the user.
            log: The log object for logging information.
            interaction: The interaction object.

        Attributes:
            invoker: The user or member who invoked the bot.
            invoker_id: The ID of the invoker.
            starting_bonus_awards: A dictionary containing
                the starting bonus awards.
            save_data: The save data for the user.
            log: The log object for logging information.
            interaction: The interaction object.
            button_clicked: A flag indicating whether the button has
                been clicked.
            die_button: The button for starting the bonus die.
        """
        super().__init__(timeout=g.starting_bonus_timeout)
        self.invoker: User | Member = invoker
        self.invoker_id: int = invoker.id
        self.starting_bonus_awards: Dict[int, int] = starting_bonus_awards
        self.save_data: UserSaveData = save_data
        self.interaction: Interaction = interaction
        self.button_clicked: bool = False
        self.die_button: Button[View] = Button(
            disabled=False,
            emoji="🎲",
            custom_id="starting_bonus_die")
        self.die_button.callback = self.on_button_click
        self.add_item(self.die_button)

    async def on_button_click(self, interaction: Interaction) -> None:
        """
        Handles the event when a button is clicked.
        This method checks if the user who clicked the button is the same user
        who invoked the interaction.
        If not, it sends an ephemeral message indicating that the user cannot
        roll the die for someone else.
        If the user is the invoker, it disables the button, rolls a die, awards
        a starting bonus based on the die roll, and sends a follow-up message
        with the result. It then adds a block transaction to the blockchain,
        logs the event, and stops the interaction.
        Args:
            interaction (Interaction): The interaction object.
        """
        assert isinstance(g.blockchain, Blockchain), (
            "g.blockchain is not initialized")
        assert isinstance(g.log, Log), "g.log is not initialized"
        clicker: User | Member = interaction.user  # The one who clicked
        clicker_id: int = clicker.id
        if clicker_id != self.invoker_id:
            await interaction.response.send_message(
                "You cannot roll the die for someone else!", ephemeral=True)
        else:
            self.button_clicked = True
            self.die_button.disabled = True
            await interaction.response.edit_message(view=self)
            die_roll: int = random.randint(1, 6)
            starting_bonus: int = self.starting_bonus_awards[die_roll]
            message_content: str = (
                f"You rolled a {die_roll} and won {starting_bonus} {g.coins}!\n"
                "You may now play on the slot machines. Good luck!")
            await interaction.followup.send(message_content)
            del message_content
            await add_block_transaction(
                blockchain=g.blockchain,
                sender=g.casino_house_id,
                receiver=self.invoker,
                amount=starting_bonus,
                method="starting_bonus"
            )
            self.save_data.starting_bonus_available = False
            last_block_timestamp: float | None = get_last_block_timestamp()
            if last_block_timestamp is None:
                print("ERROR: Could not get last block timestamp.")
                await terminate_bot()
            g.log.log(
                line=(f"{self.invoker} ({self.invoker_id}) won "
                      f"{starting_bonus} {g.coins} from the starting bonus."),
                timestamp=last_block_timestamp)
            del last_block_timestamp
            self.stop()

    async def on_timeout(self) -> None:
        """
        Handles the timeout event for the view.

        This method is called when the user takes too long to roll the die.
        It disables the die button and sends a message to the user indicating
        that they took too long and can run the command again when ready.
        """
        self.die_button.disabled = True
        message_content = ("You took too long to roll the die. When you're "
                           "ready, you may run the command again.")
        await self.interaction.edit_original_response(
            content=message_content, view=self)
        del message_content

    async def _scheduled_task(self,
                              item: Item[View],
                              interaction: Interaction) -> None:
        try:
            if interaction.data is not None:
                item._refresh_state(  # type: ignore
                    interaction, interaction.data)  # type: ignore

            allow: bool = (await item.interaction_check(interaction) and
                           await self.interaction_check(interaction))
            if not allow:
                return

            # Commented out code that restarts the timeout on click
            # if self.timeout:
            #     self.__timeout_expiry = time.monotonic() + self.timeout

            await item.callback(interaction)
        except Exception as e:
            return await self.on_error(interaction, e, item)
# endregion
