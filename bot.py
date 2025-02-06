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
from sympy import symbols, Expr, Add, Mul, Float, Integer, Rational, simplify
from typing import (
    Dict, List, LiteralString, NoReturn, TextIO, cast, NamedTuple, Literal)
# endregion

# region Named tuples


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
        self.configuration: Dict[str, str | Dict[str, Dict[str, int]]] = (
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
        configuration: Dict[str, str | Dict[str, Dict[str, int]]] = {
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

    def read(self) -> Dict[str, str | Dict[str, Dict[str, int]]]:
        if not exists(self.file_name):
            self.create()

        with open(self.file_name, "r") as file:
            configuration: Dict[str, str | Dict[str, Dict[str, int]]] = (
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
        self.configuration: (
            Dict[str,
                 Dict[str, Dict[str, int | float]] | Dict[str, int] | int]) = (
            self.load_config())
        self._reels: Dict[str, Dict[str, int]] = self.load_reels()
        # self.emoji_ids: Dict[str, int] = cast(Dict[str, int],
        #                                       self.configuration["emoji_ids"])
        self._probabilities: Dict[str, float] = (
            self.calculate_all_probabilities())
        self._jackpot: int = self.load_jackpot()

    def load_reels(self) -> Dict[str, Dict[str, int]]:
        # print("Getting reels...")
        self.configuration = self.load_config()
        reels: Dict[str, Dict[str, int]] = (
            cast(Dict[str, Dict[str, int]], self.configuration["reels"]))
        return reels

    @property
    def reels(self) -> Dict[str, Dict[str, int]]:
        return self._reels

    @reels.setter
    def reels(self, value: Dict[str, Dict[str, int]]) -> None:
        self._reels = value
        self.configuration["reels"] = (
            cast(Dict[str, Dict[str, int | float]], self._reels))
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
        configuration: Dict[
            str,
            Dict[str, Dict[str, int | str | float]] |
            Dict[str, int] |
            int |
            float
            # jackpot_amount will automatically be set to the jackpot event's
            # fixed_amount value if the latter is higher than the former
        ] = {
            "events": {
                "lose_wager": {
                    "emoji_name": "",
                    "emoji_id": 0,
                    "fixed_amount": 0,
                    "wager_multiplier": -1.0
                },
                "small_win": {
                    "emoji_name": "",
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
                    "wager_multiplier": 69.0
                },
                "jackpot": {
                    "emoji_name": "",
                    "emoji_id": 0,
                    "fixed_amount": 100,
                    "wager_multiplier": 1.0
                }
            },
            "reels": {
                "1": {
                    "lose_wager": 1,
                    "small_win": 3,
                    "medium_win": 11,
                    "high_win": 4,
                    "jackpot": 1
                },
                "2": {
                    "lose_wager": 1,
                    "small_win": 3,
                    "medium_win": 11,
                    "high_win": 4,
                    "jackpot": 1
                },
                "3": {
                    "lose_wager": 1,
                    "small_win": 3,
                    "medium_win": 11,
                    "high_win": 4,
                    "jackpot": 1
                }
            },
            "jackpot_amount": 501
        }
        # Save the configuration to the file
        with open(self.file_name, "w") as file:
            file.write(json.dumps(configuration))
        print("Template slot machine configuration file created.")

    def load_config(self) -> (
            Dict[
                str, Dict[str, Dict[str, int | float]] | Dict[str, int] | int]):
        if not exists(self.file_name):
            self.create_config()

        with open(self.file_name, "r") as file:
            configuration: (Dict[
                str, Dict[str, Dict[str, int | float]] | Dict[str, int] | int
            ]) = json.loads(file.read())
            return configuration

    def save_config(self) -> None:
        # print("Saving slot machine configuration...")
        with open(self.file_name, "w") as file:
            file.write(json.dumps(self.configuration))
        # print("Slot machine configuration saved.")
    # endregion

    # region Slot probability

    def calculate_reel_symbol_probability(self,
                                          reel: str,
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
        overall_probability: float = 1.0
        for reel in self.reels:
            probability_for_reel: float = (
                self.calculate_reel_symbol_probability(reel, symbol))
            overall_probability *= probability_for_reel
        return overall_probability

    def calculate_losing_probabilities(self) -> tuple[float, float]:
        print("Calculating chance of losing...")

        # No symbols match
        standard_lose_probability: float = 1.0

        # Either lose_wager symbols match or no symbols match
        any_lose_probability: float = 1.0

        symbols: List[str] = [symbol for symbol in self.reels["1"]]
        for symbol in symbols:
            symbols_match_probability: float = (
                self.calculate_event_probability(symbol))
            symbols_no_match_probability: float = 1 - symbols_match_probability
            standard_lose_probability *= symbols_no_match_probability
            if symbol != "lose_wager":
                any_lose_probability *= symbols_no_match_probability
        return (any_lose_probability, standard_lose_probability)

    def calculate_all_probabilities(self) -> Dict[str, float]:
        self.reels = self.load_reels()
        probabilities: Dict[str, float] = {}
        for symbol in self.reels["1"]:
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
        if reel is None:
            return sum([sum(reel.values()) for reel in self.reels.values()])
        else:
            return sum(self.reels[reel].values())
    # endregion

    # region Slot total return
    def calculate_expected_total_return_or_profit(self,
                                                  jackpot_mode: bool,
                                                  return_or_profit: (
                                                      Literal[
                                                          "return",
                                                          "profit"])) -> Add:
        # From the UX perspective, there is only the wager, which can be 1 or
        # anything above. However,
        # each spin costs 1 coin. The player will not keep this coin in any
        # win event.
        # If the player sets their wager to 2 or more, one of those coins is
        # the jackpot fee. It goes directly to the jackpot. The player will not
        # keep this coin in any win event.
        # If the player does not strike a combo, they win nothing, so the net
        # return for that spin is either -1 (the spin fee) or -2 (the spin fee
        # and the jackpot fee).

        # Jackpot mode is when the player pays the 1 coin jackpot fee by setting
        # their wager to a value higher than 1. In this mode, the player is
        # eligible for and contributing to the jackpot.
        # If they player gets the jackpot combo but didn't pay the jackpot fee,
        # it's equivalent to getting a standard lose (no combo).

        self.configuration = self.load_config()
        probabilities: Dict[str, float] = self.calculate_all_probabilities()
        events: Dict[str, Dict[str, int | float]] = cast(
            Dict[str, Dict[str, int | float]], self.configuration["events"])
        W: Expr = symbols('W')  # wager
        event_return: Integer | Add = Integer(0)
        event_total_return: Integer | Add = Integer(0)
        expected_total_return_contribution: Integer | Mul = Integer(0)
        expected_profit_contribution: Integer | Mul = Integer(0)
        expected_total_return: Integer | Add = Integer(0)
        expected_profit: Integer | Add = Integer(0)
        main_fee_int: int = 1
        main_fee: Expr = Integer(main_fee_int)
        jackpot_fee_int: int = 1
        jackpot_fee: Expr = Integer(jackpot_fee_int)
        print(f"Main fee: {main_fee_int}")
        if jackpot_mode is True:
            print("----------JACKPOT MODE----------")
            print(f"Jackpot fee: {jackpot_fee_int}")
        else:
            print("----------STANDARD MODE----------")
        for event in events:
            print(f"----\nEVENT: {event}")
            # Get the probability of this event
            p_event_float: float = probabilities[event]
            p_event = Float(p_event_float)
            print(f"Event probability: {p_event_float}")
            if p_event_float == 0.0:
                continue
            # Initialize variables
            fixed_amount_int: int = 0
            fixed_amount: Expr = Integer(fixed_amount_int)
            wager_multiplier_float: float
            wager_multiplier: Expr
            if ((event == "standard_lose") or
                    (event == "jackpot" and jackpot_mode is False)):
                # If the player doesn't pay the 1 coin jackpot fee and
                # loses,
                # he ends up with 0 coins (he only paid the 1 coin spin fee and
                # didn't win anything)
                #
                # If the player pays the 1 coin jackpot fee and loses,
                # he ends up with his wager minus the standard fee minus the
                # jackpot fee
                #
                # If the player doesn't pay the 1 coin jackpot fee
                # and gets the jackpot combo,
                # he ends up with 0 coins (he only paid the
                # 1 coin spin fee and since he didn't pay the
                # jackpot fee, he doesn't get the jackpot)
                # This is equivalent to a standard lose (no combo)
                wager_multiplier_float = 1.0
                fixed_amount_int = 0
            elif event == "jackpot" and jackpot_mode is True:
                # If the player pays the 1 coin jackpot fee
                # and wins the jackpot,
                # he ends up with his wager minus the standard fee and the
                # jackpot fee, plus the jackpot
                # Variables
                fixed_amount_int = cast(int, events[event]["fixed_amount"])
                jackpot_seed: int = fixed_amount_int
                print(f"Jackpot seed: {jackpot_seed}")
                jackpot_average: float = (
                    self.calculate_average_jackpot(
                        seed=jackpot_seed))
                # TODO Add parameter to return RTP with jackpot excluded
                # jackpot_average: float = 0.0
                print(f"Jackpot average: {jackpot_average}")
                # I expect wager multiplier to be 1.0 for the jackpot,
                # but let's include it in the calculation anyway,
                # in case someone wants to use a different value
                wager_multiplier_float = events[event]["wager_multiplier"]
                wager_multiplier = Float(wager_multiplier_float)

                # Calculations
                event_total_return = Add(
                    Mul(W, wager_multiplier),
                    jackpot_average,
                    -main_fee,
                    -jackpot_fee)
                event_return = Add(
                    event_total_return,
                    -W)
                expected_total_return_contribution = (
                    Mul(p_event, event_total_return))
                expected_profit_contribution = (
                    Mul(p_event, event_return))
                print(f"Event total return: {event_total_return} "
                      "[(w * k) + jackpot - main_fee - jackpot_fee(")
                print(f"Event return: {event_return} "
                      "[total return - w]")
                print("Expected total return contribution: "
                      f"{expected_total_return_contribution}")
                print("Expected profit contribution: "
                      f"{expected_profit_contribution}")
                expected_total_return = Add(
                    expected_total_return,
                    expected_total_return_contribution)
                expected_profit = Add(
                    expected_profit,
                    expected_profit_contribution)
                continue
            else:
                # As of typing, this includes all remaining win events
                # plus the lose_wager event
                #
                # Variables
                fixed_amount_int = cast(int, events[event]["fixed_amount"])
                wager_multiplier_float = events[event]["wager_multiplier"]
                print(f"Multiplier (k): {wager_multiplier_float}")
                print(f"Fixed amount (x): {fixed_amount_int}")
            wager_multiplier = Float(wager_multiplier_float)
            fixed_amount = Integer(fixed_amount_int)
            # Calculations
            #
            # If the player doesn't pay the 1 coin jackpot fee and
            # wins a non-jackpot award
            # He ends up with his wager plus award
            #
            # The gross return amount the player gets back (i.e. including
            # the wager)
            # The net amount the player gets back (excluding the wager)
            if jackpot_mode is True:
                # If the player pays the 1 coin jackpot fee and
                # wins a non-jackpot award
                # He ends up with his wager plus award minus
                # the jackpot fee
                #
                # Subtract the jackpot fee
                event_total_return = Add(
                    Mul(W, wager_multiplier),
                    fixed_amount,
                    -main_fee,
                    -jackpot_fee)
                print(f"Event total return: {event_total_return} "
                      "[(w * k) + x - main_fee - jackpot_fee]")
            else:
                event_total_return = Add(
                    Mul(W, wager_multiplier),
                    fixed_amount,
                    -main_fee)
                print(f"Event total return: {event_total_return} "
                      "[(w * k) + x - main_fee]")
            event_return = Add(event_total_return, -W)
            print(f"Event return: {event_return} "
                  "[total return - w]")
            # This event's contribution to
            # the average total return over many plays
            expected_total_return_contribution = (
                Mul(p_event, event_total_return))
            # This event's contribution to
            # the average profit over many plays
            expected_profit_contribution = (
                Mul(p_event, event_return))
            print("Expected total return contribution: "
                  f"{expected_total_return_contribution}")
            print("Expected profit contribution: "
                  f"{expected_profit_contribution}")
            expected_total_return = Add(
                expected_total_return,
                expected_total_return_contribution)
            expected_profit = Add(
                expected_profit,
                expected_profit_contribution)
        print(f"Expected total return: {expected_total_return}")
        print(f"Expected profit: {expected_profit}")
        # total_return_expanded: Expr = cast(Expr, expand(expected_total_return))
        # print(f"Expected total return expanded: "
        #       f"{expected_total_return_expanded}")

        # coefficient = expected_total_return.coeff(W, 1)
        # constant = expected_total_return.coeff(W, 0)
        # print(f"Expected total return coefficient: {coefficient}")
        # print(f"Expected total return constant: {constant}")
        if return_or_profit == "return":
            return cast(Add, expected_total_return)
        elif return_or_profit == "profit":
            return cast(Add, expected_profit)
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
    def calculate_rtp(self, wager: int) -> Float:
        jackpot_fee = 1
        standard_fee = 1
        jackpot_fee_paid: bool = wager >= (jackpot_fee + standard_fee)
        jackpot_mode: bool = True if jackpot_fee_paid else False
        expected_total_return: Add = (
            self.calculate_expected_total_return_or_profit(
                jackpot_mode=jackpot_mode, return_or_profit="return"))
        # IMPROVE Fix error reported by Pylance
        evaluated_total_return: Float = (
            cast(Float, expected_total_return.subs(symbols('W'), wager)))
        rtp = Rational(evaluated_total_return, wager)
        rtp_decimal: Float = cast(Float, rtp.evalf())
        print(f"RTP: {rtp}")
        print(f"RTP decimal: {rtp_decimal}")
        return rtp_decimal
    # endregion

    # region Slot stop reel
    """ def pull_lever(self):
        symbols_landed = []
        for reel in self.reels:
            symbol = self.stop_reel(reel)
            symbols_landed.append(symbol)
        return symbols_landed """

    def stop_reel(self, reel: str) -> str:
        # Create a list with all units of each symbol type on the reel
        reel_symbols: List[str] = []
        for symbol in self.reels[reel]:
            reel_symbols.extend([symbol] * self.reels[reel][symbol])
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
            results["1"]["name"] == results["2"]["name"] == results["3"]["name"]
        )):
            return ("standard_lose", "No win", 0)

        standard_fee = 1
        jackpot_fee = 1
        jackpot_fee_paid: bool = wager >= (jackpot_fee + standard_fee)
        jackpot_mode: bool = True if jackpot_fee_paid else False
        print("results: ", results)
        event_name: str = cast(str, results["1"]["name"])
        print(f"event_name: {event_name}")
        wager_multiplier: float = cast(float, results["1"]["wager_multiplier"])
        fixed_amount_payout: int = cast(int, results["1"]["fixed_amount"])
        print(f"event_multiplier: {wager_multiplier}")
        print(f"fixed_amount_payout: {fixed_amount_payout}")
        event_name_friendly: str = ""
        win_money: float = 0.0
        win_money_rounded: int = 0
        if event_name == "lose_wager":
            event_name_friendly = "Lose wager"
            return (event_name, event_name_friendly, 0)
        elif event_name == "jackpot":
            if jackpot_mode is False:
                event_name = "jackpot_fail"
                event_name_friendly = "No Jackpot"
                win_money_rounded = 0
            else:
                event_name_friendly = "JACKPOT"
                win_money_rounded = self.jackpot
            return (event_name, event_name_friendly, win_money_rounded)
        win_money = (
            (wager * wager_multiplier) + fixed_amount_payout)
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
        super().__init__(timeout=5)
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
                 interaction: Interaction) -> None:
        super().__init__(timeout=20)
        self.current_reel_number: int = 1
        self.reels_stopped: int = 0
        self.invoker: User | Member = invoker
        self.invoker_id: int = invoker.id
        self.slot_machine: SlotMachine = slot_machine
        self.wager: int = wager
        # TODO Move message variables to global scope
        self.empty_space: LiteralString = "\N{HANGUL FILLER}" * 11
        self.message_header: str = f"### {Coin} Slot Machine\n"
        self.message_reel_status: str = "The reels are spinning..."
        self.message_collect_screen: str = (f"-# Coin: {wager}\n"
                                            f"{self.empty_space}\n"
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
                "1":
                {"emoji": blank_emoji},

                "2":
                {"emoji": blank_emoji},

                "3":
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
        # reel_number: int = self.current_reel_number
        # Map button IDs to reel key names
        reel_stop_button_map: Dict[str, str] = {
            "stop_reel_1": "1",
            "stop_reel_2": "2",
            "stop_reel_3": "3"
        }
        # Pick reel based on button ID
        reel_number: str = reel_stop_button_map[button_id]
        reel_name = str(reel_number)
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
        self.reels_results[reel_number] = symbol_properties
        self.reels_stopped += 1
        reel_status: str = (
            "The reels are spinning..." if self.reels_stopped < 3 else
            "The reels have stopped.")
        empty_space: LiteralString = "\N{HANGUL FILLER}" * 11
        self.message_reel_status = reel_status
        self.message_results_row: str = (
            f"{self.reels_results['1']['emoji']}\t\t"
            f"{self.reels_results['2']['emoji']}\t\t"
            f"{self.reels_results['3']['emoji']}")
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
    print(f"Guild IDs: {guild_ids}")
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
    await interaction.response.send_message(f"{sender.mention} transferred "
                                            f"{amount} {coin_label_a} "
                                            f"to {receiver.mention}.")
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
async def balance(interaction: Interaction, user: Member | None = None) -> None:
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
        user_to_check = interaction.user.mention
        user_id: int = interaction.user.id
    else:
        user_to_check = user.mention
        user_id: int = user.id

    user_id_hash: str = sha256(str(user_id).encode()).hexdigest()
    del user_id
    balance: int | None = blockchain.get_balance(user=user_id_hash)
    if balance is None:
        await interaction.response.send_message(f"{user_to_check} has 0 "
                                                f"{coins}.")
    else:
        coin_label: str = generate_coin_label(balance)
        await interaction.response.send_message(f"{user_to_check} has "
                                            f"{balance} {coin_label}.")
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
@app_commands.describe(report="Report the current configuration")
async def reels(interaction: Interaction,
                add_symbol: str | None = None,
                remove_symbol: str | None = None,
                amount: int | None = None,
                reel: str | None = None,
                report: bool | None = None) -> None:
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
        await interaction.response.send_message(message)
        del message
        return
    if amount is None:
        if reel is None:
            amount = 3
        else:
            amount = 1
    # Refresh reels config from file
    slot_machine.reels = slot_machine.load_reels()
    new_reels: Dict[str, Dict[str, int]] = slot_machine.reels
    if add_symbol and remove_symbol:
        await interaction.response.send_message("You can only add or remove a "
                                                "symbol at a time.")
        return
    if add_symbol and reel is None:
        if amount % 3 != 0:
            await interaction.response.send_message("The amount of symbols to "
                                                    "add must be a multiple "
                                                    "of 3.")
            return
    elif add_symbol and reel:
        print(f"add_symboling symbol: {add_symbol}")
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
        if add_symbol in slot_machine.reels['1']:
            per_reel_amount: int = int(amount / 3)
            new_reels['1'][add_symbol] += per_reel_amount
            new_reels['2'][add_symbol] += per_reel_amount
            new_reels['3'][add_symbol] += per_reel_amount

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
        if remove_symbol in slot_machine.reels['1']:
            per_reel_amount: int = int(amount / 3)
            new_reels['1'][remove_symbol] -= per_reel_amount
            new_reels['2'][remove_symbol] -= per_reel_amount
            new_reels['3'][remove_symbol] -= per_reel_amount

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
    for reel, symbols in new_reels.items():
        symbols_table: str = ""
        for symbol, amount in symbols.items():
            symbols_table += f"{symbol}: {amount}\n"
        reel_amount_of_symbols = sum(symbols.values())
        reels_table += (f"**Reel {reel}**\n"
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

    cheap_mode_etr: Expr = (
        slot_machine.calculate_expected_total_return_or_profit(
            jackpot_mode=False, return_or_profit="return"))
    # TODO Suppress output
    cheap_mode_etp: Expr = (
        slot_machine.calculate_expected_total_return_or_profit(
            jackpot_mode=False, return_or_profit="profit"))
    jackpot_mode_etr: Expr = (
        slot_machine.calculate_expected_total_return_or_profit(
            jackpot_mode=True, return_or_profit="return"))
    jackpot_mode_etp: Expr = (
        slot_machine.calculate_expected_total_return_or_profit(
            jackpot_mode=True, return_or_profit="profit"))
    wagers: List[int] = [
        1, 2, 5, 10, 50, 100, 500, 1000, 10000, 100000, 1000000]
    rtp_dict: Dict[int, str] = {}
    rtp_display: str | None = None
    for wager in wagers:
        rtp: Float = (
            slot_machine.calculate_rtp(wager))
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
                    "**Expected total return (Jackpot fee paid)**\n"
                    f"{str(cheap_mode_etr).replace("*", "")}\n"
                    "**Expected total return (Jackpot fee not paid)**\n"
                    f"{str(jackpot_mode_etr).replace("*", "")}\n"
                    "**Expected total profit (Jackpot fee paid)**\n"
                    f"{str(cheap_mode_etp).replace('*', '')}\n"
                    "**Expected total profit (Jackpot fee not paid)**\n"
                    f"{str(jackpot_mode_etp).replace('*', '')}\n"
                    '-# "W" means wager\n\n'
                    "### RTP\n"
                    f"{rtp_table}")
    await interaction.response.send_message(message)
    del message


# endregion


# region /slots


@bot.tree.command(name="slots",
                  description="Play on a slot machine")
@app_commands.describe(insert_coins="Insert coins into the slot machine")
async def slots(interaction: Interaction,
                insert_coins: int | None = None) -> None:
    """
    Command to play a slot machine.

    Args:
        interaction (Interaction): The interaction object representing the
        command invocation.
    """
    # TODO Ensure you cannot wager 0 coins or negative
    # TODO Add TOS
    # TODO Add /help
    wager: int | None = insert_coins
    if wager is None:
        wager = 1
    # TODO Ensure you cannot play if your balance is below wager
    # TODO Ensure you cannot play if you have a pending game
    # TODO Log/stat outcomes (esp. wager amounts)
    user: User | Member = interaction.user
    user_id: int = user.id
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
        del starting_bonus_view
    """ else:
        print("Starting bonus already received.") """

    administrator: str = (
        (await bot.fetch_user(ADMINISTRATOR_ID)).mention)
    
    # Check balance
    user_id_hash: str = sha256(str(user_id).encode()).hexdigest()
    user_balance: int | None = blockchain.get_balance(user=user_id_hash)
    if user_balance is None:
        # Would happen if the blockchain is deleted but not the save data
        message = ("This is odd. It appears you do not have an account.\n"
                   f"{administrator} should look into this.")
        return
    elif user_balance == 0:
        message = (f"You're all out of {coins}!\n")
        await interaction.response.send_message(content=message)
        del message
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
        return
    
    slot_machine_view = SlotMachineView(invoker=user,
                                        slot_machine=slot_machine,
                                        wager=wager,
                                        interaction=interaction)
    # TODO Add animation
    # Workaround for Discord stripping trailing whitespaces
    empty_space: LiteralString = "\N{HANGUL FILLER}" * 11

    # TODO DRY
    slots_message: str = (f"### {Coin} Slot Machine\n"
                          f"-# Coin: {wager}\n"
                          f"{empty_space}\n"
                          f"{empty_space}\n"
                          "The reels are spinning...\n"
                          "\n"
                          f"🔳\t\t🔳\t\t🔳\n"
                          f"{empty_space}")

    await interaction.response.send_message(content=slots_message,
                                            view=slot_machine_view)
    del slots_message
    # Auto-stop-timer
    # Wait 3 seconds and see if the user has manually pressed a stop button
    # If not, stop the reels automatically
    # Until all reels have been stopped, wait another 3 seconds if the user
    # has clicked a button within the last 3 seconds
    # Views have built-in timers that you can wait for with the wait() method,
    # but since we have tasks to do when the timer runs out, that won't work
    # There is probably a way to do it with just the view, but I don't
    # know how
    previous_buttons_clicked_count = 0
    while True:
        buttons_clicked_count = 0
        await asyncio.sleep(3.0)
        for button in slot_machine_view.stop_reel_buttons:
            button_clicked: bool = button.disabled
            if button_clicked:
                buttons_clicked_count += 1
        if ((buttons_clicked_count == 0) or
            (buttons_clicked_count == previous_buttons_clicked_count) or
                (buttons_clicked_count == 3)):
            break
        previous_buttons_clicked_count: int = buttons_clicked_count
    await slot_machine_view.start_auto_stop()
    # await asyncio.sleep(1.0)

    # Get results
    results: Dict[str, Dict[str, str | int | float |
                            PartialEmoji]] = slot_machine_view.reels_results

    # Create some variables for the outcome messages
    slot_machine_header: str = slot_machine_view.message_header
    slot_machine_results_row: str = slot_machine_view.message_results_row
    print(f"slot_machine_results_row: '{slot_machine_results_row}'")
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
    jackpot_fee: int = 1
    event_message: str | None = None
    print(f"event_name: '{event_name}'")
    print(f"event_name_friendly: '{event_name_friendly}'")
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
    standard_fee: int = 1
    jackpot_fee_paid: bool = (
        wager >= (jackpot_fee + standard_fee))
    jackpot_mode: bool = True if jackpot_fee_paid else False
    log_line: str = ""
    if event_name == "lose_wager":
        event_message = (f"You lost your entire "
                         f"stake of {wager} {coin_label_wm}. "
                         "Better luck next time!")
        net_return = -wager
        total_return = 0
        # Remove variables with common names to prevent accidental use
    elif jackpot_mode:
        net_return = win_money - standard_fee - jackpot_fee
        if win_money > 0:
            # You don't keep any of your initial money on wins
            total_return = win_money - standard_fee - jackpot_fee
        else:
            # You keep you wager minus fees on lose
            total_return = wager - standard_fee - jackpot_fee
    else:
        net_return = win_money - standard_fee
        if win_money > 0:
            total_return = win_money - standard_fee
        else:
            total_return = wager - standard_fee
    print(f"standard_fee: {standard_fee}")
    print(f"jackpot_fee: {jackpot_fee}")
    print(f"jackpot_fee_paid: {jackpot_fee_paid}")
    print(f"jackpot_mode: {jackpot_mode}")
    print(f"win_money: {win_money}")
    print(f"net_return: {net_return}")
    print(f"total_return: {total_return}")
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
    sender: User | Member | int
    receiver: User | Member | int
    log_timestamp: float = 0.0
    last_block_error = False
    transfer_amount: int
    if net_return != 0:
        if net_return > 0:
            transfer_amount = net_return
            sender = CASINO_HOUSE_ID
            receiver = user
        elif net_return < 0:
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
        if last_block_error:
            # send message to admin
            await interaction.response.send_message("An error occurred. "
                                                    f"{administrator} pls fix.")
            await terminate_bot()

        if event_name == "jackpot":
            # Reset the jackpot
            events: Dict[str, Dict[str, int | float]] = cast(
                Dict[str, Dict[str, int | float]],
                slot_machine.configuration["events"])
            jackpot_seed: int = cast(int, events["jackpot"]["fixed_amount"])
            slot_machine.jackpot = jackpot_seed
        else:
            slot_machine.jackpot += 1
    del log_line


# endregion


# region Message
# Example slash command

@bot.tree.command(name="ping", description="Replies with Pong!")
async def ping(interaction: Interaction) -> None:
    """
    Replies with Pong! The response is visible only to the user who invoked the
    command.

    Args:
        interaction (Interaction): The interaction object representing the
        command invocation.
    """
    await interaction.response.send_message("Pong!", ephemeral=True)
# endregion

# TODO Prevent self-mining
# TODO Track reaction removals
# TODO Add "hide" parameters to commands
# TODO Add more games

# region Main
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN is not set in the environment variables.")
# endregion
