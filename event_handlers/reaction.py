# region Imports
# Standard Library
from time import time

# Third party
from discord import Member
from discord.raw_models import RawReactionActionEvent
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)

# Local
import core.global_state as g
from utils.process_reaction import process_reaction
# endregion

# region Reaction
# assert bot is not None, "bot has not been initialized."
assert isinstance(g.bot, Bot), "bot has not been initialized."


@g.bot.event
async def on_raw_reaction_add(payload: RawReactionActionEvent) -> None:
    """
    Handles the event when a reaction is added to a message.
    The process_reaction_function is called, which adds a transaction if the
    reaction is the coin emoji set in the configuration.

    Args:
        payload: An instance of the RawReactionActionEvent
            class from the discord.raw_models module that contains the data of
            the reaction event.
    """
    timestamp: float = time()

    if payload.event_type == "REACTION_ADD":
        if payload.message_author_id is None:
            return

        sender: Member | None = payload.member
        if sender is None:
            print("ERROR: Sender is None.")
            return
        receiver_user_id: int = payload.message_author_id
        message_id: int = payload.message_id
        channel_id: int = payload.channel_id
        await process_reaction(message_id=message_id,
                               emoji=payload.emoji,
                               reacter=sender,
                               message_author_id=receiver_user_id,
                               timestamp=timestamp,
                               channel_id=channel_id)
        del receiver_user_id
        del sender
        del message_id
# endregion
