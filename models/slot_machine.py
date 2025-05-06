# region Imports
# Standard library
import random
import math
from os import makedirs, stat
from os.path import exists
from typing import Dict, KeysView, List, LiteralString, cast, Literal, Any

# Third party
from sympy import (symbols,  # pyright: ignore [reportUnknownVariableType]
                   Expr, Add, Mul, Float, Integer, Eq, Lt, Ge, Rational,
                   Piecewise)
import lazyimports

# Local
import core.global_state as g
with lazyimports.lazy_imports("schemas.pydantic_models:SlotEvent"):
    from schemas.pydantic_models import SlotEvent
from schemas.sponsorblockcasino_types import (Reels, ReelSymbol, ReelResults,
                                      SlotMachineConfig)
# endregion


class SlotMachine:
    """
    Represents a slot machine game with various functionalities, such as
    loading configuration, calculating probabilities, managing reels,
    calculating expected value, and handling jackpots.
    Methods:
        __init__(file_name = "data/slot_machine.json"):
            Initializes the SlotMachine class with the given
                configuration file.
        load_reels():
            Loads the reels configuration from the
            slot machine configuration file.
        reels():
            Returns the reel configuration.
        reels(value):
            Sets the reel configuration and updates the configuration file.
        probabilities():
            Runs the calculate_all_probabilities method and returns the
            calculated probabilities.
        jackpot():
            Returns the current jackpot amount.
        jackpot(value):
            Sets the jackpot amount and updates the configuration file.
        load_jackpot():
            Loads the current jackpot pool.
        create_config():
            Creates a template slot machine configuration file.
        load_config():
            Loads the slot machine configuration from a JSON file.
        save_config():
            Saves the current slot machine configuration to a file.
        calculate_reel_symbol_probability(reel, symbol):
            Calculate the probability of a specific symbol appearing on a
            given reel.
        calculate_event_probability(symbol):
            Calculate the overall probability of a given symbol appearing
            across all reels.
        calculate_losing_probabilities():
            Calculate the probability of losing the entire wager and the
            probability of not getting any symbols to match.
        calculate_all_probabilities():
            Calculate the probabilities for all possible outcomes in the
            slot machine.
        count_symbols(ree):
            Count the total number of symbols in the specified reel or in all
            reels if no reel is specified.
        calculate_expected_value(silent):
            Calculate the expected total return and expected return for the
            slot machine.
        calculate_average_jackpot(seed_int):
            Calculate the average jackpot amount on payout based on a given
            seed (start amount) integer.
        calculate_rtp(wager):
            Calculate the return to player (RTP) percentage for a given wager.
        stop_reel(reel):
            Stops the specified reel and returns the symbol at the
            stopping position.
        calculate_award_money(wager, results):
            Calculate the award money based on the wager and the results of
            the reels.
        make_friendly_event_name(event_name):
            Make a friendly event name from the event name.
        """
    # region Slot config

    def __init__(self, file_name: str = "data/slot_machine.json") -> None:
        """
        Initializes the SlotMachine class with the given configuration file.

        Args:
            file_name: The name of the slot machine configuration file.
                Defaults to "data/slot_machine.json".

        Attributes:
            file_name: The name of the slot machine configuration file
            configuration: The loaded configuration for the slot machine
            _reels: The loaded reels for the slot machine
            _probabilities: The calculated probabilities for each event
            _jackpot: The current jackpot amount
            _fees: The fees associated with the slot machine
        """
        Coin: str = g.Coin
        print("Starting the slot machines...")
        self.file_name: str = file_name
        attributes_set = False
        while attributes_set is False:
            try:
                self.configuration: SlotMachineConfig = (
                    self.load_config())
                self._reels: Reels = self.load_reels()
                # self.emoji_ids: Dict[str, int] = (
                #     cast(Dict[str, int], self.configuration["emoji_ids"]))
                self._probabilities: Dict[str, Float] = (
                    self.calculate_all_probabilities())
                self._jackpot: int = self.load_jackpot()
                self._fees: dict[str, int | float] = self.configuration.fees
                self.header: str = f"### {Coin} Slot Machine"
                self.next_bonus_wait_seconds: int = (
                    self.configuration.new_bonus_wait_seconds)
                self.starting_bonus_die_enabled: bool = (
                    self.configuration.starting_bonus_die_enabled)
                attributes_set = True
            except KeyError as e:
                print("ERROR: "
                      f"Missing key in slot machine configuration: {e}\n"
                      "The slot machine configuration file will be replaced "
                      "with template values.")
                self.create_config()

        print("Slot machines started.")

    def load_reels(self) -> Reels:
        """
        Loads the reels configuration from the bot's configuration file.

        Returns:
            The reels configuration.
        """
        # print("Getting reels...")
        self.configuration = self.load_config()
        reels: Reels = self.configuration.reels
        return reels

    @property
    def reels(self) -> Reels:
        """
        Returns the current state of the reels.

        Returns:
            Reels: The current state of the reels.
        """
        return self._reels

    @reels.setter
    def reels(self, value: Reels) -> None:
        """
        Sets the reels value and updates the configuration.

        Args:
            value: The new value for the reels.
        """
        self._reels = value
        self.configuration.reels = self._reels
        self.save_config()

    @property
    def probabilities(self) -> Dict[str, Float]:
        """
        Calculate and return the probabilities for various outcomes.

        Returns:
            Dict: A dictionary where the keys are event names and the values
                    are their corresponding probabilities.
        """
        return self.calculate_all_probabilities()

    @property
    def jackpot(self) -> int:
        """
        Returns the current jackpot amount.

        Returns:
            int: The current jackpot amount.
        """
        return self._jackpot

    @jackpot.setter
    def jackpot(self, value: int) -> None:
        """
        Sets the jackpot value and updates the configuration.

        Args:
            value (int): The new jackpot value.
        """
        self._jackpot = value
        self.configuration.jackpot_pool = self._jackpot
        self.save_config()

    def load_jackpot(self) -> int:
        """
        Loads the current jackpot pool.

        This method retrieves the jackpot seed from the configuration file
        and compares it to the current jackpot pool. The jackpot pool is
        automatically set to the jackpot seed if the jackpot pool is lower.

        Returns:
            int: The calculated jackpot amount.
        """
        self.configuration = self.load_config()
        combo_events: Dict[str,
                           ReelSymbol] = self.configuration.combo_events
        jackpot_seed: int = combo_events["jackpot"]["fixed_amount"]
        jackpot_pool: int = self.configuration.jackpot_pool
        if jackpot_pool < jackpot_seed:
            jackpot: int = jackpot_seed
        else:
            jackpot: int = jackpot_pool
        return jackpot

    def create_config(self) -> None:
        """
        Creates a template slot machine configuration file.
        This method performs the following steps:
        1. Prints a message indicating the creation of the configuration file.
        2. Creates any missing directories in the file path.
        3. Defines a default configuration for the slot machine, including:
            - Combo events with their respective emoji names, IDs,
                fixed amount payouts, and wager multiplier payouts.
            - Reels with the number of each unique symbol on each reel.
            - Fees for different wager levels.
            - Current jackpot pool amount placeholder (not the seed).
        4. Saves the configuration to the specified file in JSON format.
        5. Prints a message indicating the completion of the configuration
            file creation.
        """
        print("Creating template slot machine configuration file...")
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        makedirs(directories, exist_ok=True)

        # Create the configuration file
        # Default configuration
        # jackpot_pool will automatically be set to the jackpot event's
        # fixed_amount value if the latter is higher than the former
        # TODO Change the names: either "small_win" and "large_win" or "low_win" and "high_win"
        configuration = SlotMachineConfig(
            combo_events={
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
                    "wager_multiplier": 3.0
                },
                "jackpot": {
                    "emoji_name": "",
                    "emoji_id": 0,
                    "fixed_amount": 100,
                    "wager_multiplier": 1.0
                }
            },
            reels={
                'reel1': {
                    'high_win': 6,
                    'jackpot': 1,
                    'lose_wager': 2,
                    'medium_win': 10,
                    'small_win': 1
                },
                'reel2': {
                    'high_win': 6,
                    'jackpot': 1,
                    'lose_wager': 2,
                    'medium_win': 10,
                    'small_win': 1
                },
                'reel3': {
                    'high_win': 6,
                    'jackpot': 1,
                    'lose_wager': 2,
                    'medium_win': 10,
                    'small_win': 1
                }
            },
            fees={
                "high_wager_jackpot": 0.01,
                "high_wager_main": 0.19,
                "low_wager_jackpot": 1,
                "low_wager_main": 0.4,
                "lowest_wager_jackpot": 0,
                "lowest_wager_main": 1,
                "medium_wager_jackpot": 0.01,
                "medium_wager_main": 0.29
            },
            reel_spin_emojis={
                'spin1': {
                    'emoji_name': "",
                    'emoji_id': 0
                },
                'spin2': {
                    "emoji_name": "",
                    'emoji_id': 0
                },
                'spin3': {
                    "emoji_name": "",
                    "emoji_id": 0
                }
            },
            jackpot_pool=0,
            new_bonus_wait_seconds=86400,
            starting_bonus_die_enabled=False
        )
        # Save the configuration to the file
        with open(self.file_name, "w", encoding="utf-8") as file:
            file.write(configuration.model_dump_json(indent=4))
        print("Template slot machine configuration file created.")

    def load_config(self) -> SlotMachineConfig:
        """
        Loads the slot machine configuration from a JSON file.
        If the configuration file does not exist, it creates a default
        configuration file.

        Returns:
            SlotMachineConfig: The loaded slot machine configuration.
        """
        file_exists: bool = exists(self.file_name)
        file_is_empty: bool = file_exists and stat(self.file_name).st_size == 0
        if file_is_empty or not file_exists:
            self.create_config()

        with open(self.file_name, "r", encoding="utf-8") as file:
            try:
                configuration: SlotMachineConfig = (
                    SlotMachineConfig.model_validate_json(file.read()))
            except Exception as e:
                print("WARNING: "
                      f"Failed to load slot machine configuration: {e}")
                self.create_config()
                with open(self.file_name, "r", encoding="utf-8") as file:
                    configuration: SlotMachineConfig = (
                        SlotMachineConfig.model_validate_json(file.read()))
            return configuration

    def save_config(self) -> None:
        """
        Saves the current slot machine configuration to a file.

        This method writes the current configuration stored in
        the `configuration` attribute to a file specified by
        the `file_name` attribute in JSON format.

        Raises:
            IOError: If the file cannot be opened or written to.
        """
        # print("Saving slot machine configuration...")
        with open(self.file_name, "w", encoding="utf-8") as file:
            file.write(self.configuration.model_dump_json(indent=4))
        # print("Slot machine configuration saved.")
    # endregion

    # region Slot probability

    def calculate_reel_symbol_probability(self,
                                          reel: Literal[
                                              "reel1", "reel2", "reel3"],
                                          symbol: str) -> float:
        """
        Calculate the probability of a specific symbol appearing on a
        given reel.

        Args:
            reel: The reel to check for the symbol.
            symbol: The symbol to calculate the probability for.

        Returns:
            float: The probability of the symbol appearing on
                    the specified reel.
        """
        number_of_symbol_on_reel: int = self.reels[reel][symbol]
        total_reel_symbols: int = sum(self.reels[reel].values())
        if total_reel_symbols != 0 and number_of_symbol_on_reel != 0:
            probability_for_reel: float = (
                number_of_symbol_on_reel / total_reel_symbols)
        else:
            probability_for_reel = 0.0
        return probability_for_reel

    def calculate_event_probability(self, symbol: str) -> Float:
        """
        Calculate the overall probability of a given symbol appearing
        across all reels.

        Args:
            symbol: The symbol to calculate the probability for.
        Returns:
            Float: The overall probability of the symbol appearing across
                    all reels.
        """
        # TODO Ensure it's still working properly
        overall_probability: Float = Float(1.0)
        for r in self.reels:
            r = (
                cast(Literal['reel1', 'reel2', 'reel3'], r))
            probability_for_reel: float = (
                self.calculate_reel_symbol_probability(r, symbol))

            overall_probability = (
                cast(Float, Mul(overall_probability, probability_for_reel)))
        return overall_probability

    def calculate_losing_probabilities(self) -> tuple[Float, Float]:
        """
        Calculate the probabilities of losing the entire wager, and the
        probability of not getting any symbols to match (standard lose).

        Returns:
            tuple[Float, Float]: A tuple containing:
                - any_lose_probability (Float): The probability of losing by
                    either not getting any symbols to match or getting the
                    "lose_wager" symbol combo.
                - standard_lose_probability (Float): The probability of losing
                    by not getting any symbols to match.
        """
        # TODO Ensure it's still working properly
        # print("Calculating chance of losing...")

        # No symbols match
        standard_lose_probability: Float | Mul = Float(1.0)

        # Either lose_wager symbols match or no symbols match
        any_lose_probability: Float | Mul = Float(1.0)

        # Take the symbols from the first reel
        # (expecting all reels to have the same symbols)
        symbols: List[str] = [symbol for symbol in self.reels["reel1"]]
        symbols_no_match_probability: Float | Add
        symbols_match_probability: Float
        for symbol in symbols:
            symbols_match_probability = (
                self.calculate_event_probability(symbol))
            symbols_no_match_probability = (
                Add(Integer(1) - symbols_match_probability))
            standard_lose_probability = (
                Mul(standard_lose_probability, symbols_no_match_probability))
            if symbol != "lose_wager":
                any_lose_probability = (
                    Mul(any_lose_probability, symbols_no_match_probability))
        return (cast(Float, any_lose_probability),
                cast(Float, standard_lose_probability))

    def calculate_all_probabilities(self) -> Dict[str, Float]:
        """
        Calculate the probabilities for all possible outcomes in
        the slot machine.

        This method loads the reels, calculates the probability for each
        symbol on the first reel (presuming all reels will have the same unique
        symbols, whether in the same or different amounts), and then calculates
        the probabilities for losing and winning events.

        Returns:
            Dict: A dictionary where the keys are the event names
                    (i.e., symbol combos, "standard_lose", "any_lose", "win")
                    and the values are their respective probabilities.
        """
        # TODO Ensure it's still working correctly now after using TypedDicts
        # self.reels = self.load_reels()
        probabilities: Dict[str, Float] = {}
        for symbol in self.reels["reel1"]:
            probability: Float = self.calculate_event_probability(symbol)
            probabilities[symbol] = probability
        any_lose_probability: Float
        standard_lose_probability: Float
        any_lose_probability, standard_lose_probability = (
            self.calculate_losing_probabilities())
        probabilities["standard_lose"] = standard_lose_probability
        probabilities["any_lose"] = any_lose_probability
        probabilities["win"] = cast(Float, Integer(1) - any_lose_probability)
        return probabilities
    # endregion

    # region Slot count
    def count_symbols(self, reel: str | None = None) -> int:
        """
        Count the total number of symbols in the specified reel or in all reels
        if no reel is specified.

        Args:
            reel: The name of the reel to count symbols from. 
                    If None, counts symbols from all reels. Otherwise it's
                    expected to be 'reel1', 'reel2', or 'reel3'.

        Returns:
            int: The total number of symbols in the specified reel or in
            all reels.
        """
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
    def calculate_expected_value(self,
                                 silent: bool = False
                                 ) -> tuple[Piecewise, Piecewise]:
        """
        Calculate the expected total return and expected return for the slot
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
        which makes the EV different for different wager sizes.
        Therefore, we express EV as a piecewise function.
        Each piece expresses the EV (ETR or ER) for a specific wager range

        Terms:
        - Expected value (EV): The average value of a random variable over
            many trials.
        - Wager (or stake): The amount of coins the player inserts into the
            machine each spin; a number that decides the fee and that the
            multiplier events are based on.
        - Jackpot: A prize that grows with each spin until someone wins it
        - Jackpot seed: The amount that the jackpot starts at (and gets reset
            to after someone wins the jackpot).
        - Total return (TR): The gross return amount that the player gets back
            (this in itself does not tell us if the player made a profit or
            loss).
        - Return (R): The net amount that the player gets back; the gain or 
            loss part of the total return money; the total return minus the
            wager.
        - Expected total return (ETR): The average total return over
            many plays; the expected value of the total return.
        - Expected return (ER): The average return (gain or loss) over many
            plays; the expected value of the return.
        - Piecewise function: A function that is defined by
            several subfunctions (used here to express ETR and ER with
            different fees for different wager ranges).

        Symbolic representation:
        - W: Wager
        - k: Wager multiplier
        - x: Fixed amount payout
        - f1k: Main fee wager multiplier
        - f1x: Main fee fixed amount
        - f2k: Jackpot fee wager multiplier
        - f2x: Jackpot fee fixed amount
        - j: Jackpot average

        Args:
        - silent: If True, the function will not print anything to the console.
        - standard_fee_fixed_amount: A fixed amount that is subtracted from the
            player's total return for each spin.
        - standard_fee_wager_multiplier: A percentage of the player's wager
            that is subtracted from the player's total return for each spin,
            and added to the jackpot pool.
        - jackpot_fee_fixed_amount: A fixed amount that is subtracted from the
            player's total return for each spin, and added to the jackpot pool.
        """

        def print_if_not_silent(*args: Any, **kwargs: Any) -> None:
            """
            Wrapper for print() that only prints if the "silent" parameter
            is False.
            """
            if not silent:
                print(*args, **kwargs)

        # Load configuration and calculate probabilities
        self.configuration = self.load_config()
        probabilities: Dict[str, Float] = self.calculate_all_probabilities()
        events: KeysView[str] = probabilities.keys()
        combo_events: Dict[str, ReelSymbol] = (
            self.configuration.combo_events)

        # Symbol
        W: Expr = symbols('W')  # wager

        def calculate_piece_ev(
                standard_fee_fixed_amount: Integer = Integer(0),
                standard_fee_wager_multiplier: Float = Float(0.0),
                jackpot_fee_fixed_amount: Integer = Integer(0),
                jackpot_fee_wager_multiplier: Float = Float(0.0)
        ) -> tuple[Add, Add]:
            """
            Calculate the *expected total return* and *expected return*
            with the fees specified with the parameters.

            Args:
                - standard_fee_fixed_amount: The fixed amount of the
                    standard fee.
                - standard_fee_wager_multiplier: The multiplier for the
                     standard fee based on the wager.
                - jackpot_fee_fixed_amount: The fixed amount of the
                    jackpot fee.
                - jackpot_fee_wager_multiplier: The multiplier for the
                    jackpot fee based on the wager.

                Returns:
                - tuple: A tuple containing the expected total return and
                            the expected return.
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
            p_event_float: Float
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
                p_event_float: Float = probabilities[event]
                p_event = Float(p_event_float)
                print_if_not_silent(f"Event probability: {p_event_float}")
                if p_event_float == 0.0:
                    continue
                if event == "jackpot" and not no_jackpot_mode:
                    # If the player pays the coin jackpot fee
                    # and wins the jackpot,
                    # he ends up with his wager minus the standard fee minus
                    # the jackpot fee, plus the jackpot
                    #
                    # Variables
                    fixed_amount_int = combo_events[event]["fixed_amount"]
                    jackpot_seed: int = fixed_amount_int
                    print_if_not_silent(f"Jackpot seed: {jackpot_seed}")
                    jackpot_average: Rational = (
                        self.calculate_average_jackpot(
                            seed_int=jackpot_seed))
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
                    print_if_not_silent(
                        f"Event total return: {event_total_return} "
                        "[(W * k) + j - (W * f1k) - (W * f2k) - f1x - f2x]")
                    event_return = Add(
                        event_total_return,
                        -W)
                    # This event's contributions to the *expected total return*
                    piece_expected_total_return_contribution = (
                        Mul(p_event, event_total_return))
                    message_content: str
                    message_content = (
                        "Expected total return contribution: "
                        f"{piece_expected_total_return_contribution}")
                    print_if_not_silent(message_content)
                    # Remove variables with common names to
                    # prevent accidental use
                    del message_content
                    # This event's contribution to the *expected return*
                    piece_expected_return_contribution = (
                        Mul(p_event, event_return))
                    print_if_not_silent(f"Event return: {event_return} "
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
                    fixed_amount_int = combo_events[event]["fixed_amount"]
                    wager_multiplier_float = (
                        combo_events[event]["wager_multiplier"])
                wager_multiplier = Float(wager_multiplier_float)
                print_if_not_silent(
                    f"Multiplier (k): {wager_multiplier_float}")
                fixed_amount = Integer(fixed_amount_int)
                print_if_not_silent(f"Fixed amount (x): {fixed_amount_int}")

                if event == "lose_wager":
                    # If the player gets the lose_wager combo
                    # he ends up with nothing
                    # No fees are subtracted
                    #
                    # Event total return calculation
                    event_total_return = Integer(0)
                    print_if_not_silent(
                        f"Event total return: {event_total_return} [0]")
                else:
                    # Some non-default events, like
                    # where wager multiplier >= 0.0
                    # and fixed amount >= 0, are not handled
                    #
                    # Calculations
                    event_total_return = Add(
                        Mul(W, wager_multiplier),
                        fixed_amount,
                        -Mul(W, standard_fee_wager_multiplier),
                        -Mul(W, jackpot_fee_wager_multiplier),
                        -standard_fee_fixed_amount,
                        -jackpot_fee_fixed_amount)
                    print_if_not_silent(
                        f"Event total return: {event_total_return} "
                        "[(W * k) + x - (W * f1k) - (W * f2k) - f1x - f2x]")
                event_return = Add(event_total_return, -W)
                print_if_not_silent(
                    f"Event return: {event_return} "
                    "[total return - W]")
                piece_expected_total_return_contribution = (
                    Mul(p_event, event_total_return))
                message_content = (
                    "Expected total return contribution: "
                    f"{piece_expected_total_return_contribution}")
                print_if_not_silent(message_content)
                del message_content
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
        self._reels = self.load_reels()
        self._fees = self.configuration.fees
        # Main fee
        lowest_wager_main_fee: Integer = Integer(
            self._fees["lowest_wager_main"])
        low_wager_main_fee: Float = Float(self._fees["low_wager_main"])
        medium_wager_main_fee: Float = Float(self._fees["medium_wager_main"])
        high_wager_main_fee: Float = Float(self._fees["high_wager_main"])
        # Jackpot fee
        lowest_wager_jackpot_fee: Integer = Integer(
            self._fees["lowest_wager_jackpot"])
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
                standard_fee_fixed_amount=lowest_wager_main_fee,
                jackpot_fee_fixed_amount=lowest_wager_jackpot_fee),
            "low_wager": calculate_piece_ev(
                standard_fee_wager_multiplier=low_wager_main_fee,
                jackpot_fee_fixed_amount=low_wager_jackpot_fee),
            "medium_wager": calculate_piece_ev(
                standard_fee_wager_multiplier=medium_wager_main_fee,
                jackpot_fee_wager_multiplier=medium_wager_jackpot_fee),
            "high_wager": calculate_piece_ev(
                standard_fee_wager_multiplier=high_wager_main_fee,
                jackpot_fee_wager_multiplier=high_wager_jackpot_fee)
        }

        # Remember to also change the help message if you change the conditions
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
    def calculate_average_jackpot(self, seed_int: int) -> Rational:
        """
        Calculate the average jackpot amount on payout
        based on a given seed (start amount) integer.

        Args:
        seed_int -- The starting amount of the jackpot pool
        """
        seed: Integer = Integer(seed_int)
        # 1 coin is added to the jackpot for every spin
        contribution_per_spin: Integer = Integer(1)
        jackpot_probability: Float = (
            self.calculate_all_probabilities()["jackpot"])
        average_spins_to_win = Rational(Integer(1), jackpot_probability)
        jackpot_cycle_growth = (
            Mul(contribution_per_spin, average_spins_to_win))
        # min + max / 2
        mean_jackpot = Rational(Add(Integer(0) + jackpot_cycle_growth))
        # (0 + jackpot_cycle_growth) / 2
        average_jackpot: Rational = cast(Rational, Add(seed, mean_jackpot))
        return average_jackpot
    # endregion

    # region Slot RTP
    def calculate_rtp(self, wager: Integer, silent: bool = False) -> Float:
        """
        Calculate the Return to Player (RTP) based on the given wager.

        Args:
            wager: The amount wagered.

        Returns:
            Float: The RTP value as a decimal.
        """
        # IMPROVE Fix error reported by Pylance
        expected_total_return_expression: Piecewise = (
            self.calculate_expected_value(silent=True))[0]
        expected_total_return: Piecewise = (
            cast(Piecewise,
                 expected_total_return_expression
                 .subs(  # pyright: ignore [reportUnknownMemberType]
                     symbols('W'), wager)))
        if not silent:
            print("Expected total return "
                  f"(W = {wager}): {expected_total_return}")
        rtp = Rational(expected_total_return, wager)
        rtp_decimal: Float = cast(Float, rtp.evalf())
        if not silent:
            print(f"RTP: {rtp}")
            print(f"RTP decimal: {rtp_decimal}")
        return rtp_decimal
    # endregion

    # region Slot stop reel
    def stop_reel(self, reel: Literal["reel1", "reel2", "reel3"]) -> str:
        """
        Stops the specified reel and returns the symbol at the
        stopping position.

        Args:
            reel: The reel to stop.

        Returns:
            str: The symbol at the stopping position.
        """
        # Create a list with all units of each symbol type on the reel
        reel_symbols: List[str] = []
        for s in self.reels[reel]:
            reel_symbols.extend([s] * self.reels[reel][s])
        # Randomly select a symbol from the list
        symbol: str = random.choice(reel_symbols)
        return symbol
    # endregion

    # region Slot win money
    def calculate_award_money(self,
                              wager: int,
                              results: ReelResults
                              ) -> tuple[SlotEvent, int]:
        """
        Calculate the award money based on the wager and the results of
        the reels. This does not include the fees. It is only the money
        that a combo event would award the player. It will not return a
        negative value.
        It also returns the internal name of the event and a user-friendly name
        of the event.
        Args:
            wager: The amount of money wagered.
            results: The results of the reels, containing associated
            combo events.
        Returns:
            tuple: A tuple containing:
                - event: A SlotEvent object representing the event.
                - win_money_rounded: The amount of money won, rounded down to
                    the nearest integer.
        """
        if (not (
            results["reel1"]["associated_combo_event"].keys()
            == results["reel2"]["associated_combo_event"].keys()
                == results["reel3"]["associated_combo_event"].keys())):
            event = SlotEvent(
                name="standard_lose",
                name_friendly="No win",
                fixed_amount=0,
                wager_multiplier=0.0,
            )
            return (event, 0)

        # IMPROVE Code is repeated from slots() function
        fees_dict: Dict[str, int | float] = self.configuration.fees
        low_wager_main_fee: int = (
            cast(int, fees_dict["low_wager_main"]))
        low_wager_jackpot_fee: int = (
            cast(int, fees_dict["low_wager_jackpot"]))
        jackpot_fee_paid: bool = (
            wager >= (low_wager_jackpot_fee + low_wager_main_fee))
        no_jackpot_mode: bool = False if jackpot_fee_paid else True
        # Since associated_combo_event is a dict with only one key,
        # we can get the key name (thus event name) by getting the first key
        event_name: str = next(
            iter(results["reel1"]["associated_combo_event"]))
        # print(f"event_name: {event_name}")
        wager_multiplier: float = (
            results["reel1"]["associated_combo_event"][event_name]
            ["wager_multiplier"])
        fixed_amount_payout: int = (
            results["reel1"]["associated_combo_event"][event_name]
            ["fixed_amount"])
        # print(f"event_multiplier: {wager_multiplier}")
        # print(f"fixed_amount_payout: {fixed_amount_payout}")
        event_name_friendly: str = ""
        win_money: float = 0.0
        win_money_rounded: int = 0
        if event_name == "lose_wager":
            event_name_friendly = "Lose stake"
            event = SlotEvent(
                name=event_name,
                name_friendly=event_name_friendly,
                fixed_amount=fixed_amount_payout,
                wager_multiplier=wager_multiplier,
            )
            return (event, 0)
        elif event_name == "jackpot":
            if no_jackpot_mode:
                event_name = "jackpot_fail"
                event_name_friendly = "No Jackpot"
                win_money_rounded = 0
            else:
                event_name_friendly = "JACKPOT"
                win_money_rounded = self.jackpot
            event = SlotEvent(
                name=event_name,
                name_friendly=event_name_friendly,
                fixed_amount=fixed_amount_payout,
                wager_multiplier=wager_multiplier,
            )
            return (event, win_money_rounded)
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
        event = SlotEvent(
            name=event_name,
            name_friendly=event_name_friendly,
            fixed_amount=fixed_amount_payout,
            wager_multiplier=wager_multiplier,
        )
        return (event, win_money_rounded)
    # endregion

    # region Friendly event name
    def make_friendly_event_name(self, event_name: str) -> str:
        """
        Creates a user-friendly name for an event.

        The function handles specific event names such as "lose_wager"
        and "jackpot" with predefined friendly names. For other events, it
        constructs a friendly name based on the wager multiplier
        and fixed amount payout from the configuration.

        This code is copied from calculate_award_money().

        Args:
            event_name: The internal name of the event.

        Returns:
            str: A user-friendly version of the event name.
        """
        combo_events: Dict[str,
                           ReelSymbol] = self.configuration.combo_events
        wager_multiplier: float = (
            combo_events[event_name]["wager_multiplier"])
        fixed_amount_payout: int = (
            combo_events[event_name]["fixed_amount"])
        event_name_friendly: str = ""
        if event_name == "lose_wager":
            event_name_friendly = "Lose stake"
            return event_name_friendly
        elif event_name == "jackpot":
            event_name_friendly = "JACKPOT"
            return event_name_friendly
        event_multiplier_friendly: str
        event_multiplier_floored: int = math.floor(wager_multiplier)
        if wager_multiplier == event_multiplier_floored:
            event_multiplier_friendly = str(int(wager_multiplier))
        else:
            event_multiplier_friendly = str(wager_multiplier)
        event_name_friendly += "{}X".format(event_multiplier_friendly)
        if fixed_amount_payout > 0:
            event_name_friendly = "+{}".format(fixed_amount_payout)
        return event_name_friendly
    # endregion

    # region Slot message
    def make_message(self,
                     text_row_1: str | None = None,
                     text_row_2: str | None = None,
                     reels_row: str | None = None) -> str:
        """
        Constructs a message that imitates a slot machine.

        Args:
            text_row_1: The text for the first row.
            text_row_2: The text for the second row.
            reels_row: The text for the reels row.

        Returns:
            str: The formatted message string.
        """
        # Workaround for Discord stripping trailing whitespaces
        empty_space: LiteralString = "\N{HANGUL FILLER}" * 11
        if text_row_1 is None:
            text_row_1 = empty_space
        if text_row_2 is None and reels_row is not None:
            text_row_2 = empty_space

        if reels_row:
            message_content: str = (f"{self.header}\n"
                                    f"{text_row_1}\n"
                                    f"{text_row_2}\n"
                                    f"{empty_space}\n"
                                    f"{reels_row}\n"
                                    f"{empty_space}")
        else:
            if text_row_2 is None:
                message_content = (f"{self.header}\n"
                                   f"{text_row_1}")
            else:
                message_content = (f"{self.header}\n"
                                   f"{text_row_1}\n"
                                   f"{text_row_2}")
        return message_content
    # endregion


def reinitialize_slot_machine() -> None:
    """
    Initializes the slot machine.
    """
    global slot_machine
    slot_machine = SlotMachine()
