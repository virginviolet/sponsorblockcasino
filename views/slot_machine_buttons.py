# region Imports
# Standard Library
import asyncio
from typing import Dict, List, LiteralString, cast, Literal

# Third party
from discord import Interaction, Member, User, PartialEmoji
from discord.ui import View, Button

# Local
from sponsorblockcasino_types import ReelSymbol, ReelResult, ReelResults, SpinEmojis
from models.slot_machine import SlotMachine
# endregion

# region Slots buttons


class SlotMachineView(View):
    def __init__(self,
                 invoker: User | Member,
                 slot_machine: SlotMachine,
                 text_row_1: str,
                 text_row_2: str,
                 interaction: Interaction) -> None:
        """
        Initialize the SlotMachineView instance.

        Args:
            invoker: The user or member who invoked the slot machine command.
            slot_machine: The slot machine instance.
            wager: The amount of coins wagered.
            fees: The total fees paid this time.
            interaction: The interaction instance.

        Attributes:
            current_reel_number: The current reel number being processed.
            reels_stopped: The number of reels that have stopped.
            invoker: The user or member who invoked the  slot machine command.
            invoker_id: The ID of the invoker.
            slot_machine: The slot machine instance.
            wager: The amount of coins wagered.
            fees: The total fees paid this time.
            empty_space: A string of empty spaces for formatting.
            message_header: The first row of the message.
            message_collect_screen: The message displayed on the collect screen.
            message_results_row: The message displaying the results row.
            message: The complete message to be displayed.
            combo_events: The combination events configuration.
            interaction: The interaction instance.
            reels_results: The results of the reels.
            button_clicked: Indicates if a button has been clicked.
            stop_reel_buttons: A list containing the stop reel buttons.
            TODO Update docstrings
        """
        super().__init__(timeout=20)
        self.current_reel_number: int = 1
        self.reels_stopped: int = 0
        self.invoker: User | Member = invoker
        self.invoker_id: int = invoker.id
        self.slot_machine: SlotMachine = slot_machine
        # TODO Move message variables to global scope
        self.empty_space: LiteralString = "\N{HANGUL FILLER}" * 11
        self.message_header_row: str = slot_machine.header
        self.message_text_row_1: str = text_row_1
        self.message_text_row_2: str = text_row_2
        self.spin_emojis: SpinEmojis = (
            self.slot_machine.configuration["reel_spin_emojis"])
        self.spin_emoji_1_name: str = self.spin_emojis["spin1"]["emoji_name"]
        self.spin_emoji_1_id: int = self.spin_emojis["spin1"]["emoji_id"]
        self.spin_emoji_1 = PartialEmoji(name=self.spin_emoji_1_name,
                                         id=self.spin_emoji_1_id,
                                         animated=True)
        self.message_reels_row: str = (f"{self.spin_emoji_1}\t\t"
                                       f"{self.spin_emoji_1}\t\t"
                                       f"{self.spin_emoji_1}\n")
        self.message_content: str = (
            slot_machine.make_message(text_row_1=self.message_text_row_1,
                                      text_row_2=self.message_text_row_2,
                                      reels_row=self.message_reels_row))
        self.combo_events: Dict[str, ReelSymbol] = (
            self.slot_machine.configuration["combo_events"])
        self.interaction: Interaction = interaction
        self.reels_results: ReelResults
        self.reels_results = {
            "reel1": {
                "associated_combo_event": {
                    "": {
                        "emoji_name": "",
                        "emoji_id": 0,
                        "wager_multiplier": 1.0,
                        "fixed_amount": 0
                    }
                },
                "emoji": self.spin_emoji_1
            },
            "reel2": {
                "associated_combo_event": {
                    "": {
                        "emoji_name": "",
                        "emoji_id": 0,
                        "wager_multiplier": 1.0,
                        "fixed_amount": 0
                    }
                },
                "emoji": self.spin_emoji_1
            },
            "reel3": {
                "associated_combo_event": {
                    "": {
                        "emoji_name": "",
                        "emoji_id": 0,
                        "wager_multiplier": 1.0,
                        "fixed_amount": 0
                    }
                },
                "emoji": self.spin_emoji_1
            }
        }
        self.button_clicked: bool = False
        self.stop_reel_buttons: List[Button[View]] = []
        # Create stop reel buttons
        for i in range(1, 4):
            button: Button[View] = Button(
                disabled=False,
                label="STOP",
                custom_id=f"stop_reel_{i}"
            )
            button.callback = lambda interaction, button_id=f"stop_reel_{i}": (
                self.on_button_click(interaction, button_id)
            )
            self.stop_reel_buttons.append(button)
            self.add_item(button)

    async def invoke_reel_stop(self, button_id: str) -> None:
        """
        Stops a reel and edits the message with the result.

        Args:
            button_id: The ID of the button that was clicked.
        """
        # Map button IDs to reel key names
        reel_stop_button_map: Dict[str, Literal["reel1", "reel2", "reel3"]] = {
            "stop_reel_1": "reel1",
            "stop_reel_2": "reel2",
            "stop_reel_3": "reel3"
        }
        # Pick reel based on button ID
        reel_name: Literal["reel1", "reel2", "reel3"] = (
            reel_stop_button_map[button_id])
        # Stop the reel and get the symbol
        symbol_name: str = self.slot_machine.stop_reel(reel=reel_name)
        # Get the emoji for the symbol (using the combo_events dictionary)
        symbol_emoji_name: str = self.combo_events[symbol_name]["emoji_name"]
        symbol_emoji_id: int = self.combo_events[symbol_name]["emoji_id"]
        # Create a PartialEmoji object (for the message)
        symbol_emoji: PartialEmoji = PartialEmoji(name=symbol_emoji_name,
                                                  id=symbol_emoji_id)
        # Copy keys and values from the appropriate sub-dictionary
        # in combo_events
        combo_event_properties: ReelSymbol = {**self.combo_events[symbol_name]}
        symbol_name: str = symbol_name
        reel_result: ReelResult = {
            "associated_combo_event": {symbol_name: combo_event_properties},
            "emoji": symbol_emoji
        }
        # Add the emoji to the result
        self.reels_results[reel_name] = reel_result
        self.reels_stopped += 1
        self.message_reels_row: str = (
            f"{self.reels_results['reel1']['emoji']}\t\t"
            f"{self.reels_results['reel2']['emoji']}\t\t"
            f"{self.reels_results['reel3']['emoji']}")
        self.message_content = self.slot_machine.make_message(
            text_row_1=self.message_text_row_1,
            text_row_2=self.message_text_row_2,
            reels_row=self.message_reels_row)

    # stop_button_callback
    async def on_button_click(self,
                              interaction: Interaction,
                              button_id: str) -> None:
        """
        Events to occur when a stop reel button is clicked.

        Args:
            interaction: The interaction object.
            button_id: The ID of the button that was clicked.
        """
        clicker_id: int = interaction.user.id
        if clicker_id != self.invoker_id:
            await interaction.response.send_message(
                "Someone else is playing this slot machine. Please take "
                "another one.", ephemeral=True)
        else:
            self.button_clicked = True
            if self.timeout is not None and self.reels_stopped != 3:
                # Increase the timeout
                self.timeout += 1
            # Turn the clickable button into a disabled button,
            # stop the corresponding reel and edit the message with the result
            self.stop_reel_buttons[int(button_id[-1]) - 1].disabled = True
            # print(f"Button clicked: {button_id}")
            # The self.halt_reel() method updates self.message_content
            await self.invoke_reel_stop(button_id=button_id)
            await interaction.response.edit_message(
                content=self.message_content, view=self)
            if self.reels_stopped == 3:
                self.stop()

    async def start_auto_stop(self) -> None:
        """
        Auto-stop the next reel.
        """
        if self.reels_stopped == 3:
            self.stop()
            return

        # Disable all buttons
        unclicked_buttons: List[str] = []
        for button in self.stop_reel_buttons:
            if not button.disabled:
                button_id: str = cast(str, button.custom_id)
                unclicked_buttons.append(button_id)
                button.disabled = True

        # Stop the remaining reels
        for button_id in unclicked_buttons:
            await self.invoke_reel_stop(button_id=button_id)
            await self.interaction.edit_original_response(
                content=self.message_content,
                view=self)
            if self.reels_stopped < 3:
                await asyncio.sleep(1)
        # The self.halt_reel() method stops the view if
        # all reels are stopped
# endregion