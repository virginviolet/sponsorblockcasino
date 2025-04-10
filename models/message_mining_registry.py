# region Imports
# Standard Library
import json
from pathlib import Path
from os.path import exists
from os import stat, stat_result
from time import time
from dataclasses import asdict
from typing import TypeGuard, Any, Dict, List, cast

# Local
from type_aliases import (MessageMiningTimeline, CoinReaction, ReactionUser,
                          ReactionUserDict)
# endregion

# region Type guard
def is_dataclass_instance(obj: object) -> TypeGuard[Any]:
    return hasattr(obj, "__dataclass_fields__")


# endregion

# region JSON encoder
class DataclassJsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for dataclass objects.
    """

    def default(self, o: object) -> Any:
        if hasattr(o, "__dataclass_fields__"):
            if is_dataclass_instance(o):
                # Convert dataclass to dict and then to JSON
                return asdict(o)
        return super().default(o)
# endregion

# region Registry


class MessageMiningRegistryManager:
    """
    Manages the coin reactions for all messages with coin reactions.
    """
    def __init__(self,
                 registry_path: str = (
                     "data/message_mining_registry.json")) -> None:
        """
        Initialize the MessageMiningTracker with an optional path to the
        messages mined for file.

        :param message_mining_registry_path: Path to the messages mined for file.
        """
        self.registry_path: Path = Path(registry_path)
        self.messages: Dict[str, MessageMiningTimeline] = (
            self.load_messages())

    def load_messages(self) -> Dict[str, MessageMiningTimeline]:
        """
        Load the messages mined for from the JSON file.

        :return: The loaded messages mined for.
        """
        file_exists: bool = exists(self.registry_path)
        file_empty: bool | None = None
        if file_exists:
            file_stat: stat_result = stat(self.registry_path)
            file_stat = stat(self.registry_path)
            file_size: int = file_stat.st_size
            file_empty = file_size == 0
        if file_exists is False or file_empty is True:
            # Create the directory if it doesn't exist
            print(f"WARNING: A new message_mining_registry file "
                  f"will be created at {self.registry_path}.", flush=True)
            self.registry_path.parent.mkdir(parents=True,
                                            exist_ok=True)
            # Create an empty file if it doesn't exist or is empty
            with open(self.registry_path, "w") as file:
                empty_registry: Dict[str, Dict[str, MessageMiningTimeline]] = (
                    {"messages": {}})
                file.write(json.dumps(empty_registry, indent=4,
                           cls=DataclassJsonEncoder))
                file.close()
            return {}
        with open(self.registry_path, "r") as file:
            # Read the JSON file,
            # reconstruct the registry so that the user dictionaries are
            # converted into ReactionUser dataclass instances
            registry_raw: Dict[str, Dict[str, MessageMiningTimeline]] = (
                json.loads(file.read()))
            messages_raw: Dict[str, MessageMiningTimeline] = (
                registry_raw.get("messages", {}))
            messages_reconstructed: Dict[str, MessageMiningTimeline] = {}
            for message_id_str, message in messages_raw.items():
                message_reconstructed: MessageMiningTimeline = message
                reactions_raw: List[CoinReaction] = (
                    message_reconstructed["reactions"])
                reactions_reconstructed: list[CoinReaction] = []
                for reaction in reactions_raw:
                    reaction_reconstructed: CoinReaction = reaction
                    user_raw: ReactionUserDict = (
                        cast(ReactionUserDict, reaction["user"]))
                    user_reconstructed: ReactionUser = ReactionUser(
                        global_name=user_raw["global_name"],
                        id=user_raw["id"],
                        name=user_raw["name"],
                        mention=user_raw["mention"]
                    )
                    reaction_reconstructed["user"] = user_reconstructed
                    reactions_reconstructed.append(reaction_reconstructed)
                message_reconstructed["reactions"] = reactions_reconstructed
                messages_reconstructed[message_id_str] = message_reconstructed
            return messages_reconstructed

    def add_reaction(self,
                     message_id: int,
                     message_timestamp: float,
                     message_author_id: int,
                     message_author_name: str,
                     channel_id: int,
                     user_id: int,
                     user_name: str,
                     user_global_name: str | None,
                     user_mention: str,
                     created_at: float | None) -> None:
        """
        Add a reaction to the messages mined for.

        :param message_id: The ID of the message.
        :param user_id: The ID of the user who reacted.
        :param user_name: The name of the user who reacted.
        """
        # Check if the message ID is already in the messages mined for
        message_found: bool = False
        reaction_found: bool = False
        # Json keys cannot be integers, so convert to string
        message_id_str: str = str(message_id)
        if message_id_str in self.messages.keys():
            message_found = True
            for reaction in self.messages[message_id_str]["reactions"]:
                user: ReactionUser | ReactionUserDict = reaction["user"]
                if not isinstance(user, ReactionUser):
                    raise TypeError(
                        f"Expected ReactionUser, got {type(user)}")
                if user.id == user_id and created_at is not None:
                    # Reaction already exists, update it
                    # reaction["created_at"] = created_at
                    # user.global_name = user_global_name
                    # user.mention = user_mention
                    # user.name = user_name
                    reaction_found = True
                    break
        if not reaction_found:
            if created_at is None:
                created_at = time()
            user = ReactionUser(
                global_name=user_global_name,
                id=user_id,
                name=user_name,
                mention=user_mention
            )
            reaction: CoinReaction = {
                "created_at": created_at,
                "user": user
            }
            if message_found:
                self.messages[message_id_str]["reactions"].append(reaction)
            else:
                self.messages[message_id_str] = {
                    "author_id": message_author_id,
                    "author_name": message_author_name,
                    "channel_id": channel_id,
                    "created_at": message_timestamp,
                    "reactions": [reaction]
                }
            with open(self.registry_path, "w") as file:
                message_registry: (
                    Dict[str, Dict[str, MessageMiningTimeline]]) = (
                        {"messages": self.messages})
                file.write(
                    json.dumps(
                        message_registry, indent=4, cls=DataclassJsonEncoder))
                file.close()

    def get_reactions(self, message_id: int) -> list[CoinReaction]:
        """
        Get the reactions for a message.

        :param message_id: The ID of the message.
        :return: The reactions for the message.
        """
        # Json keys cannot be integers, so convert to string
        message_id_str: str = str(message_id)
        if message_id_str in self.messages.keys():
            return self.messages[message_id_str]["reactions"]
        return []

    def get_reacters(self, message_id: int) -> list[ReactionUser]:
        """
        Get the reacters for a message.

        :param message_id: The ID of the message.
        :return: The reacters for the message.
        """
        message_id_str: str = str(message_id)
        if message_id_str in self.messages.keys():
            reacters: list[ReactionUser] = [
                cast(ReactionUser, reaction["user"]) for reaction
                in self.messages[message_id_str]["reactions"]]
            return reacters
        return []
# endregion
