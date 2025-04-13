# region Imports
# Standard library
from pathlib import Path
from time import time
from typing import List, cast, Literal

# Third party
from humanfriendly import format_timespan
from discord import (Interaction, Member, Message, User, TextChannel,
                     VoiceChannel, app_commands, CategoryChannel,
                     ForumChannel, StageChannel, Thread, AllowedMentions, File)
from discord.abc import PrivateChannel
from discord.ext.commands import Bot  # pyright: ignore [reportMissingTypeStubs]

# Local
import core.global_state as g
from sponsorblockcasino_types import TransactionRequest
from models.transfers_waiting_approval import TransfersWaitingApproval
from models.user_save_data import UserSaveData
from models.log import Log
from views.aml_view import AmlView
from utils.blockchain_utils import transfer_coins
from utils.formatting import format_coin_label, format_timestamp
from utils.roles import test_invoker_is_aml_officer
# endregion


aml_group = app_commands.Group(
    name="aml", description="Use an Anti-money laundering workstation")

# region approve


@aml_group.command(name="approve",
                   description="Approve transactions that require "
                   "manual approval")
async def approve(interaction: Interaction) -> None:
    """
    Command to approve or decline large transactions.
    """
    assert isinstance(g.bot, Bot), "g.bot is not initialized."
    assert isinstance(g.transfers_waiting_approval, TransfersWaitingApproval), (
        "g.transfers_waiting_approval is not initialized.")
    assert isinstance(g.log, Log), "g.log is not initialized."
    invoker_has_aml_role: bool = test_invoker_is_aml_officer(interaction)
    if not invoker_has_aml_role:
        message_content: str = "You are not an AML officer."
        await interaction.response.send_message(message_content)
        del message_content
        return

    invoker: User | Member = interaction.user
    invoker_name: str = invoker.name
    invoker_id: int = invoker.id
    transfers_list: List[TransactionRequest] = g.transfers_waiting_approval.load()
    has_sent_message = False
    for transfer in transfers_list:
        sender_id: int = transfer["sender_id"]
        sender: User | None = g.bot.get_user(sender_id)
        if sender is None:
            print(f"ERROR: Could not get user with ID {transfer['sender_id']}")
            continue
        sender_mention: str = sender.mention
        sender_id: int = transfer["sender_id"]
        receiver_id: int = transfer["receiver_id"]
        receiver: User | None = g.bot.get_user(receiver_id)
        if receiver is None:
            print("ERROR: Could not get user "
                  f"with ID {transfer['receiver_id']}")
            continue
        receiver_mention: str = receiver.mention
        amount: int = transfer["amount"]
        channel_id: int = transfer["channel_id"]
        channel: (VoiceChannel | StageChannel | ForumChannel | TextChannel |
                  CategoryChannel | Thread | PrivateChannel
                  | None) = g.bot.get_channel(channel_id)
        if channel is None:
            print("ERROR: channel is None.")
            continue
        elif isinstance(channel,
                        (PrivateChannel, ForumChannel, CategoryChannel)):
            # [ ] Test
            print(f"ERROR: channel is a {type(channel).__name__}.")
            continue
        transfer_message_id: int = transfer["message_id"]
        transfer_message: Message = (
            await channel.fetch_message(transfer_message_id))
        if not isinstance(transfer_message, Message):
            print(f"ERROR: Could not get message "
                  f"with ID {transfer_message_id}")
            continue
        purpose: str = transfer["purpose"]
        request_timestamp: float = transfer["request_timestamp"]
        log_timestamp: float = time()
        time_elapsed: float = log_timestamp - request_timestamp
        time_elapsed_friendly: str = format_timespan(time_elapsed)
        transfer_message_link: str = transfer_message.jump_url
        message_content = (f"Sender: {sender_mention}\n"
                           f"Receiver: {receiver_mention}\n"
                           f"Amount: {amount} {g.coins}\n"
                           f"When: {time_elapsed_friendly} ago\n"
                           f"Purpose: \"{purpose}\"\n"
                           f"{transfer_message_link}")
        if not has_sent_message:
            # Use interaction.response.send_message
            aml_view = AmlView(
                interaction=interaction,
                initial_message=message_content)
            await interaction.response.send_message(
                content=message_content,
                view=aml_view,
                allowed_mentions=AllowedMentions.none())
            has_sent_message = True
        else:
            # Requires interaction.followup.send
            aml_view = AmlView(
                interaction=interaction,
                initial_message=message_content)
            followup_message: Message | None = await interaction.followup.send(
                content=message_content,
                view=aml_view,
                allowed_mentions=AllowedMentions.none())
            aml_view.followup_message = followup_message
        wait: bool = await aml_view.wait()
        timed_out: bool = True if wait else False
        if timed_out:
            return
        transaction_approved: bool = aml_view.approved
        request_timestamp_friendly: str = (
            format_timestamp(request_timestamp, g.time_zone))
        log_timestamp = time()
        action: str
        if transaction_approved:
            action = "approved"
        else:
            action = "declined"
        log_message: str = (f"AML officer {invoker_name} ({invoker_id}) "
                            f"{action} {sender} ({sender_id})'s transfer "
                            f"of {amount} {g.coins} "
                            f"to {receiver} ({receiver_id}) "
                            f"dated {request_timestamp_friendly}.")
        del action
        g.log.log(log_message, log_timestamp)
        del log_message
        if transaction_approved:
            await transfer_coins(
                sender=sender, receiver=receiver, amount=amount,
                method="transfer_aml", channel_id=channel_id)
        else:
            # TODO Let AML officer provide a reason for declining the transaction
            coin_label: str = format_coin_label(amount)
            message_content = (
                f"{sender_mention} Your transfer of {amount} {coin_label} "
                f"to {receiver_mention} has been declined by an AML officer.\n"
                f"{transfer_message_link}")
            await channel.send(message_content)
            del message_content
        g.transfers_waiting_approval.remove(transfer)
    message_content = "All transactions have been processed."
    if not has_sent_message:
        await interaction.response.send_message(message_content)
    else:
        await interaction.followup.send(message_content)
    del message_content
# endregion

# region block_receivals


@aml_group.command(name="block_receivals",
                   description=f"Block a user from receiving {g.coins}")
@app_commands.describe(user=(f"User to block from receiving {g.coins}"))
@app_commands.describe(blocked=(f"Set whether the user should be blocked "
                                f"from receiving {g.coins}"))
@app_commands.describe(reason="Reason for blocking user from "
                       f"receiving {g.coins}")
async def block_receivals(interaction: Interaction,
                          user: User | Member,
                          blocked: bool | None = None,
                          reason: str | None = None) -> None:
    """
    Command to approve large transactions.
    """
    # TODO Add parameter to check reason for block
    if blocked and not reason:
        message_content: str = ("You must provide a reason for blocking "
                                "the user from receiving coins.")
        await interaction.response.send_message(message_content, ephemeral=True)
        del message_content
        return

    invoker_has_aml_role: bool = test_invoker_is_aml_officer(interaction)
    if not invoker_has_aml_role:
        message_content: str = "You are not an AML officer."
        await interaction.response.send_message(message_content)
        del message_content
        return

    user_id: int = user.id
    user_name: str = user.name
    user_mention: str = user.mention
    user_save_data = UserSaveData(user_id=user_id, user_name=user_name)
    message_content: str
    if blocked is None:
        is_blocked: bool = user_save_data.blocked_from_receiving_coins
        blocked_or_not_blocked: (
            Literal['blocked'] | Literal['not blocked']) = (
            "blocked" if is_blocked else "not blocked")
        message_content = (f"User {user_mention} is currently "
                           f"{blocked_or_not_blocked} from receiving {g.coins}.")
    else:
        blocked_or_unblocked: Literal['blocked'] | Literal['unblocked'] = (
            "blocked" if blocked else "unblocked")
        user_save_data.blocked_from_receiving_coins = blocked
        if blocked:
            user_save_data.blocked_from_receiving_coins_reason = reason
        else:
            user_save_data.blocked_from_receiving_coins_reason = None
        message_content = (f"User {user_mention} has been "
                           f"{blocked_or_unblocked} from receiving {g.coins}.")
    await interaction.response.send_message(
        message_content, allowed_mentions=AllowedMentions.none())
    del message_content
    return
# endregion

# region decrypt tx


@aml_group.command(name="decrypt_spreadsheet",
                   description=f"Block a user from receiving {g.coins}")
@app_commands.describe(user="Filter transactions by user",
                       user_name="Filter transactions by user name")
async def decrypt_spreadsheet(interaction: Interaction,
                              user: User | Member | None = None,
                              user_name: str | None = None) -> None:
    if g.decrypted_transactions_spreadsheet is None:
        message_content: str = (
            "Could not make a decrypted transactions spreadsheet.")
        await interaction.response.send_message(
            message_content, ephemeral=True)
        del message_content
        raise ValueError("decrypted_transactions_spreadsheet is None.")
    user_id: int | None = None
    message_content: str
    if user or user_name:
        user_formatted: str
        if user and user_name:
            user_user_name: str = user.name
            if user_name != user_user_name:
                message_content = (
                    "Using both the `user` and the `user_name` parameter "
                    "is not supported.")
                await interaction.response.send_message(
                    message_content, ephemeral=True)
                del message_content
                return

        if user:
            user_id = user.id
            user_formatted = user.mention
        else:
            user_name = cast(str, user_name)
            user_formatted = user_name
        message_content = ("Here is the decrypted transactions history "
                           f"for {user_formatted}.")
    else:
        message_content = (
            "The transactions spreadsheet has been decrypted.")
    try:
        g.decrypted_transactions_spreadsheet.decrypt(user_id, user_name)
        spreadsheet_path: Path = (
            g.decrypted_transactions_spreadsheet.decrypted_spreadsheet_path)
        with open(spreadsheet_path, 'rb') as f:
            decrypted_transactions_spreadsheet_file = File(f)
            await interaction.response.send_message(message_content,
                                                    file=decrypted_transactions_spreadsheet_file,
                                                    allowed_mentions=AllowedMentions.none())
    except Exception as e:
        error_message: str = ("An error occurred while decrypting the "
                              f"transactions spreadsheet: {e}")
        print(f"ERROR: {error_message}")
        await interaction.response.send_message(
            error_message, ephemeral=True)
        del error_message
        raise e
    del message_content
    return
# endregion
