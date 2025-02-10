# region Imports
import sb_blockchain
import threading
import subprocess
import signal
import asyncio
import json
import pytz
import random
import math
from time import sleep, time
from datetime import datetime
from discord import (Guild, Intents, Interaction, Member, Message, Client,
                     Emoji, PartialEmoji, Role, User, TextChannel, app_commands,
                     utils)
from discord.ui import View, Button
from discord.ext import commands
from discord.raw_models import RawReactionActionEvent
from os import environ as os_environ, getenv, makedirs
from os.path import exists
from dotenv import load_dotenv
from hashlib import sha256
from sys import exit as sys_exit
from sympy import (symbols, Expr, Add, Mul, Float, Integer, Rational, simplify,
                   Piecewise, pretty, Eq, Lt, Ge)
from _collections_abc import dict_items
from typing import (
    Dict, KeysView, List, LiteralString, NoReturn, TextIO, cast, NamedTuple,
    Literal, Any, TypedDict)
# endregion

# region Type aliases

class BotConfig(TypedDict):
    coin: str
    Coin: str
    coins: str
    Coins: str
    COIN_EMOJI_ID: str
    CASINO_HOUSE_ID: str
    ADMINISTRATOR_ID: str

class Reels(TypedDict):
    reel1: dict[str, int]
    reel2: dict[str, int]
    reel3: dict[str, int]

class Event(TypedDict):
    emoji_name: str
    emoji_id: int
    fixed_amount: int
    wager_multiplier: float
    
class SlotMachineConfig(TypedDict):
    events: dict[str, Event]
    reels: Reels
    fees: dict[str, int | float]
    jackpot_amount: int

# endregion

# region Named tuple


class StartingBonusMessage(NamedTuple):
    message_id: int
    invoker_id: int
    invoker_name: str
# endregion


# Intents and bot setup
intents: Intents = Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot("!", intents=intents)
client = Client(intents=intents)
# Load .env file for the bot DISCORD_TOKEN
load_dotenv()
DISCORD_TOKEN: str | None = getenv('DISCORD_TOKEN')
channel_checkpoint_limit: int = 3
guild_ids: List[int] = []
starting_bonus_messages_waiting: Dict[int, StartingBonusMessage] = {}
active_slot_machine_players: set[int] = set()
# endregion

# region Checkpoints


class ChannelCheckpoints:
    def __init__(self,
                 guild_name: str,
                 guild_id: int,
                 channel_name: str,
                 channel_id: int,
                 number: int = 10) -> None:
        self.number: int = number
        self.guild_name: str = guild_name
        self.guild_id: int = guild_id
        self.channel_name: str = channel_name
        self.channel_id: int = channel_id
        self.directory: str = (f"data/checkpoints/guilds/{self.guild_id}"
                               f"/channels/{self.channel_id}")
        self.file_name: str = f"{self.directory}/channel_checkpoints.json"
        self.entry_count: int = self.count_lines()
        self.last_message_ids: List[Dict[str, int]] | None = self.load()

    def count_lines(self) -> int:
        if not exists(self.file_name):
            return 0

        with open(self.file_name, "r") as file:
            count: int = sum(1 for _ in file)
            return count

    def create(self) -> None:
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        for i, directory in enumerate(directories.split("/")):
            path: str = "/".join(directories.split("/")[:i+1])
            if not exists(directory):
                makedirs(path, exist_ok=True)
            # Write the guild name and channel name to files in the id
            # directories, so that bot maintainers can identify the guilds and
            # channels
            # Channel names can change, but the IDs will not
            if directory.isdigit() and int(directory) == self.guild_id:
                name_file_name: str = f"{path}/guild_name.json"
                with open(name_file_name, "w") as file:
                    file.write(json.dumps({"guild_name": self.guild_name}))
                    pass
            elif directory.isdigit() and int(directory) == self.channel_id:
                name_file_name: str = f"{path}/channel_name.json"
                with open(name_file_name, "w") as file:
                    file.write(json.dumps({"channel_name": self.channel_name}))
                    pass

        print(f"Creating checkpoints file: '{self.file_name}'")
        with open(self.file_name, "w"):
            pass

    def save(self, message_id: int) -> None:
        if not exists(self.file_name):
            self.create()

        # print(f"Saving checkpoint: {message_id}")
        self.entry_count = self.count_lines()
        with open(self.file_name, "a") as file:
            if self.entry_count == 0:
                file.write(json.dumps({"last_message_id": message_id}))
            else:
                file.write("\n" + json.dumps({"last_message_id": message_id}))
        self.entry_count += 1

        while self.entry_count > self.number:
            self.remove_first_line()
            self.entry_count -= 1

    def remove_first_line(self) -> None:
        with open(self.file_name, "r") as file:
            lines: List[str] = file.readlines()
        with open(self.file_name, "w") as file:
            file.writelines(lines[1:])

    def load(self) -> List[Dict[str, int]] | None:
        if not exists(self.file_name):
            return None

        with open(self.file_name, "r") as file:
            checkpoints: List[Dict[str, int]] | None = []
            # print("Loading checkpoints...")
            for line in file:
                checkpoint: Dict[str, int] = (
                    {k: int(v) for k, v in json.loads(line).items()})
                # print(f"checkpoint: {checkpoint}")
                checkpoints.append(checkpoint)
                return checkpoints
# endregion

# region Log


class Log:
    '''
    The log cannot currently be verified or generated from the blockchain.
    Use a validated transactions file for verification (see
    Blockchain.validate_transactions_file()).
    The log is meant to be a local record of events.
    '''

    def __init__(self,
                 file_name: str = "data/transactions.log",
                 time_zone: str | None = None) -> None:
        self.file_name: str = file_name
        self.time_zone: str | None = time_zone
        timestamp: float = time()
        if time_zone is not None:
            self.log(f"The time zone is set to '{time_zone}'.", timestamp)
        else:
            self.log("The time zone is set to the local time zone.", timestamp)

    def create(self) -> None:
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        for _, directory in enumerate(directories.split("/")):
            if not exists(directory):
                makedirs(directory)

        # Create the log file
        with open(self.file_name, "w"):
            pass

    def log(self, line: str, timestamp: float) -> None:
        if self.time_zone is None:
            # Use local time zone
            timestamp_friendly = (
                datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"))
        else:
            # Convert Unix timestamp to datetime object
            timestamp_dt: datetime = (
                datetime.fromtimestamp(timestamp, pytz.utc))

            # Adjust for time zone
            timestamp_dt = (
                timestamp_dt.astimezone(pytz.timezone(self.time_zone)))

            # Format the timestamp
            timestamp_friendly: str = (
                timestamp_dt.strftime("%Y-%m-%d %H:%M:%S"))

        # Create the log file if it doesn't exist
        if not exists(self.file_name):
            self.create()

        with open(self.file_name, "a") as f:
            timestamped_line: str = f"{timestamp_friendly}: {line}"
            print(timestamped_line)
            f.write(f"{timestamped_line}\n")


# endregion

# region Bot config
class BotConfiguration:
    def __init__(self, file_name: str = "data/bot_configuration.json") -> None:
        self.file_name: str = file_name
        self.configuration: BotConfig = (
            self.read())
        self.coin: str = str(self.configuration["coin"])
        self.Coin: str = str(self.configuration["Coin"])
        self.coins: str = str(self.configuration["coins"])
        self.Coins: str = str(self.configuration["Coins"])
        self.coin_emoji_id: int = int(str(self.configuration["COIN_EMOJI_ID"]))
        print(f"configuration: {self.configuration}")
        if self.coin_emoji_id == 0:
            print("WARNING: COIN_EMOJI_ID has not set "
                  "in bot_configuration.json nor "
                  "in the environment variables.")
        self.administrator_id: int = int(
            str(self.configuration["ADMINISTRATOR_ID"]))
        self.casino_house_id: int = int(
            str(self.configuration["CASINO_HOUSE_ID"]))
        if self.administrator_id == 0:
            print("WARNING: ADMINISTRATOR_ID has not set "
                  "in bot_configuration.json nor "
                  "in the environment variables.")

    def create(self) -> None:
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        for directory in directories.split("/"):
            if not exists(directory):
                makedirs(directory)

        # Create the configuration file
        # Default configuration
        configuration: BotConfig = {
            "coin": "coin",
            "Coin": "Coin",
            "coins": "coins",
            "Coins": "Coins",
            "COIN_EMOJI_ID": "0",
            "CASINO_HOUSE_ID": "0",
            "ADMINISTRATOR_ID": "0"
        }
        # Save the configuration to the file
        with open(self.file_name, "w") as file:
            file.write(json.dumps(configuration))

    def read(self) -> BotConfig:
        if not exists(self.file_name):
            self.create()

        with open(self.file_name, "r") as file:
            configuration: BotConfig = (
                json.loads(file.read()))
            # Override the configuration with environment variables
            env_vars: Dict[str, str] = {
                "coin": "coin",
                "Coin": "Coin",
                "coins": "coins",
                "Coins": "Coins",
                "COIN_EMOJI_ID": "COIN_EMOJI_ID",
                "CASINO_HOUSE_ID": "CASINO_HOUSE_ID",
            }
            # TODO Add reels env vars

            for env_var, config_key in env_vars.items():
                if os_environ.get(env_var):
                    configuration[config_key] = os_environ.get(env_var, "")

            return configuration


# endregion

class SlotMachine:
    # region Slot config
    def __init__(self, file_name: str = "data/slot_machine.json") -> None:
        self.file_name: str = file_name
        self.configuration: SlotMachineConfig = (
            self.load_config())
        self._reels: Reels = self.load_reels()
        # self.emoji_ids: Dict[str, int] = cast(Dict[str, int],
        #                                       self.configuration["emoji_ids"])
        self._probabilities: Dict[str, float] = (
            self.calculate_all_probabilities())
        self._jackpot: int = self.load_jackpot()
        self._fees: dict[str, int | float] = self.configuration["fees"]

    def load_reels(self) -> Reels:
        # print("Getting reels...")
        self.configuration = self.load_config()
        reels: Reels = self.configuration["reels"]
        return reels

    @property
    def reels(self) -> Reels:
        return self._reels

    @reels.setter
    def reels(self, value: Reels) -> None:
        self._reels = value
        self.configuration["reels"] = self._reels
        self.save_config()

    @property
    def probabilities(self) -> Dict[str, float]:
        return self.calculate_all_probabilities()

    @property
    def jackpot(self) -> int:
        return self._jackpot

    @jackpot.setter
    def jackpot(self, value: int) -> None:
        self._jackpot = value
        self.configuration["jackpot_amount"] = self._jackpot
        self.save_config()

    def load_jackpot(self) -> int:
        self.configuration = self.load_config()
        events: Dict[str, Dict[str, int | float]] = cast(
            Dict[str, Dict[str, int | float]], self.configuration["events"])
        jackpot_seed: int = cast(int, events["jackpot"]["fixed_amount"])
        jackpot_size: int = cast(int, events["jackpot"]["fixed_amount"])
        if jackpot_size < jackpot_seed:
            jackpot: int = jackpot_seed
        else:
            jackpot: int = jackpot_size
        return jackpot

    def create_config(self) -> None:
        print("Creating template slot machine configuration file...")
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        makedirs(directories, exist_ok=True)

        # Create the configuration file
        # Default configuration
        # jackpot_amount will automatically be set to the jackpot event's
        # fixed_amount value if the latter is higher than the former
        configuration: SlotMachineConfig = {
                "events": {
                "lose_wager": {
                    "emoji_name": "",
                    "emoji_id": 0,
                    "emoji_id": 0,
                    "fixed_amount": 0,
                    "wager_multiplier": -1.0
                },
                "small_win": {
                    "emoji_name": "",
                    "emoji_id": 0,
                    "emoji_id": 0,
                    "fixed_amount": 3,
                    "wager_multiplier": 1.0
                },
                "medium_win": {
                    "emoji_name": "",
                    "emoji_id": 0,
                    "fixed_amount": 0,
                    "wager_multiplier": 2.0
                },
                "high_win": {
                    "emoji_name": "",
                    "emoji_id": 0,
                    "fixed_amount": 0,
                    "wager_multiplier": 3.0
                },
                "jackpot": {
                    "emoji_name": "",
                    "emoji_id": 0,
                    "emoji_id": 0,
                    "fixed_amount": 100,
                    "wager_multiplier": 1.0
                }
            },
            "reels": {
                "reel1": {
                    "lose_wager": 2,
                    "small_win": 8,
                    "medium_win": 6,
                    "high_win": 3,
                    "jackpot": 1
                },
                "reel2": {
                    "lose_wager": 2,
                    "small_win": 8,
                    "medium_win": 6,
                    "high_win": 3,
                    "jackpot": 1
                },
                "reel3": {
                    "lose_wager": 2,
                    "small_win": 8,
                    "medium_win": 6,
                    "high_win": 3,
                    "jackpot": 1
                },
            },
            "fees": {
                "low_wager_main": 1,
                "medium_wager_main": 0.19,
                "high_wager_main": 0.06,
                "low_wager_jackpot": 1,
                "medium_wager_jackpot": 0.01,
                "high_wager_jackpot": 0.01
            },
            "jackpot_amount": 101
        }
        # Save the configuration to the file
        with open(self.file_name, "w") as file:
            file.write(json.dumps(configuration))
        print("Template slot machine configuration file created.")

    def load_config(self) -> SlotMachineConfig:
        if not exists(self.file_name):
            self.create_config()

        with open(self.file_name, "r") as file:
            configuration: SlotMachineConfig = json.loads(file.read())
            return configuration

    def save_config(self) -> None:
        # print("Saving slot machine configuration...")
        with open(self.file_name, "w") as file:
            file.write(json.dumps(self.configuration))
        # print("Slot machine configuration saved.")
    # endregion

    # region Slot probability

    def calculate_reel_symbol_probability(self,
                                          reel: Literal[
                                              "reel1", "reel2", "reel3"],
                                          symbol: str) -> float:
        number_of_symbol_on_reel: int = self.reels[reel][symbol]
        total_reel_symbols: int = sum(self.reels[reel].values())
        if total_reel_symbols != 0 and number_of_symbol_on_reel != 0:
            probability_for_reel: float = (
                number_of_symbol_on_reel / total_reel_symbols)
        else:
            probability_for_reel = 0.0
        return probability_for_reel

    def calculate_event_probability(self, symbol: str) -> float:
        # TODO Ensure it's still working properly
        overall_probability: float = 1.0
        for r in self.reels:
            r = (
                cast(Literal['reel1', 'reel2', 'reel3'], r))
            probability_for_reel: float = (
                self.calculate_reel_symbol_probability(r, symbol))
            overall_probability *= probability_for_reel
        return overall_probability

    def calculate_losing_probabilities(self) -> tuple[float, float]:
        # TODO Ensure it's still working properly
        # print("Calculating chance of losing...")

        # No symbols match
        standard_lose_probability: float = 1.0

        # Either lose_wager symbols match or no symbols match
        any_lose_probability: float = 1.0

        # Take the symbols from the first reel
        # (expecting all reels to have the same symbols)
        symbols: List[str] = [symbol for symbol in self.reels["reel1"]]
        for symbol in symbols:
            symbols_match_probability: float = (
                self.calculate_event_probability(symbol))
            symbols_no_match_probability: float = 1 - symbols_match_probability
            standard_lose_probability *= symbols_no_match_probability
            if symbol != "lose_wager":
                any_lose_probability *= symbols_no_match_probability
        return (any_lose_probability, standard_lose_probability)

    def calculate_all_probabilities(self) -> Dict[str, float]:
        # TODO Ensure it's still working properly
        self.reels = self.load_reels()
        probabilities: Dict[str, float] = {}
        for symbol in self.reels["reel1"]:
            probability: float = self.calculate_event_probability(symbol)
            probabilities[symbol] = probability
        any_lose_probability: float
        standard_lose_probability: float
        any_lose_probability, standard_lose_probability = (
            self.calculate_losing_probabilities())
        probabilities["standard_lose"] = standard_lose_probability
        probabilities["any_lose"] = any_lose_probability
        probabilities["win"] = 1 - any_lose_probability
        return probabilities
    # endregion

    # region Slot count
    def count_symbols(self, reel: str | None = None) -> int:
        # TODO Ensure it's still working properly
        symbol_count: int
        all_symbols_lists: List[int] = []
        if reel is None:
            for r in self._reels:
                r = (
                    cast(Literal['reel1', 'reel2', 'reel3'], r))
                all_symbols_lists.append(sum(self._reels[r].values()))
            symbol_count = sum(all_symbols_lists)
        else:
            r = (
                cast(Literal['reel1', 'reel2', 'reel3'], reel))
            all_symbols_lists.append(sum(self._reels[r].values()))
        symbol_count = sum(all_symbols_lists)
        return symbol_count
    # endregion

    # region Slot EV
    def calculate_ev(self,
                     silent: bool = False) -> tuple[Piecewise, Piecewise]:
        """Calculate the expected total return and expected return for the slot
        machine.
        
        The player can only decide how many coins to insert into the machine
        each spin, and the fees are subtracted automatically from the player's
        total return (the amount of money they get back).

        Each spin, the player pays two fees (or four, if you count the
        fixed amount and multiplier fees separately), the main fee and the
        jackpot fee.
        If the player gets a combo that multiplies their wager, it multiplies
        their wager, not their wager minus the fees.
        The jackpot fee is money that goes directly to the jackpot pool.
        If a player's wager does not cover the jackpot fee, they get the
        "no jackpot" mode, where they are not eligible for the jackpot. In the
        event that they get the jackpot combo, they don't get the jackpot, it
        just counts as a standard lose (no combo).

        Different wager sizes have different fees,
        which makes the EV different for different wager sizes
        Therefore, we express EV as a piecewise function
        Each piece expresses the EV (ETR or ER) for a specific wager range

        Terms:
        - Expected value (EV): The average value of a random variable over
            many trials
        - Wager (or stake): The amount of coins the player inserts into the
            machine each spin; a number that decides the fee and that the
            multiplier events are based on
        - Total return (TR): The gross return amount that the player gets back
            (this in itself does not tell us if the player made a profit or
            loss)
        - Return (R): The net amount that the player gets back; the gain or loss
            part of the total return money; the total return minus the wager 
        - Expected total return (ETR): The average total return over many plays; 
            the expected value of the total return
        - Expected return (ER): The average return (gain or loss) over many
            plays; the expected value of the return
        - Piecewise function: A function that is defined by several subfunctions
            (used here to express ETR and ER with different fees for different
            wager ranges)

        Symbolic representation:
        - W: Wager
        - k: Wager multiplier
        - x: Fixed amount payout
        - f1k: Main fee wager multiplier
        - f1x: Main fee fixed amount
        - f2k: Jackpot fee wager multiplier
        - f2x: Jackpot fee fixed amount
        - j: Jackpot average

        Parameters:
        - silent: If True, the function will not print anything to the console
        - standard_fee_fixed_amount: A fixed amount that is subtracted from the
            player's total return for each spin
        - standard_fee_wager_multiplier: A percentage of the player's wager that
            is subtracted from the player's total return for each spin, and
            added to the jackpot pool
        - jackpot_fee_fixed_amount: A fixed amount that is subtracted from the
            player's total return for each spin, and added to the jackpot pool
        """

        def print_if_not_silent(*args: Any, **kwargs: Any) -> None:
            """Wrapper for print() that only prints if the "silent" parameter is
            False.
            """
            if not silent:
                print(*args, **kwargs)

        # Load configuration and calculate probabilities
        self.configuration = self.load_config()
        probabilities: Dict[str, float] = self.calculate_all_probabilities()
        events: KeysView[str] = probabilities.keys()
        combo_events: Dict[str, Dict[str, int | float]] = cast(
            Dict[str, Dict[str, int | float]], self.configuration["events"])
        
        # Symbol
        W: Expr = symbols('W')  # wager
        
        def calculate_piece_ev(
                standard_fee_fixed_amount: Integer = Integer(0),
                standard_fee_wager_multiplier: Float = Float(0.0),
                jackpot_fee_fixed_amount: Integer = Integer(0),
                jackpot_fee_wager_multiplier: Float = Float(0.0)
                ) -> tuple[Add, Add]:
            """ Calculate the *expected total return* and *expected return*
            with the fees specified with the parameters.
            """
            # Initialize variables
            piece_expected_return: Integer | Add = (
                Integer(0))
            piece_expected_total_return: Integer | Add = (
                Integer(0))
            piece_expected_total_return_contribution: Integer | Mul = (
                Integer(0))
            piece_expected_return_contribution: Integer | Mul = (
                Integer(0))
            p_event_float: float
            fixed_amount_int: int = 0
            fixed_amount: Expr = Integer(fixed_amount_int)
            wager_multiplier_float: float
            wager_multiplier: Expr

            # Mark the start
            print_if_not_silent("--------------------------------")
            
            # Print the fees
            print_if_not_silent(f"standard_fee_fixed_amount: "
                                f"{standard_fee_fixed_amount}")
            print_if_not_silent(f"standard_fee_wager_multiplier: "
                                f"{standard_fee_wager_multiplier}")
            print_if_not_silent(f"jackpot_fee_fixed_amount: "
                                f"{jackpot_fee_fixed_amount}")
            print_if_not_silent(f"jackpot_fee_wager_multiplier: "
                                f"{jackpot_fee_wager_multiplier}")
            
            # Determine if it's "no jackpot" mode (jackpot fee not paid)
            no_jackpot_mode: bool = False
            if (Eq(jackpot_fee_fixed_amount, Integer(0)) and
                Eq(jackpot_fee_wager_multiplier, Float(0.0))):
                no_jackpot_mode = True
                print_if_not_silent(f"no_jackpot_mode: {no_jackpot_mode}")

            for event in events:
                if event in ("any_lose", "win"):
                    continue
                print_if_not_silent(f"----\nEVENT: {event}")
                # Get the probability of this event
                p_event_float: float = probabilities[event]
                p_event = Float(p_event_float)
                print_if_not_silent(f"Event probability: {p_event_float}")
                if p_event_float == 0.0:
                    continue
                if event == "jackpot" and not no_jackpot_mode:
                    # If the player pays the coin jackpot fee
                    # and wins the jackpot,
                    # he ends up with his wager minus the standard fee minus the
                    # jackpot fee, plus the jackpot
                    #
                    # Variables
                    fixed_amount_int = cast(int,
                                            combo_events[event]["fixed_amount"])
                    jackpot_seed: int = fixed_amount_int
                    print_if_not_silent(f"Jackpot seed: {jackpot_seed}")
                    jackpot_average: float = (
                        self.calculate_average_jackpot(
                            seed=jackpot_seed))
                    # TODO Add parameter to return RTP with jackpot excluded
                    # jackpot_average: float = 0.0
                    print_if_not_silent(f"Jackpot average: {jackpot_average}")
                    # I expect wager multiplier to be 1.0 for the jackpot,
                    # but let's include it in the calculation anyway,
                    # in case someone wants to use a different value
                    wager_multiplier_float = (
                        combo_events[event]["wager_multiplier"])
                    wager_multiplier = Float(wager_multiplier_float)

                    # Calculations
                    event_total_return = Add(
                        Mul(W, wager_multiplier),
                        jackpot_average,
                        -Mul(W, standard_fee_wager_multiplier),
                        -Mul(W, jackpot_fee_wager_multiplier),
                        -standard_fee_fixed_amount,
                        -jackpot_fee_fixed_amount)
                    print_if_not_silent(f"Event total return: "
                                        f"{event_total_return} "
                                        "["
                                        "(W * k) + j "
                                        "- (W * f1k) - (W * f2k) "
                                        "- f1x - f2x"
                                        "]")
                    event_return = Add(
                        event_total_return,
                        -W)
                    # This event's contributions to the *expected total return*
                    piece_expected_total_return_contribution = (
                        Mul(p_event, event_total_return))
                    message: str
                    message = ("Expected total return contribution: "
                            f"{piece_expected_total_return_contribution}")
                    print_if_not_silent(message)
                    # Remove variables with common names to prevent accidental use
                    del message
                    # This event's contribution to the *expected return*
                    piece_expected_return_contribution = (
                        Mul(p_event, event_return))
                    print_if_not_silent(f"Event return: "
                                        f"{event_return} "
                                        "[total return - W]")
                    # Add the contributions to the totals
                    piece_expected_total_return = Add(
                        piece_expected_total_return,
                        piece_expected_total_return_contribution)
                    piece_expected_return = Add(
                        piece_expected_return,
                        piece_expected_return_contribution)
                    continue
                elif ((event == "standard_lose") or
                      (event == "jackpot" and no_jackpot_mode)):
                    # If the player doesn't pay the jackpot fee and
                    # loses or gets the jackpot combo
                    # he ends up with his wager minus the standard fee
                    wager_multiplier_float = 1.0
                    fixed_amount_int = 0
                else:
                    # "else" includes all remaining win events
                    # plus the lose_wager event
                    #
                    # Variables
                    fixed_amount_int = (
                        cast(int, combo_events[event]["fixed_amount"]))
                    wager_multiplier_float = (
                        combo_events[event]["wager_multiplier"])
                wager_multiplier = Float(wager_multiplier_float)
                print_if_not_silent(f"Multiplier (k): {
                                    wager_multiplier_float}")
                fixed_amount = Integer(fixed_amount_int)
                print_if_not_silent(f"Fixed amount (x): {fixed_amount_int}")

                # Calculations
                event_total_return = Add(
                    Mul(W, wager_multiplier),
                    fixed_amount,
                    -Mul(W, standard_fee_wager_multiplier),
                    -Mul(W, jackpot_fee_wager_multiplier),
                    -standard_fee_fixed_amount,
                    -jackpot_fee_fixed_amount)
                print_if_not_silent(f"Event total return: "
                                    f"{event_total_return} "
                                    "["
                                    "(W * k) + x "
                                    "- (W * f1k) - (W * f2k) "
                                    "- f1x - f2x"
                                    "]")
                event_return = Add(event_total_return, -W)
                print_if_not_silent(f"Event return: "
                                    f"{event_return} "
                                    "[total return - W]")
                piece_expected_total_return_contribution = (
                    Mul(p_event, event_total_return))
                message = ("Expected total return contribution: "
                        f"{piece_expected_total_return_contribution}")
                print_if_not_silent(message)
                del message
                piece_expected_return_contribution = (
                    Mul(p_event, event_return))
                print_if_not_silent("Expected return contribution: "
                                    f"{piece_expected_return_contribution}")
                # Add the event's contributions to the final expected returns
                piece_expected_total_return = Add(
                    piece_expected_total_return,
                    piece_expected_total_return_contribution)
                piece_expected_return = Add(
                    piece_expected_return,
                    piece_expected_return_contribution)
            return (
                cast(Add, piece_expected_total_return),
                cast(Add, piece_expected_return))
        
        # BUG The rounding to nearest integer (for the fees esp.) is not accounted for

        # Fees
        # Refresh config
        self.configuration = self.load_config()
        # Main fee
        low_wager_main_fee: Integer = Integer(self._fees["low_wager_main"])
        medium_wager_main_fee: Float = Float(self._fees["medium_wager_main"])
        high_wager_main_fee: Float = Float(self._fees["high_wager_main"])
        # Jackpot fee
        low_wager_jackpot_fee: Integer = Integer(
            self._fees["low_wager_jackpot"])
        medium_wager_jackpot_fee: Float = Float(
            self._fees["medium_wager_jackpot"])
        high_wager_jackpot_fee: Float = Float(
            self._fees["high_wager_jackpot"])
        
        # TODO Send expected return for different wager sizes with /reels
        # Calculate expected total return and expected return
        # with different fees
        pieces: Dict[str, tuple[Add, Add]] = {
            "no_jackpot": calculate_piece_ev(
            standard_fee_fixed_amount=low_wager_main_fee),
            "low_wager": calculate_piece_ev(
            standard_fee_fixed_amount=low_wager_main_fee,
            jackpot_fee_fixed_amount=low_wager_jackpot_fee),
            "medium_wager": calculate_piece_ev(
            standard_fee_wager_multiplier=medium_wager_main_fee,
            jackpot_fee_wager_multiplier=medium_wager_jackpot_fee),
            "high_wager": calculate_piece_ev(
            standard_fee_wager_multiplier=high_wager_main_fee,
            jackpot_fee_wager_multiplier=high_wager_jackpot_fee)
        }

        expected_total_return = Piecewise(
            (pieces["no_jackpot"][0], Eq(W, Integer(1))),
            (pieces["low_wager"][0], Lt(W, Integer(10))),
            (pieces["medium_wager"][0], Lt(W, Integer(100))),
            (pieces["high_wager"][0], Ge(W, Integer(100))))
        
        expected_return = Piecewise(
            (pieces["no_jackpot"][1], Eq(W, Integer(1))),
            (pieces["low_wager"][1], Lt(W, Integer(10))),
            (pieces["medium_wager"][1], Lt(W, Integer(100))),
            (pieces["high_wager"][1], Ge(W, Integer(100))))
        
        print_if_not_silent(f"Expected total return:")
        print_if_not_silent(expected_total_return)
        print_if_not_silent(f"Expected return:")
        print_if_not_silent(expected_return)

        return (expected_total_return, expected_return)
    # endregion

    # region Slot avg jackpot
    def calculate_average_jackpot(self, seed: int) -> float:
        # 1 coin is added to the jackpot for every spin
        contribution_per_spin: int = 1
        probabilities: Dict[str, float] = self.calculate_all_probabilities()
        average_spins_to_win: float = 1 / probabilities["jackpot"]
        jackpot_cycle_growth: float = (
            contribution_per_spin * average_spins_to_win)
        # min + max / 2
        mean_jackpot: float = (0 + jackpot_cycle_growth) / 2
        average_jackpot: float = seed + mean_jackpot
        return average_jackpot
    # endregion

    # region Slot RTP
    def calculate_rtp(self, wager: Integer) -> Float:
        # IMPROVE Fix error reported by Pylance
        expected_total_return_expression: Piecewise = (
            self.calculate_ev(silent=True))[0]
        expected_total_return: Piecewise = (cast(Piecewise,
            expected_total_return_expression.subs(symbols('W'), wager)))
        print(f"Expected total return (W = {wager}): {expected_total_return}")
        rtp = Rational(expected_total_return, wager)
        rtp_decimal: Float = cast(Float, rtp.evalf())
        print(f"RTP: {rtp}")
        print(f"RTP decimal: {rtp_decimal}")
        return rtp_decimal
    # endregion

    # region Slot stop reel
    # def pull_lever(self):
    #     symbols_landed = []
    #     for reel in self.reels:
    #         symbol = self.stop_reel(reel)
    #         symbols_landed.append(symbol)
    #     return symbols_landed

    def stop_reel(self, reel: Literal["reel1", "reel2", "reel3"]) -> str:
        # Create a list with all units of each symbol type on the reel
        reel_symbols: List[str] = []
        for s in self.reels[reel]:
            reel_symbols.extend([s] * self.reels[reel][s])
        # Randomly select a symbol from the list
        symbol: str = random.choice(reel_symbols)
        return symbol

    # endregion

    # region Slot money
    def calculate_award_money(self,
                              wager: int,
                              results: (
                                  Dict[str, Dict[
                                      str,
                                      str | int | float | PartialEmoji]])
                              ) -> tuple[str, str, int]:

        if (not (
            results["reel1"]["name"] == results["reel2"]["name"] == results["reel3"]["name"]
        )):
            return ("standard_lose", "No win", 0)

        low_wager_standard_fee = 1
        low_wager_jackpot_fee = 1
        jackpot_fee_paid: bool = (
            wager >= (low_wager_jackpot_fee + low_wager_standard_fee))
        no_jackpot_mode: bool = False if jackpot_fee_paid else True
        event_name: str = cast(str, results["reel1"]["name"])
        # print(f"event_name: {event_name}")
        wager_multiplier: float = cast(float, results["reel1"]["wager_multiplier"])
        fixed_amount_payout: int = cast(int, results["reel1"]["fixed_amount"])
        # print(f"event_multiplier: {wager_multiplier}")
        # print(f"fixed_amount_payout: {fixed_amount_payout}")
        event_name_friendly: str = ""
        win_money: float = 0.0
        win_money_rounded: int = 0
        if event_name == "lose_wager":
            event_name_friendly = "Lose wager"
            return (event_name, event_name_friendly, 0)
        elif event_name == "jackpot":
            if no_jackpot_mode:
                event_name = "jackpot_fail"
                event_name_friendly = "No Jackpot"
                win_money_rounded = 0
            else:
                event_name_friendly = "JACKPOT"
                win_money_rounded = self.jackpot
            return (event_name, event_name_friendly, win_money_rounded)
        win_money = (
            (wager * wager_multiplier) + fixed_amount_payout) - wager
        win_money_rounded: int = math.floor(win_money)
        # Get rid of ".0"
        event_multiplier_friendly: str
        event_multiplier_floored: int = math.floor(wager_multiplier)
        if wager_multiplier == event_multiplier_floored:
            event_multiplier_friendly = str(int(wager_multiplier))
        else:
            event_multiplier_friendly = str(wager_multiplier)
        event_name_friendly += "{}X".format(event_multiplier_friendly)
        if fixed_amount_payout > 0:
            event_name_friendly = "+{}".format(fixed_amount_payout)
        return (event_name, event_name_friendly, win_money_rounded)
    # endregion

# region UserSaveData


class UserSaveData:
    def __init__(self, user_id: int, user_name: str) -> None:
        self.user_id: int = user_id
        self.user_name: str = user_name
        self.file_name: str = f"data/save_data/{user_id}.json"
        self.starting_bonus_received: bool = False

    def create(self) -> None:
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        for i, directory in enumerate(directories.split("/")):
            path: str = "/".join(directories.split("/")[:i+1])
            if not exists(directory):
                makedirs(path, exist_ok=True)
            if directory.isdigit() and int(directory) == self.user_id:
                name_file_name: str = f"{path}/user_name.json"
                with open(name_file_name, "w") as file:
                    file.write(json.dumps(
                        {"user_name": self.user_name,
                         "user_id": self.user_id,
                         "starting_bonus_received": (
                             self.starting_bonus_received)
                         }))
                    pass

        # Create the save data file
        with open(self.file_name, "w"):
            pass

    def save(self, key: str, value: str) -> None:
        if not exists(self.file_name):
            self.create()

        with open(self.file_name, "w") as f:
            f.write(json.dumps({key: value}))

    def load(self, key: str) -> str | None:
        if not exists(self.file_name):
            return None

        all_data: Dict[str, str] = {}
        with open(self.file_name, "r") as file:
            for line in file:
                data: Dict[str, str] = json.loads(line)
                all_data.update(data)
            return all_data[key]
# endregion

# region Bonus die button


class StartingBonusView(View):
    def __init__(self,
                 invoker: User | Member,
                 starting_bonus_awards: Dict[int, int],
                 save_data: UserSaveData,
                 log: Log,
                 interaction: Interaction) -> None:
        super().__init__(timeout=30)
        self.invoker: User | Member = invoker
        self.invoker_id: int = invoker.id
        self.starting_bonus_awards: Dict[int, int] = starting_bonus_awards
        self.save_data: UserSaveData = save_data
        self.log: Log = log
        self.interaction: Interaction = interaction
        self.button_clicked: bool = False
        self.die_button: Button[View] = Button(
            disabled=False,
            emoji="🎲",
            custom_id="starting_bonus_die")
        self.die_button.callback = self.on_button_click
        self.add_item(self.die_button)

    async def on_button_click(self, interaction: Interaction) -> None:
        clicker_id: int = interaction.user.id
        if clicker_id != self.invoker_id:
            await interaction.response.send_message(
                "You cannot role the die for someone else!", ephemeral=True)
        else:
            self.button_clicked = True
            self.die_button.disabled = True
            await interaction.response.edit_message(
                view=self)

            die_roll: int = random.randint(1, 6)
            starting_bonus: int = self.starting_bonus_awards[die_roll]
            message: str = (
                f"You rolled a {die_roll} and won {starting_bonus} {coins}!\n"
                "You may now play on the slot machines. Good luck!")
            await interaction.followup.send(message)
            del message
            await add_block_transaction(
                blockchain=blockchain,
                sender=CASINO_HOUSE_ID,
                receiver=self.invoker,
                amount=starting_bonus,
                method="starting_bonus"
            )
            self.save_data.save("starting_bonus_received", "True")
            last_block_timestamp: float | None = get_last_block_timestamp()
            if last_block_timestamp is None:
                print("ERROR: Could not get last block timestamp.")
                await terminate_bot()
            log.log(
                line=(f"{self.invoker} ({self.invoker_id}) won "
                      f"{starting_bonus} {coins} from the starting bonus."),
                timestamp=last_block_timestamp)
            del last_block_timestamp
            self.stop()

    async def on_timeout(self) -> None:
        self.die_button.disabled = True
        message = ("You took too long to roll the die. When you're "
                   "ready, you may run the command again.")
        await self.interaction.edit_original_response(content=message,
                                                      view=self)
        del message
# endregion

# region Slots buttons


class SlotMachineView(View):
    def __init__(self,
                 invoker: User | Member,
                 slot_machine: SlotMachine,
                 wager: int,
                 fees: int,
                 interaction: Interaction) -> None:
        super().__init__(timeout=20)
        self.current_reel_number: int = 1
        self.reels_stopped: int = 0
        self.invoker: User | Member = invoker
        self.invoker_id: int = invoker.id
        self.slot_machine: SlotMachine = slot_machine
        self.wager: int = wager
        self.fees: int = fees
        # TODO Move message variables to global scope
        self.empty_space: LiteralString = "\N{HANGUL FILLER}" * 11
        self.message_header: str = f"### {Coin} Slot Machine\n"
        self.message_reel_status: str = "The reels are spinning..."
        self.message_collect_screen: str = (f"-# Coin: {self.wager}\n"
                                            f"-# Fee: {self.fees}\n"
                                            f"{self.empty_space}")
        self.message_results_row: str = f"🔳\t\t🔳\t\t🔳"
        self.message: str = (f"{self.message_header}\n"
                             f"{self.message_collect_screen}\n"
                             f"{self.message_reel_status}\n"
                             "\n"
                             f"{self.empty_space}")
        self.events: (
            Dict[str, Dict[str, int | float]]) = cast(
                Dict[str, Dict[str, int | float]],
            self.slot_machine.configuration["events"])
        self.interaction: Interaction = interaction
        blank_emoji: PartialEmoji = PartialEmoji.from_str("🔳")
        self.reels_results: Dict[
            str,
            Dict[str, str | int | float | PartialEmoji]]
        self.reels_results = (
            {
                "reel1":
                {"emoji": blank_emoji},

                "reel2":
                {"emoji": blank_emoji},

                "reel3":
                {"emoji": blank_emoji}
            }
        )
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
        """
        # Map button IDs to reel key names
        reel_stop_button_map: Dict[str, Literal["reel1", "reel2", "reel3"]] = {
            "stop_reel_1": "reel1",
            "stop_reel_2": "reel2",
            "stop_reel_3": "reel3"
        }
        # Pick reel based on button ID
        reel_name: Literal["reel1", "reel2", "reel3"] = reel_stop_button_map[button_id]
        # Stop the reel and get the symbol
        symbol_name: str = self.slot_machine.stop_reel(reel=reel_name)
        # Get the emoji for the symbol (using the events dictionary)
        symbol_emoji_name: str = cast(str,
                                      self.events[symbol_name]["emoji_name"])
        symbol_emoji_id: int = cast(int,
                                    self.events[symbol_name]["emoji_id"])
        # Create a PartialEmoji object (for the message)
        symbol_emoji: PartialEmoji = PartialEmoji(name=symbol_emoji_name,
                                                  id=symbol_emoji_id)
        # Copy keys and values from the appropriate sub-dictionary in events
        symbol_properties: Dict[str, str | int | float | PartialEmoji]
        symbol_properties = {**self.events[symbol_name]}
        symbol_properties["name"] = symbol_name
        symbol_properties["emoji"] = symbol_emoji
        # Add the emoji to the result
        self.reels_results[reel_name] = symbol_properties
        self.reels_stopped += 1
        reel_status: str = (
            "The reels are spinning..." if self.reels_stopped < 3 else
            "The reels have stopped.")
        empty_space: LiteralString = "\N{HANGUL FILLER}" * 11
        self.message_reel_status = reel_status
        self.message_results_row: str = (
            f"{self.reels_results['reel1']['emoji']}\t\t"
            f"{self.reels_results['reel2']['emoji']}\t\t"
            f"{self.reels_results['reel3']['emoji']}")
        self.message = (f"{self.message_header}\n"
                        f"{self.message_collect_screen}\n"
                        f"{reel_status}\n"
                        f"{self.empty_space}\n"
                        f"{self.message_results_row}\n"
                        f"{empty_space}")

    # stop_button_callback
    async def on_button_click(self,
                              interaction: Interaction,
                              button_id: str) -> None:
        """
        Events to occur when a stop reel button is clicked.
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
            # The self.halt_reel() method updates self.message
            await self.invoke_reel_stop(button_id=button_id)
            await interaction.response.edit_message(content=self.message,
                                                    view=self)
            if self.reels_stopped == 3:
                self.stop()

    async def start_auto_stop(self) -> None:
        """
        Events to occur when the view times out.
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
                content=self.message,
                view=self)
            if self.reels_stopped < 3:
                await asyncio.sleep(1)
        # The self.halt_reel() method stops the view if
        # all reels are stopped
# endregion

# region Flask funcs


def start_flask_app_waitress() -> None:
    global waitress_process

    def stream_output(pipe: TextIO, prefix: str) -> None:
        # Receive output from the Waitress subprocess
        for line in iter(pipe.readline, ''):
            # print(f"{prefix}: {line}", end="")
            print(f"{line}", end="")
        if hasattr(pipe, 'close'):
            pipe.close()

    print("Starting Flask app with Waitress...")
    program = "waitress-serve"
    app_name = "sb_blockchain"
    host = "*"
    # Use the environment variable or default to 8000
    port: str = os_environ.get("PORT", "8080")
    command: List[str] = [
        program,
        f"--listen={host}:{port}",
        f"{app_name}:app"
    ]
    waitress_process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Flask app started with Waitress.")

    # Start threads to read output from the subprocess
    threading.Thread(
        target=stream_output,
        args=(waitress_process.stdout, "STDOUT"),
        daemon=True
    ).start()
    threading.Thread(
        target=stream_output,
        args=(waitress_process.stderr, "STDERR"),
        daemon=True
    ).start()


def start_flask_app() -> None:
    # For use with the Flask development server
    print("Starting flask app...")
    try:
        sb_blockchain.app.run(port=5000, debug=True, use_reloader=False)
    except Exception as e:
        print(f"Error running Flask app: {e}")
# endregion

# region CP start


def start_checkpoints(limit: int = 10) -> Dict[int, ChannelCheckpoints]:
    all_checkpoints: dict[int, ChannelCheckpoints] = {}
    print("Starting checkpoints...")
    channel_id: int = 0
    channel_name: str = ""
    for guild in bot.guilds:
        guild_id: int = guild.id
        guild_name: str = guild.name
        print(f"Guild: {guild_name} ({guild_id})")
        for channel in guild.text_channels:
            channel_id = channel.id
            channel_name = channel.name
            print(f"Channel: {channel_name} ({channel_id})")
            all_checkpoints[channel_id] = ChannelCheckpoints(
                guild_name=guild_name,
                guild_id=guild_id,
                channel_name=channel_name,
                channel_id=channel_id,
                number=limit
            )
    print("Checkpoints started.")
    return all_checkpoints


# region Missed msgs


async def process_missed_messages() -> None:
    '''
    Process messages that were sent since the bot was last online.
    This does not process reaction to messages older than the last checkpoint
    (i.e. older than the last message sent before the bot went offline). That
    would require keeping track of every single message and reactions on the
    server in a database.
    '''
    global all_channel_checkpoints
    missed_messages_processed_message: str = "Missed messages processed."

    print("Processing missed messages...")

    for guild in bot.guilds:
        print("Fetching messages from "
              f"guild: {guild.name} ({guild.id})...")
        for channel in guild.text_channels:
            print("Fetching messages from "
                  f"channel: {channel.name} ({channel.id})...")
            channel_checkpoints: List[Dict[str, int]] | None = (
                all_channel_checkpoints[channel.id].load())
            if channel_checkpoints is not None:
                print(f"Channel checkpoints loaded.")
            else:
                print("No checkpoints could be loaded.")
            new_channel_messages_found: int = 0
            fresh_last_message_id: int | None = None
            checkpoint_reached: bool = False
            # Fetch messages from the channel (reverse chronological order)
            async for message in channel.history(limit=None):
                message_id: int = message.id
                if new_channel_messages_found == 0:
                    # The first message found will be the last message sent
                    # This will be used as the checkpoint
                    fresh_last_message_id = message_id
                # print(f"{message.author}: {message.content} ({message_id}).")
                if channel_checkpoints is not None:
                    for checkpoint in channel_checkpoints:
                        if message_id == checkpoint["last_message_id"]:
                            print("Channel checkpoint reached.")
                            checkpoint_reached = True
                            break
                    if checkpoint_reached:
                        break
                    new_channel_messages_found += 1
                    sender: Member | User
                    receiver: User | Member
                    for reaction in message.reactions:
                        async for user in reaction.users():
                            # print(f"Reaction found: {reaction.emoji}: {user}.")
                            # print(f"Message ID: {message_id}.")
                            # print(f"{message.author}: {message.content}")
                            sender = user
                            receiver = message.author
                            emoji: PartialEmoji | Emoji | str = reaction.emoji
                            await process_reaction(emoji, sender, receiver)
            print("Messages from "
                  f"channel {channel.name} ({channel.id}) fetched.")
            if fresh_last_message_id is None:
                print("WARNING: No channel messages found.")
            else:
                if new_channel_messages_found > 0:
                    print(f"Saving checkpoint: {fresh_last_message_id}")
                    all_channel_checkpoints[channel.id].save(
                        fresh_last_message_id)
                else:
                    print("Will not save checkpoint for this channel because "
                          "no new messages were found.")
        print(f"Messages from guild {guild.id} ({guild}) fetched.")
    print(missed_messages_processed_message)
    del missed_messages_processed_message

# endregion

# region Coin reaction


async def process_reaction(emoji: PartialEmoji | Emoji | str,
                           sender: Member | User,
                           receiver: Member | User | None = None,
                           receiver_id: int | None = None) -> None:

    emoji_id: int | str | None = 0
    match emoji:
        case Emoji():
            emoji_id = emoji.id
        case PartialEmoji() if emoji.id is not None:
            emoji_id = emoji.id
        case PartialEmoji():
            return
        case str():
            return
    if emoji_id == COIN_EMOJI_ID:
        if receiver is None:
            # Get receiver from id
            if receiver_id is not None:
                receiver = await bot.fetch_user(receiver_id)
            else:
                print("ERROR: Receiver is None.")
                return
        else:
            receiver_id = receiver.id
        sender_id: int = sender.id

        if sender_id == receiver_id:
            return

        print(f"{sender} ({sender_id}) is mining 1 {coin} "
              f"for {receiver} ({receiver_id})...")
        await add_block_transaction(
            blockchain=blockchain,
            sender=sender,
            receiver=receiver,
            amount=1,
            method="reaction"
        )

        # Log the mining
        last_block_timestamp: float | None = get_last_block_timestamp()
        if last_block_timestamp is None:
            print("ERROR: Could not get last block timestamp.")
            await terminate_bot()

        try:
            mined_message: str = (f"{sender} ({sender_id}) mined 1 {coin} "
                                  f"for {receiver} ({receiver_id}).")
            log.log(line=mined_message, timestamp=last_block_timestamp)
            # Remove variables with common names to prevent accidental use
            del mined_message
            del last_block_timestamp
        except Exception as e:
            print(f"Error logging mining: {e}")
            await terminate_bot()

        chain_validity: bool | None = None
        try:
            print("Validating blockchain...")
            chain_validity = blockchain.is_chain_valid()
        except Exception as e:
            # TODO Revert blockchain to previous state
            print(f"Error validating blockchain: {e}")
            chain_validity = False

        if chain_validity is False:
            await terminate_bot()
# endregion

# region Get timestamp


def get_last_block_timestamp() -> float | None:
    last_block_timestamp: float | None = None
    try:
        # Get the last block's timestamp for logging
        last_block: None | sb_blockchain.Block = blockchain.get_last_block()
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


async def add_block_transaction(
    blockchain: sb_blockchain.Blockchain,
    sender: Member | User | int,
    receiver: Member | User | int,
    amount: int,
    method: str
) -> None:
    if isinstance(sender, int):
        sender_id = sender
    else:
        sender_id: int = sender.id
    if isinstance(receiver, int):
        receiver_id = receiver
    else:
        receiver_id: int = receiver.id
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
        data: List[Dict[str, sb_blockchain.TransactionDict]] = (
            [{"transaction": {
                "sender": sender_id_hash,
                "receiver": receiver_id_hash,
                "amount": amount,
                "method": method
            }}])
        data_casted: List[str | Dict[str, sb_blockchain.TransactionDict]] = (
            cast(List[str | Dict[str, sb_blockchain.TransactionDict]], data))
        blockchain.add_block(data=data_casted, difficulty=0)
    except Exception as e:
        print(f"Error adding transaction to blockchain: {e}")
        await terminate_bot()
    print("Transaction added to blockchain.")
# endregion

# region Terminate bot


async def terminate_bot() -> NoReturn:
    print("Closing bot...")
    await bot.close()
    print("Bot closed.")
    print("Shutting down the blockchain app...")
    waitress_process.send_signal(signal.SIGTERM)
    waitress_process.wait()
    """ print("Shutting down blockchain flask app...")
    try:
        requests.post("http://127.0.0.1:5000/shutdown")
    except Exception as e:
        print(e) """
    await asyncio.sleep(1)  # Give time for all tasks to finish
    print("The script will now exit.")
    sys_exit(1)
# endregion

# region Guild list


def load_guild_ids(file_name: str = "data/guild_ids.txt") -> List[int]:
    print("Loading guild IDs...")
    # Create missing directories
    makedirs("file_name", exist_ok=True)
    guild_ids: List[int] = []
    read_mode: str = "a+"
    if not exists(file_name):
        read_mode = "w+"
    else:
        read_mode = "r+"
    with open(file_name, read_mode) as file:
        for line in file:
            guild_id = int(line.strip())
            print(f"Adding guild ID {guild_id} from file to the list...")
            guild_ids.append(guild_id)
        for guild in bot.guilds:
            guild_id: int = guild.id
            if not guild_id in guild_ids:
                print(f"Adding guild ID {guild_id} "
                      "to the list and the file...")
                file.write(f"{guild_id}\n")
                guild_ids.append(guild_id)
    print("Guild IDs loaded.")
    return guild_ids
# endregion

# region Coin label


def generate_coin_label(number: int) -> str:
    if number == 1 or number == -1:
        return coin
    else:
        return coins
# endregion


# region Flask
if __name__ == "__main__":
    print("Starting blockchain flask app thread...")
    try:
        flask_thread = threading.Thread(target=start_flask_app_waitress)
        flask_thread.daemon = True  # Set the thread as a daemon thread
        flask_thread.start()
        print("Flask app thread started.")
    except Exception as e:
        print(f"Error starting Flask app thread: {e}")
    sleep(1)

    print(f"Initializing blockchain...")
    try:
        blockchain = sb_blockchain.Blockchain()
        print(f"Blockchain initialized.")
    except Exception as e:
        print(f"Error initializing blockchain: {e}")
        print("This script will be terminated.")
        sys_exit(1)
# endregion

# region Init
print("Starting bot...")

print("Loading bot configuration...")
configuration = BotConfiguration()
coin: str = configuration.coin
Coin: str = configuration.Coin
coins: str = configuration.coins
Coins: str = configuration.Coins
COIN_EMOJI_ID: int = configuration.coin_emoji_id
CASINO_HOUSE_ID: int = configuration.casino_house_id
ADMINISTRATOR_ID: int = configuration.administrator_id
slot_machine = SlotMachine()
print("Bot configuration loaded.")

print("Initializing log...")
log = Log(time_zone="Canada/Central")
print("Log initialized.")


@bot.event
async def on_ready() -> None:
    print("Bot started.")

    global all_channel_checkpoints
    all_channel_checkpoints = (
        start_checkpoints(limit=channel_checkpoint_limit))

    # await process_missed_messages()

    # global guild_ids
    # guild_ids = load_guild_ids()
    # print(f"Guild IDs: {guild_ids}")
    for guild in bot.guilds:
        print(f"- {guild.name} ({guild.id})")

    # Sync the commands to Discord
    print("Syncing global commands...")
    try:
        await bot.tree.sync()
        print(f"Synced commands for bot {bot.user}.")
        print(f"Bot is ready!")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# endregion


# region Message
@bot.event
async def on_message(message: Message) -> None:
    global all_channel_checkpoints
    channel_id: int = message.channel.id

    if channel_id in all_channel_checkpoints:
        all_channel_checkpoints[channel_id].save(message.id)
    else:
        # If a channel is created while the bot is running, we will likely end
        # up here.
        # Add a new instance of ChannelCheckpoints to
        # the all_channel_checkpoints dictionary for this new channel.
        guild: Guild | None = message.guild
        if guild is None:
            print("ERROR: Guild is None.")
            administrator: str = (
                (await bot.fetch_user(ADMINISTRATOR_ID)).mention)
            await message.channel.send("An error occurred. "
                                       f"{administrator} pls fix.")
            return
        guild_name: str = guild.name
        guild_id: int = guild.id
        channel = message.channel
        if isinstance(channel, TextChannel):
            channel_name: str = channel.name
            all_channel_checkpoints[channel_id] = ChannelCheckpoints(
                guild_name=guild_name,
                guild_id=guild_id,
                channel_name=channel_name,
                channel_id=channel_id
            )
        else:
            print("ERROR: Channel is not a text channel.")
            administrator: str = (
                (await bot.fetch_user(ADMINISTRATOR_ID)).mention)
            await message.channel.send("An error occurred. "
                                       f"{administrator} pls fix.")
            return

# endregion


# region Reaction
@bot.event
async def on_raw_reaction_add(payload: RawReactionActionEvent) -> None:
    # `payload` is an instance of the RawReactionActionEvent class from the
    # discord.raw_models module that contains the data of the reaction event.
    if payload.guild_id is None:
        return

    if payload.event_type == "REACTION_ADD":
        if payload.message_author_id is None:
            return

        # Look for slot machine reactions
        message_id: int = payload.message_id
        reacter_id: int = payload.user_id
        if message_id in starting_bonus_messages_waiting:
            if (payload.emoji.name == "🎲" and
                    (starting_bonus_messages_waiting[message_id].invoker_id
                     == reacter_id)):
                print("Die rolled!")
        del message_id
        del reacter_id

        # Look for coin emoji
        if payload.emoji.id is None:
            return
        sender: Member | None = payload.member
        if sender is None:
            print("ERROR: Sender is None.")
            return
        receiver_user_id: int = payload.message_author_id
        await process_reaction(emoji=payload.emoji,
                               sender=sender,
                               receiver_id=receiver_user_id)
        del receiver_user_id
        del sender
# endregion


# region /transfer
@bot.tree.command(name="transfer",
                  description=f"Transfer {coins} to another user")
@app_commands.describe(amount=f"Amount of {coins} to transfer",
                       user=f"User to transfer the {coins} to")
async def transfer(interaction: Interaction, amount: int, user: Member) -> None:
    """
    Transfer a specified amount of coins to another user.

    Args:
        interaction (Interaction): The interaction object representing the
        command invocation.
    """
    sender: User | Member = interaction.user
    sender_id: int = sender.id
    receiver: Member = user
    receiver_id: int = receiver.id
    coin_label_a: str = generate_coin_label(amount)
    print(f"User {sender_id} is requesting to transfer "
          f"{amount} {coin_label_a} to user {receiver_id}...")
    balance: int | None = None
    try:
        balance = blockchain.get_balance(user_unhashed=sender_id)
    except Exception as e:
        print(f"Error getting balance for user {sender} ({sender_id}): {e}")
        administrator: str = (await bot.fetch_user(ADMINISTRATOR_ID)).mention
        await interaction.response.send_message("Error getting balance."
                                                f"{administrator} pls fix.")
    if balance is None:
        print(f"Balance is None for user {sender} ({sender_id}).")
        await interaction.response.send_message(f"You have 0 {coins}.")
        return
    if balance < amount:
        print(f"{sender} ({sender_id}) does not have enough {coins} to "
              f"transfer {amount} {coin_label_a} to {sender} ({sender_id}). "
              f"Balance: {balance}.")
        coin_label_b: str = generate_coin_label(balance)
        await interaction.response.send_message(f"You do not have enough "
                                                f"{coins}. You have {balance} "
                                                f"{coin_label_b}.",
                                                ephemeral=True)
        del coin_label_b
        return
    del balance

    await add_block_transaction(
        blockchain=blockchain,
        sender=sender,
        receiver=receiver,
        amount=amount,
        method="transfer"
    )
    last_block: sb_blockchain.Block | None = blockchain.get_last_block()
    if last_block is None:
        print("ERROR: Last block is None.")
        administrator: str = (await bot.fetch_user(ADMINISTRATOR_ID)).mention
        await interaction.response.send_message(f"Error transferring {coins}. "
                                                f"{administrator} pls fix.")
        await terminate_bot()
    timestamp: float = last_block.timestamp
    log.log(line=f"{sender} ({sender_id}) transferred {amount} {coin_label_a} "
            f"to {receiver} ({receiver_id}).",
            timestamp=timestamp)
    await interaction.response.send_message(f"{sender} transferred "
                                            f"{amount} {coin_label_a} "
                                            f"to {receiver.mention}'s account.")
    del sender
    del sender_id
    del receiver
    del receiver_id
    del amount
    del coin_label_a
# endregion

# region /balance


@bot.tree.command(name="balance", description="Check your balance")
@app_commands.describe(user="User to check the balance")
@app_commands.describe(incognito="Do not display the balance publicly")
async def balance(interaction: Interaction,
                  user: Member | None = None,
                  incognito: bool = False) -> None:
    """
    Check the balance of a user. If no user is specified, the balance of the
    user who invoked the command is checked.

    Args:
        interaction (Interaction): The interaction object representing the
        command invocation.

        user (str, optional): The user to check the balance. Defaults to None.
    """
    user_to_check: Member | str
    if user is None:
        user_to_check = interaction.user.name
        user_id: int = interaction.user.id
    else:
        user_to_check = user.name
        user_id: int = user.id

    user_id_hash: str = sha256(str(user_id).encode()).hexdigest()
    del user_id
    balance: int | None = blockchain.get_balance(user=user_id_hash)
    if balance is None:
        await interaction.response.send_message(f"{user_to_check} has 0 "
                                                f"{coins}.",
                                                ephemeral=incognito)
    else:
        coin_label: str = generate_coin_label(balance)
        await interaction.response.send_message(f"{user_to_check} has "
                                                f"{balance} {coin_label}.",
                                                ephemeral=incognito)
        del coin_label
    del balance
# endregion
# region /reels


@bot.tree.command(name="reels",
                  description="Design the slot machine reels")
@app_commands.describe(add_symbol="Add a symbol to the reels")
@app_commands.describe(amount="Amount of symbols to add")
@app_commands.describe(remove_symbol="Remove a symbol from the reels")
@app_commands.describe(reel="The reel to modify")
@app_commands.describe(inspect="Inspect the reels")
@app_commands.describe(close_off="Close off the area so that others cannot "
                       "see the reels")
async def reels(interaction: Interaction,
                add_symbol: str | None = None,
                remove_symbol: str | None = None,
                amount: int | None = None,
                reel: str | None = None,
                close_off: bool = False,
                inspect: bool | None = None) -> None:
    """
    Design the slot machine reels by adding and removing symbols.

    Args:
        interaction (Interaction): The interaction object representing the
        command invocation.

        add_symbol (str, optional): add_symbol a symbol to the reels.
        Defaults to None.

        remove_symbol (str, optional): Remove a symbol from the reels.
        Defaults to None.
    """
    await interaction.response.defer()
    # Check if user has the necessary role
    invoker: User | Member = interaction.user
    invoker_roles: List[Role] = cast(Member, invoker).roles
    administrator_role: Role | None = (
        utils.get(invoker_roles, name="Administrator"))
    technician_role: Role | None = (
        utils.get(invoker_roles, name="Slot Machine Technician"))
    if administrator_role is None and technician_role is None:
        # TODO Maybe let other users see the reels
        message: str = ("Only slot machine technicians may look at the reels.")
        await interaction.response.send_message(message, ephemeral=True)
        del message
        return
    if amount is None:
        if reel is None:
            amount = 3
        else:
            amount = 1
    # Refresh reels config from file
    slot_machine.reels = slot_machine.load_reels()
    new_reels: Reels = slot_machine.reels
    if add_symbol and remove_symbol:
        await interaction.response.send_message("You can only add or remove a "
                                                "symbol at a time.",
                                                ephemeral=True)
        return
    if add_symbol and reel is None:
        if amount % 3 != 0:
            await interaction.response.send_message("The amount of symbols to "
                                                    "add must be a multiple "
                                                    "of 3.",
                                                    ephemeral=True)
            return
    elif add_symbol and reel:
        print(f"Adding symbol: {add_symbol}")
        print(f"Amount: {amount}")
        print(f"Reel: {reel}")
        if (reel in slot_machine.reels and
                add_symbol in slot_machine.reels[reel]):
            slot_machine.reels[reel][add_symbol] += amount
        else:
            print(f"Error: Invalid reel or symbol '{reel}' or '{add_symbol}'")
    if add_symbol:
        print(f"Adding symbol: {add_symbol}")
        print(f"Amount: {amount}")
        if add_symbol in slot_machine.reels['reel1']:
            per_reel_amount: int = int(amount / 3)
            new_reels['reel1'][add_symbol] += per_reel_amount
            new_reels['reel2'][add_symbol] += per_reel_amount
            new_reels['reel3'][add_symbol] += per_reel_amount

            slot_machine.reels = new_reels
            print(f"Added {per_reel_amount} {add_symbol} to each reel.")
        else:
            print(f"Error: Invalid symbol '{add_symbol}'")
        print(slot_machine.reels)
        # if amount
    elif remove_symbol and reel:
        print(f"Removing symbol: {remove_symbol}")
        print(f"Amount: {amount}")
        print(f"Reel: {reel}")
        if (reel in slot_machine.reels and
                remove_symbol in slot_machine.reels[reel]):
            slot_machine.reels[reel][remove_symbol] -= amount
        else:
            print(f"Error: Invalid reel '{reel}' or symbol '{remove_symbol}'")
    elif remove_symbol:
        print(f"Removing symbol: {remove_symbol}")
        print(f"Amount: {amount}")
        if remove_symbol in slot_machine.reels['reel1']:
            per_reel_amount: int = int(amount / 3)
            new_reels['reel1'][remove_symbol] -= per_reel_amount
            new_reels['reel2'][remove_symbol] -= per_reel_amount
            new_reels['reel3'][remove_symbol] -= per_reel_amount

            slot_machine.reels = new_reels
            print(f"Removed {per_reel_amount} {remove_symbol} from each reel.")
        else:
            print(f"Error: Invalid symbol '{remove_symbol}'")
        print(slot_machine.reels)

    print("Saving reels...")

    slot_machine.reels = new_reels
    new_reels = slot_machine.reels
    # print(f"Reels: {slot_machine.configuration}")
    print(f"Probabilities saved.")

    # TODO Report payouts
    amount_of_symbols: int = slot_machine.count_symbols()
    reel_amount_of_symbols: int
    reels_table: str = "### Reels\n"
    for reel_name, symbols in new_reels.items():
        reel_symbols: Dict[str, int] = cast(Dict[str, int], symbols)
        symbols_table: str = ""
        symbols_and_amounts: dict_items[str, int] = reel_symbols.items()
        for symbol, amount in symbols_and_amounts:
            symbols_table += f"{symbol}: {amount}\n"
        symbols_dict: Dict[str, int] = cast(Dict[str, int], symbols)
        reel_amount_of_symbols = sum(symbols_dict.values())
        reels_table += (f"**Reel {reel_name}**\n"
                        f"**Symbol**: **Amount**\n"
                        f"{symbols_table}"
                        "**Total**\n"
                        f"{reel_amount_of_symbols}\n\n")
    probabilities: Dict[str, float] = slot_machine.probabilities
    probabilities_table: str = "**Outcome**: **Probability**\n"
    max_digits: int = 4
    lowest_number: float = float("0." + "0" * (max_digits - 1) + "1")
    for symbol, probability in probabilities.items():
        probability_display: str | None = None
        probability_percentage: float = probability * 100
        probability_rounded: float = round(probability_percentage, max_digits)
        if (probability == probability_rounded):
            probability_display = f"{str(probability_percentage)}%"
        elif probability_percentage > lowest_number:
            probability_display = "~{}%".format(
                str(round(probability_percentage, max_digits)))
        else:
            probability_display = f"<{str(lowest_number)}%"
        probabilities_table += f"{symbol}: {probability_display}\n"

    ev: tuple[Piecewise, Piecewise] = slot_machine.calculate_ev()
    expected_return_ugly: Piecewise = ev[0]
    expected_return: str = (
        cast(str, pretty(expected_return_ugly))).replace("⋅", "")
    expected_total_return_ugly: Piecewise = ev[1]
    expected_total_return: str = (
        cast(str, pretty(expected_total_return_ugly,))).replace("⋅", "")
    wagers: List[int] = [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
        25, 50, 75, 99, 100, 500, 1000, 10000, 100000, 1000000]
    rtp_dict: Dict[int, str] = {}
    rtp_display: str | None = None
    for wager in wagers:
        rtp: Float = (
            slot_machine.calculate_rtp(Integer(wager)))
        rtp_percentage = Mul(rtp, 100.0)
        rtp_rounded: Float = round(rtp_percentage, max_digits)
        if rtp == rtp_rounded:
            rtp_display = f"{str(rtp_percentage)}%"
        elif simplify(rtp_percentage) > lowest_number:
            rtp_display = "~{}%".format(str(rtp_rounded))
        else:
            rtp_display = f"<{str(lowest_number)}%"
        rtp_dict[wager] = rtp_display

    rtp_table: str = "**Wager**: **RTP**\n"
    for wager_sample, rtp_sample in rtp_dict.items():
        rtp_table += f"{wager_sample}: {rtp_sample}\n"

    message: str = ("### Reels\n"
                    f"{reels_table}\n"
                    "### Symbols total\n"
                    f"{amount_of_symbols}\n\n\n"
                    "### Probabilities\n"
                    f"{probabilities_table}\n\n"
                    "### Expected values\n"
                    "**Expected total return**\n"
                    f"{expected_total_return}\n\n"
                    "**Expected return**\n"
                    f"{expected_return}\n"
                    '-# "W" means wager\n\n'
                    "### RTP\n"
                    f"{rtp_table}")
    print(message)
    await interaction.followup.send(message, ephemeral=close_off)
    del message


# endregion


# region /slots


@bot.tree.command(name="slots",
                  description="Play on a slot machine")
@app_commands.describe(insert_coins="Insert coins into the slot machine")
@app_commands.describe(private_room="Play in a private room")
@app_commands.describe(jackpot="Check the current jackpot amount")
@app_commands.describe(reboot="Reboot the slot machine")
async def slots(interaction: Interaction,
                insert_coins: int | None = None,
                private_room: bool = False,
                jackpot: bool = False,
                reboot: bool = False) -> None:
    """
    Command to play a slot machine.

    Args:
        interaction (Interaction): The interaction object representing the
        command invocation.
    """
    # TODO Add TOS
    # TODO Add /help
    wager: int | None = insert_coins
    if wager is None:
        wager = 1
    # TODO Log/stat outcomes (esp. wager amounts)
    user: User | Member = interaction.user
    user_id: int = user.id
    if reboot:
        message = (f"### {Coin} Slot Machine\n"
                   f"-# The {Coin} slot machine is restarting...")
        await interaction.response.send_message(message,
                                                ephemeral=private_room)
        del message
        await asyncio.sleep(8)
        if user_id in active_slot_machine_players:
            active_slot_machine_players.remove(user_id)
        message = (f"### {Coin} Slot Machine\n"
                   f"-# Welcome to the {Coin} Casino!\n")
        await interaction.edit_original_response(content=message)
        del message
        return
    elif jackpot:
        # Check the jackpot amount
        jackpot_amount: int = slot_machine.jackpot
        coin_label: str = generate_coin_label(jackpot_amount)
        message = (f"### {Coin} Slot Machine\n"
                     f"-# JACKPOT: {jackpot_amount} "
                     f"{coin_label}.")
        del coin_label
        await interaction.response.send_message(message, ephemeral=private_room)
        return

    # Check if user is already playing on a slot machine
    if user_id in active_slot_machine_players:
        await interaction.response.send_message(
            "You are only allowed to play "
            "on one slot machine at a time.\n"
            "-# If you're having issues, please try rebooting the slot machine "
            f"before contacting the {Coin} Casino staff.",
            ephemeral=True)
        return
    else:
        active_slot_machine_players.add(user_id)

    user_name: str = user.name
    save_data: UserSaveData = (
        UserSaveData(user_id=user_id, user_name=user_name))
    starting_bonus_received: bool = (
        save_data.load("starting_bonus_received") == "True")

    if not starting_bonus_received:
        # Send message to inform user of starting bonus
        starting_bonus_awards: Dict[int, int] = {
            1: 50, 2: 100, 3: 200, 4: 300, 5: 400, 6: 500}
        starting_bonus_table: str = "> **Die roll**\t**Amount**\n"
        for die_roll, amount in starting_bonus_awards.items():
            starting_bonus_table += f"> {die_roll}\t\t\t\t{amount}\n"
        # TODO Divide into separate messages
        message: str = (f"Welcome to the {Coin} Casino! This seems to be your "
                        "first time here.\n"
                        "A standard 6-sided die will decide your starting "
                        "bonus.\n"
                        "The possible outcomes are displayed below.\n\n"
                        f"{starting_bonus_table}")

        starting_bonus_view = (
            StartingBonusView(invoker=user,
                              starting_bonus_awards=starting_bonus_awards,
                              save_data=save_data,
                              log=log,
                              interaction=interaction))
        await interaction.response.send_message(content=message,
                                                view=starting_bonus_view)
        await starting_bonus_view.wait()
        if user_id in active_slot_machine_players:
            active_slot_machine_players.remove(user_id)
        return
    # else:
    #     print("Starting bonus already received.")

    administrator: str = (
        (await bot.fetch_user(ADMINISTRATOR_ID)).mention)

    # Check balance
    user_id_hash: str = sha256(str(user_id).encode()).hexdigest()
    user_balance: int | None = blockchain.get_balance(user=user_id_hash)
    if user_balance is None:
        # Would happen if the blockchain is deleted but not the save data
        message = ("This is odd. It appears you do not have an account.\n"
                   f"{administrator} should look into this.")
        await interaction.response.send_message(content=message)
        del message
        if user_id in active_slot_machine_players:
            active_slot_machine_players.remove(user_id)
        return
    elif user_balance == 0:
        message = (f"You're all out of {coins}!\n")
        await interaction.response.send_message(content=message)
        del message
        if user_id in active_slot_machine_players:
            active_slot_machine_players.remove(user_id)
        return
    elif user_balance < wager:
        coin_label_w: str = generate_coin_label(wager)
        coin_label_b: str = generate_coin_label(user_balance)
        message = (f"You do not have enough {coins} "
                   f"to stake {wager} {coin_label_w}.\n"
                   f"Your current balance is {user_balance} {coin_label_b}.")
        await interaction.response.send_message(content=message, ephemeral=True)
        del coin_label_w
        del coin_label_b
        del message
        if user_id in active_slot_machine_players:
            active_slot_machine_players.remove(user_id)
        return

    
    fees_dict: Dict[str, int | float] = slot_machine.configuration["fees"]
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
        wager >= (low_wager_main_fee + low_wager_jackpot_fee))
    no_jackpot_mode: bool = False if jackpot_fee_paid else True
    jackpot_fee: int
    main_fee: int
    if no_jackpot_mode:
        # TODO Make min_wager config keys
        main_fee = low_wager_main_fee
        jackpot_fee = 0
    elif wager < 10:
        main_fee = low_wager_main_fee
        jackpot_fee = low_wager_jackpot_fee
    elif wager < 100:
        main_fee_unrounded: float = wager * medium_wager_main_fee
        main_fee = round(main_fee_unrounded)
        jackpot_fee_unrounded: float = wager * medium_wager_jackpot_fee
        jackpot_fee = round(jackpot_fee_unrounded)
    else:
        main_fee_unrounded: float = wager * high_wager_main_fee
        main_fee = round(main_fee_unrounded)
        jackpot_fee_unrounded: float = wager * high_wager_jackpot_fee
        jackpot_fee = round(jackpot_fee_unrounded)
    fees: int = jackpot_fee + main_fee
    slot_machine_view = SlotMachineView(invoker=user,
                                        slot_machine=slot_machine,
                                        wager=wager,
                                        fees=fees,
                                        interaction=interaction)
    # TODO Add animation
    # Workaround for Discord stripping trailing whitespaces
    empty_space: LiteralString = "\N{HANGUL FILLER}" * 11

    # TODO DRY
    slots_message: str = (f"### {Coin} Slot Machine\n"
                          f"-# Coin: {wager}\n"
                          f"-# Fee: {fees}\n"
                          f"{empty_space}\n"
                          "The reels are spinning...\n"
                          "\n"
                          f"🔳\t\t🔳\t\t🔳\n"
                          f"{empty_space}")

    await interaction.response.send_message(content=slots_message,
                                            view=slot_machine_view,
                                            ephemeral=private_room)
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
        all_buttons_clicked = buttons_clicked_count == 3
        user_stopped_clicking = (
            buttons_clicked_count == previous_buttons_clicked_count)
        if (user_irresonsive or all_buttons_clicked or user_stopped_clicking):
            let_the_user_stop = False
        previous_buttons_clicked_count: int = buttons_clicked_count
    await slot_machine_view.start_auto_stop()

    # Get results
    results: Dict[str, Dict[str, str | int | float |
                            PartialEmoji]] = slot_machine_view.reels_results

    # Create some variables for the outcome messages
    slot_machine_header: str = slot_machine_view.message_header
    slot_machine_results_row: str = slot_machine_view.message_results_row
    del slot_machine_view

    # Calculate win amount
    event_name: str
    event_name_friendly: str
    # Win money is the amount of money that the event will award
    # (not usually the same as net profit or net return)
    win_money: int
    event_name, event_name_friendly, win_money = (
        slot_machine.calculate_award_money(wager=wager,
                                           results=results))

    # Generate outcome messages
    event_message: str | None = None
    # print(f"event_name: '{event_name}'")
    # print(f"event_name_friendly: '{event_name_friendly}'")
    # print(f"win money: '{win_money}'")
    coin_label_wm: str = generate_coin_label(win_money)
    if event_name == "jackpot_fail":
        jackpot_amount: int = slot_machine.jackpot
        coin_label_fee: str = generate_coin_label(jackpot_amount)
        coin_label_jackpot: str = generate_coin_label(jackpot_amount)
        event_message = (f"{event_name_friendly}! Unfortunately, you did "
                         "not pay the jackpot fee of "
                         f"{jackpot_fee} {coin_label_fee}, meaning "
                         "that you did not win the jackpot of "
                         f"{jackpot_amount} {coin_label_jackpot}. "
                         "Better luck next time!")
        del coin_label_fee
        del coin_label_jackpot
    elif event_name == "standard_lose":
        event_message = None
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
                         f"stake of {wager} {coin_label_wm}. "
                         "Better luck next time!")
        net_return = -wager
        total_return = 0
    elif no_jackpot_mode:
        net_return = win_money - main_fee
        if win_money > 0:
            total_return = win_money - main_fee
        else:
            total_return = wager - main_fee
    else:
        net_return = win_money - main_fee - jackpot_fee
        if win_money > 0:
            # You don't keep any of your initial money on wins
            total_return = win_money - main_fee - jackpot_fee
        else:
            # You keep you wager minus fees on lose
            total_return = wager - main_fee - jackpot_fee
    # print(f"standard_fee: {main_fee}")
    # print(f"jackpot_fee: {jackpot_fee}")
    # print(f"jackpot_fee_paid: {jackpot_fee_paid}")
    # print(f"jackpot_mode: {jackpot_mode}")
    # print(f"win_money: {win_money}")
    # print(f"net_return: {net_return}")
    # print(f"total_return: {total_return}")
    coin_label_nr: str = generate_coin_label(net_return)
    if net_return > 0:
        log_line = (f"{user_name} ({user_id}) won the {event_name} "
                    f"({event_name_friendly}) reward "
                    f"of {win_money} {coin_label_wm} and profited "
                    f"{net_return} {coin_label_nr} on the {Coin} slot machine.")
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
                        f"{wager} {coin_label_nr} on the {Coin} slot machine, "
                        "yet they neither lost any coins nor profited.")
        elif win_money > 0:
            # With the default config, this will happen if the fees are higher
            # than the win money
            log_line = (f"{user_name} ({user_id}) won the {event_name} "
                        f"({event_name_friendly}) reward "
                        f"of {win_money} {coin_label_wm} on the {Coin} "
                        "slot machine, but made no profit.")
        else:
            # This should not happen without win money with the default config
            # (because of the fees)
            log_line = (f"{user_name} ({user_id}) made no profit on the "
                        f"{Coin} slot machine.")
    else:
        # if net return is negative, the user lost money
        if event_name == "lose_wager":
            log_line = (f"{user_name} ({user_id}) got the {event_name} event "
                        f"({event_name_friendly}) and lost their entire wager "
                        f"of {wager} {coin_label_nr} on the "
                        f"{Coin} slot machine.")
        if event_name == "jackpot_fail":
            log_line = (f"{user_name} ({user_id}) lost {-net_return} "
                        f"{coin_label_nr} on the {Coin} slot machine by "
                        f"getting the {event_name} ({event_name_friendly}) "
                        "event without paying the jackpot fee.")
        elif win_money > 0:
            # turn -net_return into a positive number
            log_line = (f"{user_name} ({user_id}) won "
                        f"{win_money} {coin_label_wm} on "
                        f"the {event_name} ({event_name_friendly}) reward, "
                        f"but lost {-net_return} {coin_label_nr} in net return "
                        f"on the {Coin} slot machine.")
        else:
            log_line = (f"{user_name} ({user_id}) lost "
                        f"{-net_return} {coin_label_nr} on "
                        f"the {Coin} slot machine.")
    del coin_label_wm

    # Generate collect message
    coin_label_tr: str = generate_coin_label(total_return)
    collect_message: str | None = None
    if (total_return > 0):
        collect_message = (f"-# You collect {total_return} {coin_label_tr}.")
    else:
        collect_message = None
    del coin_label_nr

    if event_message or collect_message:
        # Display outcome messages
        outcome_message_line_1: str = empty_space
        outcome_message_line_2: str = empty_space
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
        slots_message_outcome: str = (f"{slot_machine_header}\n"
                                      f"{outcome_message_line_1}\n"
                                      f"{outcome_message_line_2}\n"
                                      f"{empty_space}\n"
                                      "The reels have stopped.\n"
                                      f"{empty_space}\n"
                                      f"{slot_machine_results_row}\n"
                                      f"{empty_space}")
        del outcome_message_line_1
        del outcome_message_line_2
        del slot_machine_results_row
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
            sender = CASINO_HOUSE_ID
            receiver = user
        else:
            sender = user
            receiver = CASINO_HOUSE_ID
            # flip to positive value (transferring a negative amount would mean
            # reducing the receiver's balance)
            transfer_amount = -net_return
        await add_block_transaction(
            blockchain=blockchain,
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
    log.log(line=log_line, timestamp=log_timestamp)
    del log_timestamp
    del log_line

    if user_id in active_slot_machine_players:
        active_slot_machine_players.remove(user_id)

    if last_block_error:
        # send message to admin
        await interaction.response.send_message("An error occurred. "
                                                f"{administrator} pls fix.")
        await terminate_bot()
    del last_block_error

    if event_name == "jackpot":
        # Reset the jackpot
        events: Dict[str, Dict[str, int | float]] = cast(
            Dict[str, Dict[str, int | float]],
            slot_machine.configuration["events"])
        jackpot_seed: int = cast(int, events["jackpot"]["fixed_amount"])
        slot_machine.jackpot = jackpot_seed
    else:
        slot_machine.jackpot += 1


# endregion


# TODO Track reaction removals
# TODO Add more games

# region Main
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN is not set in the environment variables.")
# endregion
