# region Imports
# Standard library
import os
from time import time

# Third party
# from pydantic

# Local
from schemas.pydantic_models import (HighScores, SlotsHighScoreWins,
                                     SlotsHighScoreWinEntry)

# endregion

# region Slot machine high scores


class SlotMachineHighScores:
    """
    Class to handle the high scores of the slot machine.
    """

    def __init__(self,
                 file_path: str = (
                     "data/slot_machine_high_scores.json")) -> None:
        self.file_path: str = file_path
        self._high_scores: HighScores = self.load()

    def load(self) -> HighScores:
        """
        Load the high scores from the file.
        """
        file_exists: bool = os.path.exists(self.file_path)
        file_empty: bool = file_exists and os.path.getsize(self.file_path) == 0
        if file_empty or not file_exists:
            # create file if it doesn't exist
            current_time: float = time()
            highest_wins: SlotsHighScoreWins = SlotsHighScoreWins(
                entries=[],
                last_updated=current_time
            )
            high_scores: HighScores = HighScores(
                highest_wins=highest_wins
            )
            with open(self.file_path, "w") as f:
                f.write(high_scores.model_dump_json(indent=4))
            return high_scores
        # load json with pydantic
        try:
            with open(self.file_path, "r") as f:
                high_scores: HighScores = (
                    HighScores.model_validate_json(f.read()))
                return high_scores
        except Exception as e:
            raise Exception(
                f"Error loading high scores: {e}. "
                f"File path: {self.file_path}"
            ) from e

    def add_entry(self,
                  entry: SlotsHighScoreWinEntry) -> None:
        """
        Add an entry to the high scores.
        """
        user_is_new: bool = True
        for i, existing_entry in enumerate(
                self._high_scores.highest_wins.entries):
            if existing_entry.user.id == entry.user.id:
                # update existing entry
                self._high_scores.highest_wins.entries[i] = entry
                user_is_new = False
                break
        if user_is_new:
            self._high_scores.highest_wins.entries.append(entry)
        self._high_scores.highest_wins.last_updated = time()
        with open(self.file_path, "w") as file:
            file.write(self._high_scores.model_dump_json(indent=4))

    def fetch_user_high_score(self,
                              category: str,
                              user_id: int) -> int | None:
        """
        Get the user entry from the high scores.
        """
        if category == "highest_wins":
            for entry in self._high_scores.highest_wins.entries:
                if entry.user.id == user_id:
                    return entry.win_money

    @property
    def high_scores(self) -> HighScores:
        """
        Get the high scores.
        """
        return self._high_scores

    @high_scores.setter
    def high_scores(self, value: HighScores) -> None:
        """
        Set the high scores.
        """
        self._high_scores = value
        self._high_scores.highest_wins.last_updated = time()
        with open(self.file_path, "w") as file:
            file.write(value.model_dump_json(indent=4))


# endregion
