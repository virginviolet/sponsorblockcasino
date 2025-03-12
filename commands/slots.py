# region Imports
# Standard library
import asyncio
import math
from time import time
from hashlib import sha256

# Standard library
from sympy import Float, Integer, simplify
from typing import (Dict, List, cast)

# Third party
from humanfriendly import format_timespan
from discord import Interaction, Member, PartialEmoji, User, app_commands, Role
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
from bot_configuration import invoke_bot_configuration
from type_aliases import ReelSymbol,  ReelResults, SpinEmojis
from core.terminate_bot import terminate_bot
from models.slot_machine import SlotMachine
from models.grifter_suppliers import GrifterSuppliers
from models.log import Log
from models.transfers_waiting_approval import TransfersWaitingApproval
from models.user_save_data import UserSaveData
from utils.blockchain_utils import (add_block_transaction,
                                    get_last_block_timestamp)
from utils.formatting import format_coin_label
from utils.roles import get_cybersecurity_officer_role
from views.starting_bonus_view import StartingBonusView
from views.slot_machine_buttons import SlotMachineView
from blockchain.models.blockchain import Blockchain
# endregion

# region /slots
# assert g.bot is not None, "bot has not been initialized."
assert isinstance(g.bot, Bot), "bot has not been initialized."


@g.bot.tree.command(name="slots",
                    description="Play on a slot machine")
@app_commands.describe(insert_coins="Insert coins into the slot machine")
@app_commands.describe(private_room="Play in a private room")
@app_commands.describe(jackpot="Check the current jackpot amount")
@app_commands.describe(reboot="Reboot the slot machine")
@app_commands.describe(show_help="Show help")
@app_commands.describe(rtp="Show the return to player percentage for "
                       "a given wager")
async def slots(interaction: Interaction,
                insert_coins: int | None = None,
                private_room: bool | None = None,
                jackpot: bool = False,
                reboot: bool = False,
                show_help: bool = False,
                rtp: int | None = False) -> None:
    """
    Command to play a slot machine.

    If it's the first time the user plays, they will be offered a
    starting bonus of an amount that is decided by a die.

    Three blank emojis are displayed and then the reels will stop in a few
    seconds, or the user can stop them manually by hitting the stop buttons that
    appear. The message containing the blank emojis are updated each time a reel
    is stopped.
    If they get a net positive outcome, the amount will be added to their
    balance. If they get a net negative outcome, the loss amount will be
    transferred to the casino's account.
    See the "show_help" parameter for more information about the game.

    See the UserSaveData documentation for more information
    about 'starting_bonus_available' and 'when_last_bonus_received'. 

    Args:
    interaction  -- The interaction object representing the
                    command invocation.
    insert_coins -- Sets the stake/wager (default 1)
    private_room -- Makes the bot's messages ephemeral
                    (only visible to the invoker) (default False)
    jackpot      -- Reports the current jackpot pool (default False)
    reboot       -- Removes the invoker from g.active_slot_machine_players
                    (default False)
    show_help   -- Sends information about the command/game (default False)
    """

    # TODO Add TOS parameter
    # TODO Add service parameter
    # IMPROVE Make incompatible parameters not selectable together
    assert isinstance(g.bot, Bot), (
        "bot has not been initialized.")
    assert isinstance(g.slot_machine, SlotMachine), (
        "g.slot_machine has not been initialized.")
    assert isinstance(g.blockchain, Blockchain), (
        "g.blockchain has not been initialized.")
    assert isinstance(g.grifter_suppliers, GrifterSuppliers), (
        "g.grifter_suppliers has not been initialized.")
    assert isinstance(g.log, Log), "g.log has not been initialized."

    async def remove_from_active_players(user_id: int) -> None:
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

    def grifter_supplier_check() -> bool:
        """
        Checks if the invoker is a Grifter Supplier and sends a message if they
        are.
        """
        # Check if the user has coins in GrifterSwap
        assert isinstance(g.grifter_suppliers, GrifterSuppliers), (
            "grifter_suppliers has not been initialized.")
        all_grifter_suppliers: List[int] = g.grifter_suppliers.suppliers
        is_grifter_supplier: bool = user_id in all_grifter_suppliers
        if is_grifter_supplier:
            return True
        else:
            return False

    if private_room:
        should_use_ephemeral = True
    else:
        should_use_ephemeral = False
    wager_int: int | None = insert_coins
    if wager_int is None:
        wager_int = 1
    if wager_int < 0:
        message_content = "Thief!"
        await interaction.response.send_message(
            message_content, ephemeral=False)
        return
    elif wager_int == 0:
        message_content = "Insert coins to play!"
        await interaction.response.send_message(
            message_content, ephemeral=should_use_ephemeral)
        return
    # TODO Log/stat outcomes (esp. wager amounts)
    user: User | Member = interaction.user
    user_id: int = user.id

    if show_help:
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
        help_message_1: str = (
            f"## {g.Coin} Slot Machine Help\n"
            f"Win big by playing the {g.Coin} Slot Machine!*\n\n"
            "### Pay table\n"
            f"{pay_table}\n"
            "\n"
            "### Fees\n"
            "> Coins inserted: Fee\n"
            f"> 1:             1 {g.Coin}\n"
            f"> <10:        2 {g.coins}\n"
            "> <100:     20%\n"
            "> ≥100:     7%\n"
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
            "To play, insert coins with the `insert_coin` parameter of the \n"
            "`/slots` command. Then wait for the reels to stop, or stop them "
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
            "your entire stake, but only the fees. But if you get Lose wager "
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
        # Use ephemeral messages unless explicitly set to False
        if private_room is False:
            should_use_ephemeral = False
        else:
            should_use_ephemeral = True
        await interaction.response.send_message(help_message_1,
                                                ephemeral=should_use_ephemeral)
        await interaction.followup.send(help_message_2,
                                        ephemeral=should_use_ephemeral)
        await interaction.followup.send(help_message_3,
                                        ephemeral=should_use_ephemeral)
        return
    elif rtp:
        wager_int = rtp
        wager = Integer(rtp)
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
        coin_label = format_coin_label(wager_int)
        message_content = g.slot_machine.make_message(
            f"-# RTP (stake={wager_int} {coin_label}): {rtp_display}")
        if private_room is False:
            should_use_ephemeral = False
        else:
            should_use_ephemeral = True
        await interaction.response.send_message(message_content,
                                                ephemeral=should_use_ephemeral)
        return
    elif reboot:
        message_content = g.slot_machine.make_message(
            f"-# The {g.Coin} Slot Machine is restarting...")
        await interaction.response.send_message(message_content,
                                                ephemeral=should_use_ephemeral)
        del message_content
        await asyncio.sleep(4)
        # Refresh configuration and reinitialize classes
        invoke_bot_configuration()
        g.slot_machine = SlotMachine()
        g.grifter_suppliers = GrifterSuppliers()
        g.transfers_waiting_approval = TransfersWaitingApproval()

        # Remove invoker from active players in case they are stuck in it
        # Multiple checks are put in place to prevent cheating
        bootup_message: str = f"-# Welcome to the {g.Coin} Casino!"
        current_time: float = time()
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
                    await remove_from_active_players(user_id)
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
    elif jackpot:
        # Check the jackpot amount
        jackpot_pool: int = g.slot_machine.jackpot
        coin_label: str = format_coin_label(jackpot_pool)
        message_header: str = g.slot_machine.header
        message_content = (f"{message_header}\n"
                           f"-# JACKPOT: {jackpot_pool} {coin_label}.")
        del coin_label
        await interaction.response.send_message(message_content,
                                                ephemeral=should_use_ephemeral)
        return

    # Check if user is already playing on a slot machine
    wait_seconds_left: int = 2
    while user_id in g.active_slot_machine_players and wait_seconds_left > 0:
        await asyncio.sleep(1)
        wait_seconds_left -= 1
    # If the user is still in the active players list, send a message and return
    if user_id in g.active_slot_machine_players:
        await interaction.response.send_message(
            "You are only allowed to play "
            "on one slot machine at a time.\n"
            "-# If you're having issues, please try rebooting the slot machine "
            f"before contacting the {g.Coin} Casino staff.",
            ephemeral=True)
        return
    else:
        start_play_timestamp: float = time()
        g.active_slot_machine_players[user_id] = start_play_timestamp
        del start_play_timestamp

    user_name: str = user.name
    save_data: UserSaveData = (
        UserSaveData(user_id=user_id, user_name=user_name))
    starting_bonus_available: bool | float = save_data.starting_bonus_available

    # Check balance
    user_id_hash: str = sha256(str(user_id).encode()).hexdigest()
    user_balance: int | None = g.blockchain.get_balance(user=user_id_hash)
    if user_balance is None:
        user_balance = 0

    has_played_before: bool = save_data.has_visited_casino
    new_bonus_wait_complete: bool = (
        (isinstance(starting_bonus_available, float)) and
        (time() >= starting_bonus_available))
    is_grifter_supplier = False
    if not has_played_before:
        starting_bonus_available = True
    elif (user_balance <= 0):
        is_grifter_supplier = grifter_supplier_check()
        if is_grifter_supplier:
            message_content: str = (
                f"Welcome back! We give free coins to customers who do not "
                "have any. However, we request that you first delete "
                "your GrifterSwap account.\n"
                "Here's how you can do it:\n"
                "See your GrifterSwap balance with `!balance`, withdraw all "
                "your coins with \n"
                "`!withdraw <currency> <amount>`, and then use `!suppliers` to "
                "prove you're no longer a supplier.")
            await interaction.response.send_message(
                message_content, ephemeral=should_use_ephemeral)
            del message_content
            await remove_from_active_players(user_id)
            return

    if ((user_balance <= 0) and
        (isinstance(starting_bonus_available, bool)) and
            (starting_bonus_available is False)):
        # The `isinstance()` check is technically unnecessary,
        # but is included for clarity

        # See the UserSaveData documentation for information
        # about `starting_bonus_available` and `when_last_bonus_received`.
        when_last_bonus_received: float | None = (
            save_data.when_last_bonus_received)
        if when_last_bonus_received is None:
            starting_bonus_available = True
        else:
            min_seconds_between_bonuses: int = (
                g.slot_machine.next_bonus_wait_seconds)
            when_eligible_for_bonus: float = (
                when_last_bonus_received + min_seconds_between_bonuses)
            is_eligible_for_bonus: bool = time() >= when_eligible_for_bonus
            if is_eligible_for_bonus:
                starting_bonus_available = True
            else:
                starting_bonus_available = when_eligible_for_bonus
                save_data.starting_bonus_available = when_eligible_for_bonus
                min_time_between_bonuses: str = format_timespan(
                    min_seconds_between_bonuses)
                message_content = (
                    f"Come back in {min_time_between_bonuses} and "
                    "we will give you some coins to play with.")
                await interaction.response.send_message(
                    message_content, ephemeral=should_use_ephemeral)
                del message_content
                await remove_from_active_players(user_id)
                return
    elif ((user_balance <= 0) and
          (isinstance(starting_bonus_available, float)) and
          (time() < starting_bonus_available)):
        seconds_left = int(starting_bonus_available - time())
        time_left: str = format_timespan(seconds_left)
        message_content: str = (f"You are out of {g.coins}. Come back "
                                f"in {time_left} to get some coins.")
        # Use ephemeral unless explicitly set to False
        if private_room is False:
            should_use_ephemeral = False
        else:
            should_use_ephemeral = True
        await interaction.response.send_message(
            message_content, ephemeral=should_use_ephemeral)
        del message_content
        await remove_from_active_players(user_id)
        return

    main_bonus_requirements_passed: bool = (
        new_bonus_wait_complete or
        starting_bonus_available == True)
    if main_bonus_requirements_passed:
        is_grifter_supplier = grifter_supplier_check()
    should_give_bonus: bool = (
        main_bonus_requirements_passed and not is_grifter_supplier)
    if should_give_bonus:
        # Send message to inform user of starting bonus
        starting_bonus_awards: Dict[int, int] = {
            1: 50, 2: 100, 3: 200, 4: 300, 5: 400, 6: 500}
        starting_bonus_table: str = "> **Die roll**\t**Amount**\n"
        for die_roll, amount in starting_bonus_awards.items():
            starting_bonus_table += f"> {die_roll}\t\t\t\t{amount}\n"
        message_preamble: str
        if has_played_before:
            message_preamble = (f"Welcome back! You spent all your {g.coins} "
                                "and we want to give you another chance.\n"
                                f"Roll the die and we will give you a bonus.")
        else:
            message_preamble = (f"Welcome to the {g.Coin} Casino! This seems "
                                "to be your first time here.\n"
                                "A standard 6-sided die will decide your "
                                "starting bonus.")
        # TODO Move the table to a separate message
        message_content: str = (f"{message_preamble}\n"
                                "The possible outcomes are displayed below.\n\n"
                                f"{starting_bonus_table}")

        starting_bonus_view = (
            StartingBonusView(invoker=user,
                              starting_bonus_awards=starting_bonus_awards,
                              save_data=save_data,
                              interaction=interaction))
        await interaction.response.send_message(content=message_content,
                                                view=starting_bonus_view)
        wait: bool = await starting_bonus_view.wait()
        timed_out: bool = wait is True
        if not timed_out:
            save_data.has_visited_casino = True
            current_time: float = time()
            save_data.when_last_bonus_received = current_time
        await remove_from_active_players(user_id)
        return

    del has_played_before

    if user_balance < wager_int:
        coin_label_w: str = format_coin_label(wager_int)
        coin_label_b: str = format_coin_label(user_balance)
        message_content = (f"You do not have enough {g.coins} "
                           f"to stake {wager_int} {coin_label_w}.\n"
                           f"Your current balance is {user_balance} {coin_label_b}.")
        await interaction.response.send_message(
            content=message_content, ephemeral=True)
        del coin_label_w
        del coin_label_b
        del message_content
        if user_id in g.active_slot_machine_players:
            await remove_from_active_players(user_id)
        return

    fees_dict: Dict[str, int | float] = g.slot_machine.configuration["fees"]
    low_wager_main_fee: int = (
        cast(int, fees_dict["low_wager_main"]))
    medium_wager_main_fee: float = (
        cast(float, fees_dict["medium_wager_main"]))
    high_wager_main_fee: float = (
        cast(float, fees_dict["high_wager_main"]))
    low_wager_jackpot_fee: int = (
        cast(int, fees_dict["low_wager_jackpot"]))
    medium_wager_jackpot_fee: float = (
        cast(float, fees_dict["medium_wager_jackpot"]))
    high_wager_jackpot_fee: float = (
        cast(float, fees_dict["high_wager_jackpot"]))

    jackpot_fee_paid: bool = (
        wager_int >= (low_wager_main_fee + low_wager_jackpot_fee))
    no_jackpot_mode: bool = False if jackpot_fee_paid else True
    jackpot_fee: int
    main_fee: int
    if no_jackpot_mode:
        # IMPROVE Make min_wager config keys
        main_fee = low_wager_main_fee
        jackpot_fee = 0
    elif wager_int < 10:
        main_fee = low_wager_main_fee
        jackpot_fee = low_wager_jackpot_fee
    elif wager_int < 100:
        main_fee_unrounded: float = wager_int * medium_wager_main_fee
        main_fee = round(main_fee_unrounded)
        jackpot_fee_unrounded: float = wager_int * medium_wager_jackpot_fee
        jackpot_fee = round(jackpot_fee_unrounded)
    else:
        main_fee_unrounded: float = wager_int * high_wager_main_fee
        main_fee = round(main_fee_unrounded)
        jackpot_fee_unrounded: float = wager_int * high_wager_jackpot_fee
        jackpot_fee = round(jackpot_fee_unrounded)
    fees: int = jackpot_fee + main_fee

    spin_emojis: SpinEmojis = g.slot_machine.configuration["reel_spin_emojis"]
    spin_emoji_1_name: str = spin_emojis["spin1"]["emoji_name"]
    spin_emoji_1_id: int = spin_emojis["spin1"]["emoji_id"]
    spin_emoji_1 = PartialEmoji(name=spin_emoji_1_name,
                                id=spin_emoji_1_id,
                                animated=True)
    reels_row: str = f"{spin_emoji_1}\t\t{spin_emoji_1}\t\t{spin_emoji_1}"
    wager_row: str = f"-# Coin: {wager_int}"
    fees_row: str = f"-# Fee: {fees}"
    slots_message: str = g.slot_machine.make_message(text_row_1=wager_row,
                                                     text_row_2=fees_row,
                                                     reels_row=reels_row)

    slot_machine_view = SlotMachineView(invoker=user,
                                        slot_machine=g.slot_machine,
                                        text_row_1=wager_row,
                                        text_row_2=fees_row,
                                        interaction=interaction)
    await interaction.response.send_message(content=slots_message,
                                            view=slot_machine_view,
                                            ephemeral=should_use_ephemeral)
    del slots_message
    # Auto-stop reel timer
    # Views have built-in timers that you can wait for with the wait() method,
    # but since we have tasks to upon the timer running out, that won't work
    # There is probably a way to do it with just the view, but I don't know how
    previous_buttons_clicked_count = 0
    let_the_user_stop = True
    user_irresonsive: bool
    user_stopped_clicking: bool
    all_buttons_clicked: bool
    while let_the_user_stop:
        buttons_clicked_count = 0
        await asyncio.sleep(3.0)
        for button in slot_machine_view.stop_reel_buttons:
            button_clicked: bool = button.disabled
            if button_clicked:
                buttons_clicked_count += 1
        user_irresonsive = buttons_clicked_count == 0
        # FIXME
        all_buttons_clicked = buttons_clicked_count == 3
        user_stopped_clicking = (
            buttons_clicked_count == previous_buttons_clicked_count)
        if (user_irresonsive or all_buttons_clicked or user_stopped_clicking):
            let_the_user_stop = False
        previous_buttons_clicked_count: int = buttons_clicked_count
    await slot_machine_view.start_auto_stop()

    # Get results
    results: ReelResults = slot_machine_view.reels_results

    # Create some variables for the outcome messages
    slot_machine_reels_row: str = slot_machine_view.message_reels_row
    del slot_machine_view

    # Calculate win amount
    event_name: str
    event_name_friendly: str
    # Win money is the amount of money that the event will award
    # (not usually the same as net profit or net return)
    win_money: int
    event_name, event_name_friendly, win_money = (
        g.slot_machine.calculate_award_money(wager=wager_int,
                                             results=results))

    # Generate outcome messages
    event_message: str | None = None
    # print(f"event_name: '{event_name}'")
    # print(f"event_name_friendly: '{event_name_friendly}'")
    # print(f"win money: '{win_money}'")
    coin_label_wm: str = format_coin_label(win_money)
    if event_name == "jackpot_fail":
        jackpot_pool: int = g.slot_machine.jackpot
        coin_label_fee: str = format_coin_label(jackpot_pool)
        coin_label_jackpot: str = format_coin_label(jackpot_pool)
        event_message = (f"{event_name_friendly}! Unfortunately, you did "
                         "not pay the jackpot fee of "
                         f"{jackpot_fee} {coin_label_fee}, meaning "
                         "that you did not win the jackpot of "
                         f"{jackpot_pool} {coin_label_jackpot}. "
                         "Better luck next time!")
        del coin_label_fee
        del coin_label_jackpot
    elif event_name == "standard_lose":
        # event_message = None
        event_message = "So close!"
    else:
        # The rest of the possible events are win events
        event_message = (f"{event_name_friendly}! "
                         f"You won {win_money} {coin_label_wm}!")

    # Calculate net return to determine who should get money (house or player)
    # and to generate collect screen message and an informative log line
    # Net return is the loss or profit of the player (wager excluded)
    net_return: int
    # Total return is the total amount of money that the player will get
    # get back (wager included)
    total_return: int
    log_line: str = ""
    if event_name == "lose_wager":
        event_message = (f"You lost your entire "
                         f"stake of {wager_int} {coin_label_wm}. "
                         "Better luck next time!")
        net_return = -wager_int
        total_return = 0
    net_return = win_money - main_fee - jackpot_fee
    total_return = wager_int + win_money - main_fee - jackpot_fee
    # print(f"wager: {wager_int}")
    # print(f"standard_fee: {main_fee}")
    # print(f"jackpot_fee: {jackpot_fee}")
    # print(f"jackpot_fee_paid: {jackpot_fee_paid}")
    # print(f"jackpot_mode: {jackpot_mode}")
    # print(f"win_money: {win_money}")
    # print(f"net_return: {net_return}")
    # print(f"total_return: {total_return}")
    coin_label_nr: str = format_coin_label(net_return)
    if net_return > 0:
        log_line = (f"{user_name} ({user_id}) won the {event_name} "
                    f"({event_name_friendly}) reward "
                    f"of {win_money} {coin_label_wm} and profited "
                    f"{net_return} {coin_label_nr} on the {g.Coin} Slot Machine.")
    elif net_return == 0:
        if event_name == "jackpot_fail":
            # This should not happen with default config
            log_line = (f"{user_name} ({user_id}) got the {event_name} "
                        f"({event_name_friendly}) event without paying the "
                        "jackpot fee, so they did not win the jackpot, "
                        "yet they neither lost any coins nor profited.")
        elif event_name == "lose_wager":
            # This should not happen with default config
            log_line = (f"{user_name} ({user_id}) got "
                        f"the {event_name} event ({event_name_friendly}) "
                        "and lost their entire wager of "
                        f"{wager_int} {coin_label_nr} on "
                        f"the {g.Coin} Slot Machine, "
                        "yet they neither lost any coins nor profited.")
        elif win_money > 0:
            # With the default config, this will happen if the fees are higher
            # than the win money
            log_line = (f"{user_name} ({user_id}) won the {event_name} "
                        f"({event_name_friendly}) reward "
                        f"of {win_money} {coin_label_wm} on the {g.Coin} "
                        "slot machine, but made no profit.")
        else:
            # This should not happen without win money with the default config
            # (because of the fees)
            log_line = (f"{user_name} ({user_id}) made no profit on the "
                        f"{g.Coin} Slot Machine.")
    else:
        # if net return is negative, the user lost money
        if event_name == "lose_wager":
            log_line = (f"{user_name} ({user_id}) got the {event_name} event "
                        f"({event_name_friendly}) and lost their entire wager "
                        f"of {wager_int} {coin_label_nr} on the "
                        f"{g.Coin} Slot Machine.")
        if event_name == "jackpot_fail":
            log_line = (f"{user_name} ({user_id}) lost {-net_return} "
                        f"{coin_label_nr} on the {g.Coin} Slot Machine by "
                        f"getting the {event_name} ({event_name_friendly}) "
                        "event without paying the jackpot fee.")
        elif win_money > 0:
            # turn -net_return into a positive number
            log_line = (f"{user_name} ({user_id}) won "
                        f"{win_money} {coin_label_wm} on "
                        f"the {event_name} ({event_name_friendly}) reward, "
                        f"but lost {-net_return} {coin_label_nr} in net return "
                        f"on the {g.Coin} Slot Machine.")
        else:
            log_line = (f"{user_name} ({user_id}) lost "
                        f"{-net_return} {coin_label_nr} on "
                        f"the {g.Coin} Slot Machine.")
    del coin_label_wm

    # Generate collect message
    coin_label_tr: str = format_coin_label(total_return)
    collect_message: str | None = None
    if (total_return > 0):
        collect_message = f"-# You collect {total_return} {coin_label_tr}."
    else:
        collect_message = None
    del coin_label_nr

    # TODO Move code to SlotMachine.make_message
    if event_message or collect_message:
        # Display outcome messages
        outcome_message_line_1: str | None = None
        outcome_message_line_2: str | None = None
        if event_message and not collect_message:
            outcome_message_line_1 = event_message
        elif collect_message and not event_message:
            outcome_message_line_1 = collect_message
        elif event_message and collect_message:
            outcome_message_line_1 = event_message
            outcome_message_line_2 = collect_message
        del event_message
        del collect_message

        # edit original message
        slots_message_outcome: str = g.slot_machine.make_message(
            text_row_1=outcome_message_line_1,
            text_row_2=outcome_message_line_2,
            reels_row=slot_machine_reels_row)
        del outcome_message_line_1
        del outcome_message_line_2
        del slot_machine_reels_row
        await interaction.edit_original_response(content=slots_message_outcome)
        del slots_message_outcome

    # Transfer and log
    last_block_error = False
    if net_return != 0:
        sender: User | Member | int
        receiver: User | Member | int
        log_timestamp: float = 0.0
        transfer_amount: int
        if net_return > 0:
            transfer_amount = net_return
            sender = g.casino_house_id
            receiver = user
        else:
            sender = user
            receiver = g.casino_house_id
            # flip to positive value (transferring a negative amount would mean
            # reducing the receiver's balance)
            transfer_amount = -net_return
        await add_block_transaction(
            blockchain=g.blockchain,
            sender=sender,
            receiver=receiver,
            amount=transfer_amount,
            method="slot_machine"
        )
        del sender
        del receiver
        del transfer_amount
        last_block_timestamp: float | None = get_last_block_timestamp()
        if last_block_timestamp is None:
            print("ERROR: Could not get last block timestamp.")
            log_timestamp = time()
            log_line += ("(COULD NOT GET LAST BLOCK TIMESTAMP; "
                         "USING CURRENT TIME; WILL NOT RESET JACKPOT)")
            last_block_error = True
        else:
            log_timestamp = last_block_timestamp
        del last_block_timestamp
    else:
        log_timestamp = time()
    g.log.log(line=log_line, timestamp=log_timestamp)
    del log_timestamp
    del log_line

    coins_left: int = user_balance + net_return
    if coins_left <= 0 and starting_bonus_available is False:
        next_bonus_time_left: str = format_timespan(
            g.slot_machine.next_bonus_wait_seconds)
        invoker: str = user.mention
        all_grifter_suppliers: List[int] = g.grifter_suppliers.suppliers
        is_grifter_supplier: bool = user_id in all_grifter_suppliers
        if is_grifter_supplier:
            message_content = (f"{invoker} You're all out of {g.coins}!\n"
                               "To customers who run out of coins, we usually give "
                               "some for free. However, we request that you please "
                               "delete your GrifterSwap account first.\n"
                               "Here's how you can do it:\n"
                               "See your GrifterSwap balance with `!balance`, "
                               "withdraw all your coins with\n"
                               "`!withdraw <currency> <amount>`, "
                               "and then use `!suppliers` to prove you're no longer "
                               "a supplier.")
            await interaction.followup.send(content=message_content,
                                            ephemeral=should_use_ephemeral)
            del message_content
        else:
            message_content: str = (f"{invoker} You're all out of {g.coins}!\n"
                                    f"Come back in {next_bonus_time_left} "
                                    "for a new starting bonus.")
            del next_bonus_time_left
            await interaction.followup.send(content=message_content,
                                            ephemeral=should_use_ephemeral)
            del message_content
            next_bonus_point_in_time: float = (
                time() + g.slot_machine.next_bonus_wait_seconds)
            save_data.starting_bonus_available = next_bonus_point_in_time
            del next_bonus_point_in_time

    if user_id in g.active_slot_machine_players:
        await remove_from_active_players(user_id)

    if last_block_error:
        # send message to admin
        administrator: str = (await g.bot.fetch_user(g.administrator_id)).name
        await interaction.response.send_message("An error occurred. "
                                                f"{administrator} pls fix.")
        await terminate_bot()
    del last_block_error

    if event_name == "jackpot":
        # Reset the jackpot
        combo_events: Dict[str, ReelSymbol] = (
            g.slot_machine.configuration["combo_events"])
        jackpot_seed: int = combo_events["jackpot"]["fixed_amount"]
        g.slot_machine.jackpot = jackpot_seed
    else:
        g.slot_machine.jackpot += 1
# endregion
