# region Imports
# Standard library
import json
from os import makedirs, stat
from os.path import exists
from typing import (List, cast)

# Local
from sponsorblockcasino_types import (SaveData, T)
# endregion

# region UserSaveData



class UserSaveData:
    """
    Handles the creation, saving, and loading of user-specific data
    in JSON format.

    ### About `starting_bonus_available` and `when_last_bonus_received`

    The property `starting_bonus_available` can be a unix timestamp that
    signifies when a new bonus will be given out if the command is run, no
    matter what their balance is at that point. It will only become a timestamp
    when the users` account is depleted, effectively starting a timer.

    If it was the case that `starting_bonus_available` was set to a new time
    immediately upon receiving a bonus, then it would become an always recurring
    event, not triggered by the user running out of coins. Therefore, it gets
    set to False after the user has received a bonus.

    Because `starting_bonus_available` is not always a timestamp, we need
    another property - `when_last_bonus_received` - to keep track of when the
    user last received a bonus. This way, we can make sure that the user does
    not receive a bonus too often.

    In short:
    `starting_bonus_available` means: if the user should receive a
    bonus, *or* a point in time when a bonus will be given to them, no matter
    what their balance is at that moment. `when_last_bonus_received` means: the
    point in time when the user last received a bonus.


    Methods:
        __init__(user_id, user_name):
            Initializes the UserSaveData instance with the given user ID
            and name.
        create():
            Creates the necessary directories and files for the user.
        save(key, value):
            Saves a key-value pair to a JSON file. If the file does not exist,
            it creates a new one.
        load(key):
            Loads the value associated with the given key from a JSON file.
            Returns the value associated with the key if it exists,
            otherwise None.
    """

    def __init__(self, user_id: int, user_name: str | None = None) -> None:
        # print("Initializing save data...")
        self.user_id: int = user_id
        self.file_name: str = f"data/save_data/{user_id}/save_data.json"
        self._starting_bonus_available: bool | float
        self._has_visited_casino: bool
        self._reaction_message_received: bool
        self._when_last_bonus_received: float | None
        self._mining_messages_enabled: bool
        self._blocked_from_receiving_coins: bool
        self._blocked_from_receiving_coins_reason: str | None
        self._user_name: str
        file_exists: bool = exists(self.file_name)
        file_empty: bool | None = None
        file_size: int
        if file_exists:
            file_size = stat(self.file_name).st_size
            file_empty = file_size == 0
        if file_empty:
            print(f"ERROR: Save data file for {self.user_id} is empty.")
        if (not file_exists or file_empty) and (user_name is None):
            raise ValueError("user_name must be provided if save data "
                             "does not exist for the user.")
        elif (not file_exists or file_empty) and (user_name is not None):
            self._user_name: str = user_name
            self._has_visited_casino = False
            self._starting_bonus_available = True
            self._when_last_bonus_received = None
            self._reaction_message_received = False
            self._mining_messages_enabled = True
            self._blocked_from_receiving_coins = False
            self._blocked_from_receiving_coins_reason = None
            self.create()
        elif (file_exists) and (not file_empty) and (user_name is None):
            self.user_name: str = self._load_value(
                key="user_name",
                expected_type=str, default="")
            self._load_all_properties()
        else:
            self._load_all_properties()
        # print("Save data initialized.")

    def _load_all_properties(self) -> None:
        """
        Load all properties from the disk.
        """
        self._has_visited_casino = self._load_value(
            key="has_visited_casino",
            expected_type=bool, default=False)
        self._starting_bonus_available = self._load_value(
            key="starting_bonus_available",
            expected_type=(bool, float), default=True)
        self._when_last_bonus_received = self._load_value(
            key="when_last_bonus_received",
            expected_type=(float, type(None)), default=None)
        self._reaction_message_received = self._load_value(
            key="reaction_message_received",
            expected_type=bool, default=False)
        self._mining_messages_enabled = self._load_value(
            key="mining_messages_enabled",
            expected_type=bool, default=True)
        self._blocked_from_receiving_coins = self._load_value(
            key="blocked_from_receiving_coins",
            expected_type=bool, default=False)
        self._blocked_from_receiving_coins_reason = self._load_value(
            key="blocked_from_receiving_coins_reason",
            expected_type=(str, type(None)), default=None)

    def _load_value(self,
                    key: str,
                    expected_type: type[T] | tuple[type, ...],
                    default: T) -> T:
        """
        Load a value from the disk.
        """

        value: str | List[int] | bool | float | None = self.load(key)
        if isinstance(value, expected_type):
            return cast(T, value)
        else:
            found_type = type(value)
            found_type_name: str = found_type.__name__
            if isinstance(expected_type, tuple):
                expected_type_name: str = (
                    ', '.join(t.__name__ for t in expected_type))
            else:
                expected_type_name: str = expected_type.__name__
            print(f"ERROR: Value of '{key}' ('{value}') does not match "
                  f"the expected type. Found '{found_type_name}', expected "
                  f"'{expected_type_name}'. "
                  f"Setting to default value {default}.")
            return default

    @property
    def has_visited_casino(self) -> bool:
        """
        Indicates if the user has visited the casino.
        """
        return self._has_visited_casino

    @has_visited_casino.setter
    def has_visited_casino(self, value: bool) -> None:
        """
        Sets the status of the user's visit to the casino.
        """
        self._has_visited_casino = value
        self.save("has_visited_casino", value)

    @property
    def starting_bonus_available(self) -> bool | float:
        """
        Indicates if they can receive a starting bonus.
        """
        return self._starting_bonus_available

    @starting_bonus_available.setter
    def starting_bonus_available(self, value: bool | float) -> None:
        """
        Sets the status of the starting bonus received.
        """
        self._starting_bonus_available = value
        self.save("starting_bonus_available", value)

    @property
    def when_last_bonus_received(self) -> float | None:
        """
        Indicates when the user last received a bonus.
        """
        return self._when_last_bonus_received

    @when_last_bonus_received.setter
    def when_last_bonus_received(self, value: float) -> None:
        """
        Sets the timestamp of the last bonus received.
        """
        self._when_last_bonus_received = value
        self.save("when_last_bonus_received", value)

    @property
    def reaction_message_received(self) -> bool:
        """
        Indicates if the user has received the reaction message.
        """
        return self._reaction_message_received

    @reaction_message_received.setter
    def reaction_message_received(self, value: bool) -> None:
        """
        Sets the status of the user receiving the reaction message.
        """
        self._reaction_message_received = value
        self.save("reaction_message_received", value)

    @property
    def mining_messages_enabled(self) -> bool:
        """
        Indicates if the user has enabled mining messages.
        """
        return self._mining_messages_enabled

    @mining_messages_enabled.setter
    def mining_messages_enabled(self, value: bool) -> None:
        """
        Sets the user's preference for mining messages.
        """
        self._mining_messages_enabled = value
        self.save("mining_messages_enabled", value)

    @property
    def blocked_from_receiving_coins(self) -> bool:
        """
        Indicates if the user is blocked from receiving coins.
        """
        return self._blocked_from_receiving_coins

    @blocked_from_receiving_coins.setter
    def blocked_from_receiving_coins(self, value: bool) -> None:
        """
        Sets the status of the user being blocked from receiving coins.
        """
        self._blocked_from_receiving_coins = value
        self.save("blocked_from_receiving_coins", value)

    @property
    def blocked_from_receiving_coins_reason(self) -> str | None:
        """
        Indicates the reason the user is blocked from receiving coins.
        """
        return self._blocked_from_receiving_coins_reason

    @blocked_from_receiving_coins_reason.setter
    def blocked_from_receiving_coins_reason(self, value: str | None) -> None:
        """
        Sets the reason the user is blocked from receiving coins.
        """
        self._blocked_from_receiving_coins_reason = value
        self.save("blocked_from_receiving_coins_reason", value)

    def create(self) -> None:
        """
        Creates the necessary directories and files for the user.
        This method performs the following actions:
        1. Creates any missing directories based on the file path.
        2. If a directory name matches the user ID, it creates a JSON file 
           containing the user's name, user ID, and starting bonus status.
        3. Creates an empty save data file specified by `self.file_name`.
        Attributes:
            self.file_name: The path to the save data file.
            self.user_name: The name of the user.
            self.user_id: The ID of the user.
            self._starting_bonus_available: Indicates if the user can receive
            free coins.
        """
        # Create missing directories and create save data file
        directories: str = self.file_name[:self.file_name.rfind("/")]
        for i, directory in enumerate(directories.split("/")):
            path: str = "/".join(directories.split("/")[:i+1])
            if not exists(directory):
                makedirs(path, exist_ok=True)
            if directory.isdigit() and int(directory) == self.user_id:
                with open(self.file_name, "w") as file:
                    file_contents: SaveData = {
                        "user_name": self._user_name,
                        "user_id": self.user_id,
                        "has_visited_casino": False,
                        "starting_bonus_available": (
                            self._starting_bonus_available),
                        "when_last_bonus_received": None,
                        "messages_mined": [],
                        "reaction_message_received": False,
                        "mining_messages_enabled": True,
                        "blocked_from_receiving_coins": False,
                        "blocked_from_receiving_coins_reason": None
                    }
                    file_contents_json: str = json.dumps(file_contents)
                    file.write(file_contents_json)

    def save(self, key: str, value: str | List[int] | float | None) -> None:
        """
        Saves a key-value pair to a JSON file. If the file does not exist,
        it creates a new one.

        Args:
            key: The key to be saved.
            value: The value to be saved.
        """

        # Read the existing data
        save_data: SaveData
        with open(self.file_name, "r") as file:
            save_data = json.load(file)
        # Update the data with the new key-value pair
        save_data[key] = value

        # Write the updated data back to the file
        with open(self.file_name, "w") as file:
            json.dump(save_data, file)

    def load(self, key: str) -> str | List[int] | bool | float | None:
        """
        Loads the value associated with the given key from a JSON file.
        Args:
            key: The key whose value needs to be retrieved.
        Returns:
            str | None: The value associated with the key if it exists,
                            otherwise None.
        """
        if not exists(self.file_name):
            return None
        all_data: SaveData
        with open(self.file_name, "r") as file:
            all_data = json.load(file)
        requested_value: str | List[int] | None = all_data.get(key)
        if ((isinstance(requested_value, str)) and
                (requested_value.lower() == "true")):
            return True
        elif (
            (isinstance(requested_value, str)) and
                (requested_value.lower() == "false")):
            return False
        else:
            return requested_value
# endregion
