# region Imports
# Standard library
from typing import Dict

# Standard library
from typing import Dict

# Third party
from discord import Interaction, PartialEmoji, app_commands
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
from type_aliases import ReelSymbol
from models.slot_machine import SlotMachine
from .slots_main import slots_group
# endregion

# region show_help


@slots_group.command(name="show_help",
                     description="Show information about the slot machine")
@app_commands.describe(private_room=(
    "Whether you want to book a private room or not"))
async def show_help(interaction: Interaction,
                    private_room: bool = True) -> None:
    assert isinstance(g.bot, Bot), (
        "g.bot has not been initialized.")
    assert isinstance(g.slot_machine, SlotMachine), (
        "g.slot_machine has not been initialized.")
    pay_table: str = ""
    combo_events: Dict[str, ReelSymbol] = (
        g.slot_machine.configuration["combo_events"])
    combo_event_count: int = len(combo_events)
    for event in combo_events:
        event_name: str = event
        event_name_friendly: str = (
            g.slot_machine.make_friendly_event_name(event_name))
        emoji_name: str = combo_events[event]['emoji_name']
        emoji_id: int = combo_events[event]['emoji_id']
        emoji: PartialEmoji = PartialEmoji(name=emoji_name, id=emoji_id)
        row: str = (
            f"> {emoji} {emoji} {emoji}    {event_name_friendly}\n> \n")
        pay_table += row
    # strip the last ">"
    pay_table = pay_table[:pay_table.rfind("\n> ")]
    jackpot_seed: int = (
        g.slot_machine.configuration["combo_events"]
        ["jackpot"]["fixed_amount"])
    administrator: str = (await g.bot.fetch_user(g.administrator_id)).name
    # TODO Import fees from configuration instead of hardcoding them
    help_message_1: str = (
        f"## {g.Coin} Slot Machine Help\n"
        f"Win big by playing the {g.Coin} Slot Machine!*\n\n"
        "### Pay table\n"
        f"{pay_table}\n"
        "\n"
        "### Fees\n"
        "> Coins inserted: Fee\n"
        f"> 1:             1 {g.Coin}\n"
        f"> <10:        1 {g.coin} + 29%\n"
        "> <100:     25%\n"
        "> ≥100:     19%\n"
        "\n"
        "Fees are calculated from your total stake (the amount of coins "
        "you insert), and are deducted from your total return (your "
        "gross return.). For example, if you insert 100 coins, and win "
        "a 2X award, you get 200 coins, and then 2 coins are deducted, "
        "leaving you with 198 coins.\n"
        "\n"
        "### Rules\n"
        "You must be 18 years or older to play.\n\n"
        "### How to play\n"
        "To play, run the `/slots insert_coins` command, and optionally "
        "specify the amount of coins with the `amount` parameter. "
        "Then wait for the reels to stop, or stop them "
        "yourself by hitting the stop buttons. Your goal is to get a "
        "winning combination of three symbols illustrated on the "
        "pay table.\n"
        "\n"
        "### Overview\n"
        f"The {g.Coin} Slot Machine has 3 reels.\n"
        f"Each reel has {combo_event_count} unique symbols.\n"
        "If three symbols match, you get an award based on the symbol, "
        "or, if you're unlucky, you lose your entire stake (see the pay "
        "table).\n"
        "\n")
    help_message_2: str = (
        "### Stake\n"
        "The amount of coins you insert is your stake. This includes the "
        "fees. The stake is the amount of coins you are willing to risk. "
        "It will determine the amount you can win, and how high the fees "
        "will be.\n"
        "\n"
        "Multiplier awards multiply your total stake before fees are "
        "deducted.\n"
        "\n"
        "If you do not specify a stake, it means you insert 1 coin and "
        "that will be your stake.\n"
        "\n"
        f"A perhaps counter-intuitive feature of the {g.Coin} Slot Machine "
        "is that if you do not strike a combination, you do not lose "
        "your entire stake, but only the fees. But if you get \"Lose stake\" "
        "combination, you do lose your entire stake.\n"
        "\n"
        "Any net positive outcome will be immediately added to your "
        "balance. Similarly, if you get a net negative outcome, the "
        f"loss amount will be transferred to the {g.Coin} Casino's "
        "account.\n"
        "\n"
        "### Jackpot\n"
        "The jackpot is a pool of coins that grows as people play the "
        "slot machine.\n"
        "If you get a jackpot-winning combination, you win the "
        "entire jackpot pool.\n"
        "\n"
        "To check the current jackpot amount, "
        "use the `jackpot` parameter.\n"
        "\n"
        f"To be eligible for the jackpot, you must insert "
        f"at least 2 {g.coins}. Then, a small portion of your stake will "
        "be added to the jackpot pool as a jackpot fee. For stakes "
        "between 2 and 10 coins, the jackpot fee is 1 coin. Above that, it "
        "is 1%. The jackpot fees are included in in the fees you see on "
        "the fees table.\n\n"
        f"When someone wins the jackpot, the pool is reset "
        f"to {jackpot_seed} {g.coins}.\n"
        "\n")
    help_message_3: str = (
        "### Fairness\n"
        "The outcome of a play is never predetermined. The slot machine "
        "uses a random number generator to determine the outcome of each "
        "reel each time you play. Some symbols are however more likely "
        "to appear than others, because each reel has a set amount of "
        "each symbol.\n"
        "\n"
        "To check the RTP (return to player) for a given stake, use "
        "the `rtp` parameter.\n"
        "\n"
        "### Contact\n"
        "If you are having issues, you can reboot the slot machine by "
        "using the reboot parameter. If you have any other issues, "
        f"please contact the {g.Coin} Casino staff or a Slot Machine "
        "Technician (ping Slot Machine Technician). If you need to "
        f"contact the {g.Coin} Casino CEO, ping {administrator}.\n"
        "\n"
        "-# *Not guaranteed. Actually, for legal reasons, nothing about "
        "this game is guaranteed.\n")
    await interaction.response.send_message(help_message_1,
                                            ephemeral=private_room)
    await interaction.followup.send(help_message_2,
                                    ephemeral=private_room)
    await interaction.followup.send(help_message_3,
                                    ephemeral=private_room)
    return
# endregion
