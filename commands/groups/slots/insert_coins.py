# region Imports
# Standard library
import asyncio
from time import time
from hashlib import sha256
from typing import Dict, List, cast

# Third party
from humanfriendly import format_timespan
from discord import (Interaction, Member, PartialEmoji, User, app_commands,
                     Client)
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
from type_aliases import ReelSymbol,  ReelResults, SpinEmojis
from core.terminate_bot import terminate_bot
from models.slot_machine import SlotMachine
from models.grifter_suppliers import GrifterSuppliers
from models.log import Log
from models.user_save_data import UserSaveData
from utils.blockchain_utils import (add_block_transaction,
                                    get_last_block_timestamp)
from utils.formatting import format_coin_label
from views.starting_bonus_view import StartingBonusView
from views.slot_machine_buttons import SlotMachineView
from blockchain.models.blockchain import Blockchain
from .slots_main import slots_group
from .slots_utils import remove_from_active_players
# endregion

# region insert_coins


@slots_group.command(name="insert_coins",
                     description=f"Play on a {g.Coin} Slot Machine")
@app_commands.describe(amount="The amount of coins to stake")
@app_commands.describe(private_room=(
    "Whether you want to book a private room or not"))
async def insert_coins(interaction: Interaction,
                       amount: str = "1",
                       private_room: bool | None = None) -> None:
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

    GrifterSwap suppliers are denied a new starting.

    See the "show_help" subcommand module for more information about the game.

    Args:
    interaction  -- The interaction object representing the
                    command invocation.
    amount        -- Sets the stake/wager (default 1)
    private_room -- Makes the bot's messages ephemeral
                    (only visible to the invoker) (default False)
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

    user: User | Member = interaction.user
    user_id: int = user.id

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

    amount_int: int
    amount_is_int: bool = False
    if amount.lower() != "all" and amount.lower() != "max":
        try:
            int(amount)
        except ValueError:
            if private_room is False:
                should_use_ephemeral = False
            else:
                should_use_ephemeral = True
            message_content = ("Input a valid number of coins to stake.")
            await interaction.response.send_message(
                message_content, ephemeral=should_use_ephemeral)
            return

    if private_room:
        should_use_ephemeral = True
    else:
        should_use_ephemeral = False

    if amount_is_int and amount_int < 0:
        message_content = "Thief!"
        await interaction.response.send_message(
            message_content, ephemeral=False)
        return
    elif amount_is_int and amount_int == 0:
        message_content = "Insert coins to play!"
        await interaction.response.send_message(
            message_content, ephemeral=should_use_ephemeral)
        return
    # TODO Log/stat outcomes (esp. wager amounts)

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

    if amount.lower() == "all" or amount.lower() == "max":
        amount_int = user_balance
    else:
        amount_int = int(amount)

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
            await remove_from_active_players(interaction, user_id)
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
                await remove_from_active_players(interaction, user_id)
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
        await remove_from_active_players(interaction, user_id)
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
        for die_roll, resulting_amount in starting_bonus_awards.items():
            starting_bonus_table += f"> {die_roll}\t\t\t\t{resulting_amount}\n"
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
        await remove_from_active_players(interaction, user_id)
        return

    del has_played_before

    if user_balance < amount_int:
        coin_label_w: str = format_coin_label(amount_int)
        coin_label_b: str = format_coin_label(user_balance)
        message_content = (f"You do not have enough {g.coins} "
                           f"to stake {amount_int} {coin_label_w}.\n"
                           f"Your current balance is {user_balance} {coin_label_b}.")
        await interaction.response.send_message(
            content=message_content, ephemeral=True)
        del coin_label_w
        del coin_label_b
        del message_content
        if user_id in g.active_slot_machine_players:
            await remove_from_active_players(interaction, user_id)
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
        amount_int >= (low_wager_main_fee + low_wager_jackpot_fee))
    no_jackpot_mode: bool = False if jackpot_fee_paid else True
    jackpot_fee: int
    main_fee: int
    if no_jackpot_mode:
        # IMPROVE Make min_wager config keys
        main_fee = low_wager_main_fee
        jackpot_fee = 0
    elif amount_int < 10:
        main_fee = low_wager_main_fee
        jackpot_fee = low_wager_jackpot_fee
    elif amount_int < 100:
        main_fee_unrounded: float = amount_int * medium_wager_main_fee
        main_fee = round(main_fee_unrounded)
        jackpot_fee_unrounded: float = amount_int * medium_wager_jackpot_fee
        jackpot_fee = round(jackpot_fee_unrounded)
    else:
        main_fee_unrounded: float = amount_int * high_wager_main_fee
        main_fee = round(main_fee_unrounded)
        jackpot_fee_unrounded: float = amount_int * high_wager_jackpot_fee
        jackpot_fee = round(jackpot_fee_unrounded)
    fees: int = jackpot_fee + main_fee

    spin_emojis: SpinEmojis = g.slot_machine.configuration["reel_spin_emojis"]
    spin_emoji_1_name: str = spin_emojis["spin1"]["emoji_name"]
    spin_emoji_1_id: int = spin_emojis["spin1"]["emoji_id"]
    spin_emoji_1 = PartialEmoji(name=spin_emoji_1_name,
                                id=spin_emoji_1_id,
                                animated=True)
    reels_row: str = f"{spin_emoji_1}\t\t{spin_emoji_1}\t\t{spin_emoji_1}"
    wager_row: str = f"-# Coin: {amount_int}"
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
        g.slot_machine.calculate_award_money(wager=amount_int,
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
                         f"stake of {amount_int} {coin_label_wm}. "
                         "Better luck next time!")
        net_return = -amount_int
        total_return = 0
    else:
        total_return = amount_int + win_money - main_fee - jackpot_fee
    net_return = win_money - main_fee - jackpot_fee
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
                        f"{amount_int} {coin_label_nr} on "
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
                        f"of {amount_int} {coin_label_nr} on the "
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
        await remove_from_active_players(interaction, user_id)

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


@insert_coins.autocomplete(name="amount")
async def amount_autocomplete(interaction: Interaction[Client],
                              current: str) -> List[app_commands.Choice[str]]:
    choices = []
    if current.lower().startswith("a"):
        choices: List[app_commands.Choice[str]] = (
            [app_commands.Choice(name="All", value="all")])
        return choices
    elif current.lower().startswith("m"):
        choices: List[app_commands.Choice[str]] = (
            [app_commands.Choice(name="Max", value="max")])
        return choices
    return choices
# endregion
