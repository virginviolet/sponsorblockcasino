# region Imports
# Standard Library
import json
from os.path import exists
from os import environ as os_environ, makedirs, stat
from typing import Dict, cast, Any

# Local
import core.global_state as g
from schemas.typed import BotConfig
# endregion

# region Bot config


class BotConfiguration:
    """
    A class to handle the bot configuration.

    Methods:
        __init__(file_name = "data/bot_configuration.json"): Initializes
            the bot configuration.
        create(): Creates the necessary directories and a default
            configuration file.
        read(): Reads the bot configuration from a file and overrides it
            with environment variables if they exist.
        """

    def __init__(self, file_name: str = "data/bot_configuration.json") -> None:
        """
        Initializes the bot configuration.

        Args:
            file_name: The path to the configuration file. Defaults
                        to "data/bot_configuration.json".

        Attributes:
            file_name: The path to the configuration file.
            configuration: The bot configuration read from the file.
            coin: The coin name from the configuration.
            Coin: The capitalized coin name from the configuration.
            coins: The plural form of the coin name from the configuration.
            Coins: The capitalized plural form of the coin name from
                the configuration.
            coin_emoji_id: The emoji ID for the coin from the configuration.
            bot_maintainer_id: The bot maintainer ID from the configuration.
            casino_house_id: The casino house ID from the configuration.

        Warnings:
            If `coin_emoji_id` is 0, a warning is printed indicating
                that COIN_EMOJI_ID is not set.
            If `bot_maintainer_id` is 0, a warning is printed indicating
                that bot_maintainer_id is not set.
        """
        print("Initializing bot configuration...")
        # TODO Do not integers as string
        self.file_name: str = file_name
        self._default_config: BotConfig = {
            "Blockchain_name": "Blockchain",
            "Coin": "Coin",
            "Coins": "Coins",
            "aml_office_channel_id": 0,
            "aml_office_thread_id": 0,
            "auto_approve_transfer_limit": 0,
            "blockchain_name": "blockchain",
            "bot_maintainer_id": 0,
            "casino_channel_id": 0,
            "casino_house_id": 0,
            "coin": "coin",
            "coin_emoji_id": 0,
            "coin_emoji_name": "",
            "coins": "coins",
            "grifter_swap_id": 0,
            "leaderboard_holder_blocked": False,
            "leaderboard_slots_highest_wager_blocked": False,
            "leaderboard_slots_highest_win_blocked": False,
            "mining_highlights_channel_id": 0,
            "mining_highlights_channel_name": (
                "the network mining highlights channel"),
            "mining_updates_channel_id": 0,
            "mining_updates_channel_name": "the network mining channel",
            "network_mining_enabled": True,
            "reaction_messages_enabled": True,
            "sbcoin_id": 0
        }
        attributes_set = False
        while attributes_set is False:
            try:
                self.configuration: BotConfig = self.read()
                self.coin: str = self.configuration["coin"]
                self.Coin: str = self.configuration["Coin"]
                self.coins: str = self.configuration["coins"]
                self.Coins: str = self.configuration["Coins"]
                self.coin_emoji_id: int = (
                    self.configuration["coin_emoji_id"])
                self.coin_emoji_name: str = (
                    self.configuration["coin_emoji_name"])
                self.bot_maintainer_id: int = (
                    self.configuration["bot_maintainer_id"])
                self.casino_house_id: int = (
                    self.configuration["casino_house_id"])
                self.casino_channel_id: int = (
                    self.configuration["casino_channel_id"])
                self.mining_updates_channel_id: int = (
                    self.configuration["mining_updates_channel_id"])
                self.mining_updates_channel_name: str = (
                    self.configuration["mining_updates_channel_name"])
                self.mining_highlights_channel_id: int = (
                    self.configuration["mining_highlights_channel_id"])
                self.mining_highlights_channel_name: str = (
                    self.configuration["mining_highlights_channel_name"])
                self.network_mining_enabled: bool = (
                    self.configuration["network_mining_enabled"])
                self.blockchain_name: str = (
                    self.configuration["blockchain_name"])
                self.Blockchain_name: str = (
                    self.configuration["Blockchain_name"])
                self.grifter_swap_id: int = (
                    self.configuration["grifter_swap_id"])
                self.sbcoin_id: int = (
                    self.configuration["sbcoin_id"])
                self.auto_approve_transfer_limit: int = (
                    self.configuration["auto_approve_transfer_limit"])
                self.aml_office_channel_id: int = (
                    self.configuration["aml_office_channel_id"])
                self.aml_office_thread_id: int = (
                    self.configuration["aml_office_thread_id"])
                self.reaction_messages_enabled: bool = (
                    self.configuration["reaction_messages_enabled"])
                self._leaderboard_holder_blocked: bool = (
                    self.configuration["leaderboard_holder_blocked"])
                self._leaderboard_slots_highest_wager_blocked: bool = (
                    self.configuration[
                        "leaderboard_slots_highest_wager_blocked"])
                self._leaderboard_slots_highest_win_blocked: bool = (
                    self.configuration[
                        "leaderboard_slots_highest_win_blocked"])
                attributes_set = True
            except KeyError as e:
                print(f"ERROR: Missing key in bot configuration: {e}\n"
                      "The bot configuration file will be replaced "
                      "with template values.")
                self.create()

        # Iterate this class' attributes
        attributes: Dict[str, Any] = self.__dict__
        for attribute in attributes:
            if not attribute in self._default_config:
                continue
            configured_value: str | int = attributes[attribute]
            default_value: str | int = cast(
                str | int, self._default_config[attribute])
            if (configured_value == default_value):
                print(f"WARNING: `{attribute}` has not been set "
                      f"in '{self.file_name}' "
                      "nor in the environment variables.")
        print(f"Bot configuration initialized.")
        
    @property
    def leaderboard_holder_blocked(self) -> bool:
        """
        Gets the _leaderboard_holder_blocked attribute.
        This property is used to check if the leaderboard for holder
        is blocked or not.
        Returns:
            bool: True if the leaderboard is blocked, False otherwise.
        """
        return self._leaderboard_holder_blocked

    @leaderboard_holder_blocked.setter
    def leaderboard_holder_blocked(self, value: bool) -> None:
        """
        Sets the _leaderboard_holder_blocked attribute.
        Args:
            value (bool): True if the leaderboard is blocked, False otherwise.
        """
        self._leaderboard_holder_blocked: bool = value
        self.configuration["leaderboard_holder_blocked"] = value
        with open(self.file_name, "w", encoding="utf-8") as file:
            file.write(json.dumps(self.configuration, indent=4))
    
    @property
    def leaderboard_slots_highest_win_blocked(self) -> bool:
        """
        Gets the _leaderboard_slots_highest_win_blocked attribute.
        """
        return self._leaderboard_slots_highest_win_blocked

    @leaderboard_slots_highest_win_blocked.setter
    def leaderboard_slots_highest_win_blocked(self, value: bool) -> None:
        """
        Sets the _leaderboard_slots_highest_win_blocked attribute.
        """
        self._leaderboard_slots_highest_win_blocked: bool = value
        self.configuration["leaderboard_slots_highest_win_blocked"] = value
        with open(self.file_name, "w", encoding="utf-8") as file:
            file.write(json.dumps(self.configuration, indent=4))

    @property
    def leaderboard_slots_highest_wager_blocked(self) -> bool:
        """
        Gets the leaderboard_slots_highest_wager_blocked attribute.
        """
        return self._leaderboard_slots_highest_wager_blocked
    
    @leaderboard_slots_highest_wager_blocked.setter
    def leaderboard_slots_highest_wager_blocked(self, value: bool) -> None:
        """
        Sets the leaderboard_slots_highest_wager_blocked attribute.
        """
        self._leaderboard_slots_highest_wager_blocked: bool = value
        self.configuration["leaderboard_slots_highest_wager_blocked"] = value
        with open(self.file_name, "w", encoding="utf-8") as file:
            file.write(json.dumps(self.configuration, indent=4))

    def create(self) -> None:
        """
        Creates the necessary directories and a default configuration file.
        This method performs the following actions:
        1. Creates any missing directories specified in the file path.
        2. Creates a configuration file with default settings if it does not
            already exist.
        The default configuration includes:
        - coin: Default coin name in lowercase.
        - Coin: Default coin name with the first letter capitalized.
        - coins: Plural form of the default coin name in lowercase.
        - Coins: Plural form of the default coin name with the first
                    letter capitalized.
        - coin_emoji_id: Placeholder for the emoji ID of the coin.
        - casino_house_id: Placeholder for the ID of the casino house.
        - bot_maintainer_id: Placeholder for the ID of the bot maintainer.
        Raises:
            OSError: If there is an error creating directories or writing
                        the configuration file.
        """
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        for directory in directories.split("/"):
            if not exists(directory):
                makedirs(directory)

        # Create the configuration file
        # Default configuration
        configuration: BotConfig = self._default_config
        # Save the configuration to the file
        with open(self.file_name, "w", encoding="utf-8") as file:
            file.write(json.dumps(configuration, indent=4))

    def read(self) -> BotConfig:
        """
        Reads the bot configuration from a file and overrides it with
        environment variables if they exist.
        If the configuration file does not exist, it creates a new one.
        Returns:
            The bot configuration dictionary with possible overrides
                from environment variables.
        """
        file_exists: bool = exists(self.file_name)
        file_is_empty: bool = file_exists and (
            stat(self.file_name).st_size == 0)
        if file_is_empty or not file_exists:
            print(f"WARNING: '{self.file_name}' is empty or does not exist. "
                  "Creating a new configuration file with default values.")
            self.create()
            return self._default_config

        with open(self.file_name, "r", encoding="utf-8") as file:
            configuration: BotConfig = json.loads(file.read())
            # Override the configuration with environment variables
            # TODO Add reels env vars
            # BUG: Environment variable names are be case-insensitive on Windows
            for config_key in configuration:
                env_value: str | None = os_environ.get(config_key)
                if env_value:
                    if isinstance(configuration[config_key], int):
                        configuration[config_key] = int(env_value)
                    else:
                        configuration[config_key] = env_value
                    print(f"NOTE: {config_key} overridden by "
                          f"environment variable to {env_value}.")
            return configuration


def invoke_bot_configuration() -> None:
    """
    Updates the global config variables.
    This is necessary because I need to be able to update the config with
    a slash command.
    """
    print("Loading bot configuration...")
    g.configuration = BotConfiguration()
    g.coin = g.configuration.coin
    g.Coin = g.configuration.Coin
    g.coins = g.configuration.coins
    g.Coins = g.configuration.Coins
    g.coin_emoji_id = g.configuration.coin_emoji_id
    g.coin_emoji_name = g.configuration.coin_emoji_name
    g.casino_house_id = g.configuration.casino_house_id
    g.bot_maintainer_id = g.configuration.bot_maintainer_id
    g.casino_channel_id = g.configuration.casino_channel_id
    g.mining_updates_channel_id = g.configuration.mining_updates_channel_id
    g.mining_updates_channel_name = g.configuration.mining_updates_channel_name
    g.mining_highlights_channel_id = g.configuration.mining_highlights_channel_id
    g.mining_highlights_channel_name = (
        g.configuration.mining_highlights_channel_name)
    g.blockchain_name = g.configuration.blockchain_name
    g.Blockchain_name = g.configuration.Blockchain_name
    g.network_mining_enabled = g.configuration.network_mining_enabled
    g.grifter_swap_id = g.configuration.grifter_swap_id
    g.sbcoin_id = g.configuration.sbcoin_id
    g.auto_approve_transfer_limit = (
        g.configuration.auto_approve_transfer_limit)
    g.aml_office_channel_id = g.configuration.aml_office_channel_id
    g.aml_office_thread_id = (
        g.configuration.aml_office_thread_id)
    g.reaction_messages_enabled = g.configuration.reaction_messages_enabled
    g.leaderboard_holder_blocked = g.configuration.leaderboard_holder_blocked
    g.leaderboard_slots_highest_win_blocked = (
        g.configuration.leaderboard_slots_highest_win_blocked)
    g.leaderboard_slots_highest_wager_blocked = (
        g.configuration.leaderboard_slots_highest_wager_blocked)
    print("Bot configuration loaded.")
