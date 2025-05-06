"""
Functions for interacting with the blockchain from the Discord bot.
"""
# region Imports
# Standard Library
import asyncio
from time import time
from hashlib import sha256
from typing import TYPE_CHECKING

# Third party
from discord import (
    Guild, Interaction, Member, Message, Role, User, TextChannel, VoiceChannel,
    CategoryChannel, ForumChannel, StageChannel, Thread, AllowedMentions,
    InteractionMessage)
from discord.abc import PrivateChannel
from discord.utils import MISSING
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)

# Local
if TYPE_CHECKING:
    from sponsorblockchain.sponsorblockchain_types import (
        BlockData)
import core.global_state as g
from schemas.typed import TransactionRequest
from schemas.data_classes import ReactionUser
from core.terminate_bot import terminate_bot
from models.log import Log
from models.transfers_waiting_approval import TransfersWaitingApproval
from models.user_save_data import UserSaveData
from utils.donation_goal_apply_setting import apply_donation_reward
from utils.formatting import format_coin_label
from utils.roles import get_aml_officer_role
from sponsorblockchain.sponsorblockchain_types import Transaction
from sponsorblockchain.models.blockchain import Blockchain
from sponsorblockchain.models.block import Block
# endregion

# region Get timestamp


def get_last_block_timestamp() -> float | None:
    """
    Retrieves the timestamp of the last block in the blockchain.

    Returns:
        float | None: The timestamp of the last block if available,
        otherwise None.

    Raises:
        Exception: If there is an error retrieving the last block.
    """
    if g.blockchain is None:
        raise ValueError("blockchain is None.")

    last_block_timestamp: float | None = None
    try:
        # Get the last block's timestamp for logging
        last_block: None | Block = g.blockchain.get_last_block()
        if last_block is not None:
            last_block_timestamp = last_block.timestamp
            del last_block
        else:
            print("ERROR: Last block is None.")
            return None
    except Exception as e:
        print(f"ERROR: Error getting last block: {e}")
        return None
    return last_block_timestamp


# endregion

# region Add tx block


async def add_block_transaction(blockchain: Blockchain,
                                sender: Member | User | ReactionUser | int,
                                receiver: Member | User | ReactionUser | int,
                                amount: int,
                                method: str) -> None:
    """
    Adds a transaction to the blockchain.

    Args:
        blockchain: The blockchain instance to which the transaction will
            be added.
        sender: The sender of the transaction. Can be a Member, User,
            or an integer User ID.
        receiver: The receiver of the transaction. Can be a Member, User,
            or an integer ID.
        amount: The amount of the transaction.
        method: The method of the transaction; "reaction", "slot_machine",
            "transfer".

    Raises:
        Exception: If there is an error adding the transaction to
            the blockchain.
    """
    sender_id: int
    receiver_id: int
    if isinstance(sender, int):
        sender_id = sender
    else:
        sender_id = sender.id
    if isinstance(receiver, int):
        receiver_id = receiver
    else:
        receiver_id = receiver.id
    sender_id_unhashed: int = sender_id
    receiver_id_unhashed: int = receiver_id
    sender_id_hash: str = (
        sha256(str(sender_id_unhashed).encode()).hexdigest())
    del sender_id
    del sender_id_unhashed
    receiver_id_hash: str = (
        sha256(str(receiver_id_unhashed).encode()).hexdigest())
    del receiver_id
    del receiver_id_unhashed
    print("Adding transaction to blockchain...")
    try:
        transaction = Transaction(
            sender=sender_id_hash,
            receiver=receiver_id_hash,
            amount=amount,
            method=method
        )
        data: BlockData = (
            [{"transaction": transaction}])
        blockchain.add_block(data=data, difficulty=0)
    except Exception as e:
        print(f"ERROR: Error adding transaction to blockchain: {e}")
        await terminate_bot()
    print("Transaction added to blockchain.")
# endregion

# region Transfer


async def transfer_coins(sender: Member | User,
                         receiver: Member | User,
                         amount: int,
                         method: str,
                         channel_id: int,
                         purpose: str | None = None,
                         interaction: Interaction | None = None) -> None:
    """
    Transfers coins from one user to another.
    Only pass the interaction parameter if the transfer is immediately
    initiated by the one who wishes to make a transfer.
    """
    assert isinstance(g.bot, Bot), "g.bot is not initialized."
    assert isinstance(g.log, Log), "g.log is not initialized."
    assert isinstance(
        g.transfers_waiting_approval, TransfersWaitingApproval), (
        "g.transfers_waiting_approval is not initialized.")
    if g.blockchain is None:
        raise ValueError("blockchain is None.")
    if interaction:
        channel = interaction.channel
    else:
        channel: (VoiceChannel | StageChannel | ForumChannel | TextChannel |
                  CategoryChannel | Thread | PrivateChannel | None) = (
            g.bot.get_channel(channel_id))

    async def send_message(message_text: str,
                           ephemeral: bool = False,
                           allowed_mentions: AllowedMentions = MISSING
                           ) -> None:
        if interaction is None:
            if channel is None:
                print("ERROR: channel is None.")
                return
            elif isinstance(channel,
                            (PrivateChannel, ForumChannel, CategoryChannel)):
                # [ ] Test
                print(f"ERROR: channel is a {type(channel).__name__}.")
                return
            await channel.send(content=message_text)
        else:
            if not has_responded:
                await interaction.response.send_message(
                    content=message_text,
                    ephemeral=ephemeral,
                    allowed_mentions=allowed_mentions)
            else:
                await interaction.followup.send(
                    content=message_text,
                    ephemeral=ephemeral,
                    allowed_mentions=allowed_mentions)

    has_responded: bool = False
    sender_id: int = sender.id
    receiver_id: int = receiver.id
    coin_label_a: str = format_coin_label(amount)
    sender_mention: str = sender.mention
    if not interaction:
        await send_message(f"{sender_mention} Your transfer request "
                           "has been approved.")
        has_responded = True
    print(f"User {sender_id} is attempting to transfer "
          f"{amount} {coin_label_a} to user {receiver_id}...")
    balance: int | None = None
    if amount == 0:
        message_content = "You cannot transfer 0 coins."
        await send_message(message_content, ephemeral=True)
        del message_content
        return
    elif amount < 0:
        message_content = "You cannot transfer a negative amount of coins."
        await send_message(message_content, ephemeral=True)
        del message_content
        return

    try:
        balance = g.blockchain.get_balance(user_unhashed=sender_id)
    except Exception as e:
        administrator: str = (
            await g.bot.fetch_user(g.administrator_id)).mention
        await send_message(f"Error getting balance. {administrator} pls fix.")
        error_message: str = ("ERROR: Error getting balance "
                              f"for user {sender} ({sender_id}): {e}")
        raise Exception(error_message)
    if balance is None:
        print(f"Balance is None for user {sender} ({sender_id}).")
        await send_message(f"You have 0 {g.coins}.")
        return
    if balance < amount:
        print(f"{sender} ({sender_id}) does not have enough {g.coins} to "
              f"transfer {amount} {coin_label_a} to {sender} ({sender_id}). "
              f"Balance: {balance}.")
        coin_label_b: str = format_coin_label(balance)
        await send_message(
            f"You do not have enough {g.coins}. "
            f"You have {balance} {coin_label_b}.", ephemeral=True)
        del coin_label_b
        return
    del balance

    if interaction:
        receiver_name: str = receiver.name
        recipient_account_data = UserSaveData(
            user_id=receiver_id, user_name=receiver_name)
        recipient_receive_blocked: bool = (
            recipient_account_data.blocked_from_receiving_coins)
        if recipient_receive_blocked:
            receiver_mention: str = receiver.mention
            aml_role: None | Role = get_aml_officer_role(interaction)
            if aml_role is None:
                raise Exception("aml_role is None.")
            aml_mention: str = aml_role.mention
            message_content = (f"{receiver_mention} has been blocked from "
                               f"receiving {g.coins}.\n"
                               "-# If you believe this is a "
                               "mistake, please contact "
                               "an anti-money-laundering officer by "
                               f"mentioning {aml_mention}.")
            await send_message(
                message_content, allowed_mentions=AllowedMentions.none())
            del message_content
            return
        if ((amount > g.auto_approve_transfer_limit) and
            (sender_id != g.grifter_swap_id) and
                (receiver_id != g.grifter_swap_id)):
            # Unhindered transfers between GrifterSwap (abuse is mitigated by
            # the GrifterSwap supplier check in the /slots command)
            print(f"Transfer amount exceeds auto-approval limit of "
                  f"{g.auto_approve_transfer_limit}.")
            receiver_mention: str = receiver.mention
            if purpose is None:
                message_content: str = (
                    f"Anti-money laundering policies (AML) requires us to "
                    "manually approve this transaction. "
                    "Please state your purpose of transferring "
                    f"{amount} {coin_label_a} to {receiver_mention}.")
                await send_message(message_content)
                del message_content
                has_responded = True

                def check(message: Message) -> bool:
                    message_author: User | Member = message.author
                    return message_author == sender
                try:
                    purpose_message: Message = await g.bot.wait_for(
                        "message", timeout=60, check=check)
                except asyncio.TimeoutError:
                    message_content = "Come back when you have a purpose."
                    await interaction.followup.send(message_content)
                    del message_content
                    return
                purpose = purpose_message.content
            else:
                # Need to defer to get a message id
                # (used to make a message link in /aml)
                await interaction.response.defer()
            request_timestamp: float = time()
            interaction_message: InteractionMessage = (
                await interaction.original_response())
            interaction_message_id: int = interaction_message.id
            del interaction_message
            if channel is None:
                raise Exception("channel is None.")
            transaction_request: TransactionRequest = {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "amount": amount,
                "request_timestamp": request_timestamp,
                "channel_id": channel_id,
                "message_id": interaction_message_id,
                "purpose": purpose
            }
            try:
                g.transfers_waiting_approval.add(transaction_request)
                awaiting_approval_message_content: str = (
                    f"A request for transferring {amount} {coin_label_a} "
                    f"to {receiver_mention} has been sent for approval.")
                await interaction.followup.send(
                    awaiting_approval_message_content,
                    allowed_mentions=AllowedMentions.none())
                log_message: str = (
                    f"A request for transferring {amount} {coin_label_a} "
                    f"to {receiver_mention} for the purpose of \"{purpose}\" "
                    "has been sent for approval.")
                g.log.log(log_message, request_timestamp)
                del log_message
            except Exception as e:
                administrator: str = (
                    (await g.bot.fetch_user(g.administrator_id)).mention)
                message_content = ("Error sending transfer request.\n"
                                   f"{administrator} pls fix.")
                await interaction.followup.send(message_content)
                del message_content
                error_message = ("ERROR: Error adding transaction request "
                                 f"to queue: {e}")
                raise Exception(error_message)
            try:
                if ((g.aml_office_channel_id == 0) and
                        (g.aml_office_thread_id == 0)):
                    raise Exception(
                        "aml_office_channel_id and aml_office_thread_id "
                        "are both 0.")
                guild: Guild | None = interaction.guild
                if guild is None:
                    print("ERROR: Guild is None.")
                    return
                aml_officer: Role | None = get_aml_officer_role(
                    interaction)
                if aml_officer is None:
                    raise Exception("aml_officer is None.")
                aml_officer_mention: str = aml_officer.mention
                aml_office_message: str = (
                    aml_officer_mention +
                    awaiting_approval_message_content)
                if g.aml_office_channel_id != 0:
                    aml_office_channel: (
                        VoiceChannel | StageChannel | ForumChannel |
                        TextChannel | CategoryChannel | PrivateChannel |
                        Thread) = (
                            await g.bot.fetch_channel(g.aml_office_channel_id))
                    if isinstance(aml_office_channel,
                                  (PrivateChannel, ForumChannel,
                                   CategoryChannel, Thread)):
                        raise Exception(
                            "aml_office_channel is a "
                            f"{type(aml_office_channel).__name__}.")
                    await aml_office_channel.send(
                        aml_office_message,
                        allowed_mentions=AllowedMentions.none())
                if g.aml_office_thread_id != 0:
                    aml_office_thread: (
                        VoiceChannel | StageChannel | ForumChannel |
                        TextChannel | CategoryChannel | PrivateChannel |
                        Thread) = (
                            await g.bot.fetch_channel(g.aml_office_thread_id))
                    if not isinstance(aml_office_thread, Thread):
                        raise Exception(
                            "aml_office_thread is a "
                            f"{type(aml_office_thread).__name__}.")
                    await aml_office_thread.send(
                        aml_office_message,
                        allowed_mentions=AllowedMentions.none())
            except Exception as e:
                administrator: str = (
                    (await g.bot.fetch_user(g.administrator_id)).mention)
                message_content = (
                    "There was an error notifying the AML office.\n"
                    f"{administrator} pls fix.")
                await interaction.followup.send(message_content)
                del message_content
                error_message = ("ERROR: Error sending transfer request "
                                 f"to AML office: {e}")
                raise Exception(error_message)
            return

    await add_block_transaction(blockchain=g.blockchain,
                                sender=sender,
                                receiver=receiver,
                                amount=amount,
                                method=method)
    last_block: Block | None = g.blockchain.get_last_block()
    if last_block is None:
        print("ERROR: Last block is None.")
        administrator: str = (
            await g.bot.fetch_user(g.administrator_id)).mention
        await send_message(f"Error transferring {g.coins}. "
                           f"{administrator} pls fix.")
        await terminate_bot()
        raise Exception("Last block is None.")
    timestamp: float = last_block.timestamp
    g.log.log(line=f"{sender} ({sender_id}) transferred "
              f"{amount} {coin_label_a} "
              f"to {receiver} ({receiver_id}).",
              timestamp=timestamp)

    # Prepare transferred message
    sender_mention: str = sender.mention
    receiver_mention: str = receiver.mention
    transferred_message_content: str = (
        f"{sender_mention} transferred "
        f"{amount} {coin_label_a} "
        f"to {receiver_mention}'s account.")
    allowed_pings = AllowedMentions(users=[receiver])
    # Donation goal
    donation_goal_update_message: str = ""
    donation_goal_reached_message: str = ""
    if (g.donation_goal is not None and
            g.donation_goal.donation_recipient_id == receiver_id):
        g.donation_goal.donated_amount += amount
        remaining_donation_ratio: float = (
            g.donation_goal.donated_amount / g.donation_goal.target_amount)
        if g.donation_goal.donation_recipient_id == g.casino_house_id:
            transferred_message_content += "\nThank you for your donation!"
        donation_goal_update_message = (
            "Donation goal "
            f"for {g.donation_goal.donation_recipient_mention} updated:\n"
            f"## {g.donation_goal.goal_description}\n"
            f"{g.donation_goal.donated_amount}/"
            f"{g.donation_goal.target_amount} {coin_label_a} "
            f"({remaining_donation_ratio:.0%})\n")
        if g.donation_goal.donated_amount >= g.donation_goal.target_amount:
            # Goal reached
            recipient_pronoun: str = (
                "its" if receiver_id == g.casino_house_id else "their")
            coin_label_g: str = format_coin_label(
                g.donation_goal.target_amount)
            donation_goal_reached_message = (
                f"{receiver_mention} has reached "
                f"{recipient_pronoun} donation goal of "
                f"{g.donation_goal.target_amount} {coin_label_g}!\n")
            del coin_label_g
            if g.donation_goal.goal_reached_message_content is not None:
                donation_goal_reached_message += (
                    f"{g.donation_goal.goal_reached_message_content}")
            if (g.donation_goal.reward_setting_key is not None or
                    g.donation_goal.reward_setting_value is not None):
                apply_donation_reward()
            g.donation_goal = None
    await send_message(
        transferred_message_content,
        allowed_mentions=allowed_pings)
    has_responded = True
    if donation_goal_update_message != "":
        await send_message(donation_goal_update_message)
    if donation_goal_reached_message != "":
        await send_message(donation_goal_reached_message)
    del sender
    del sender_id
    del receiver
    del receiver_id
    del amount
    del coin_label_a
# endregion
