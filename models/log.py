# region Imports
# Standard library
from os.path import exists
from time import time
from datetime import datetime
from os import makedirs

# Third party
import pytz
# endregion

# region Log


class Log:
    """
    Provides functionality for logging events with timestamps to a file.
    For timestamps, the local time zone is used by default, but a different
    time zone can be specified.

    The log cannot be verified or generated from the blockchain.
    Use a validated transactions file for verification (see
    Blockchain.validate_transactions_file()).
    The log is meant to be a local record of interesting events on the server.

    Attributes:
        file_name: The name of the file where transactions are logged.
        time_zone: The time zone to be used for logging. If None, the
                    local time zone is used.
    Methods:
        __init__(file_name = "data/transactions.log", time_zone) -> None:
            Initializes the log file with the specified file name and time zone.
        create(): Creates the necessary directories and an empty log file.
        log(line, timestamp): Logs a line of text with a timestamp to the file.
    """

    def __init__(self,
                 file_name: str = "data/transactions.log",
                 time_zone: str | None = None) -> None:
        """
        Initializes the log file.

        Args:
            file_name: The name of the file where transactions are logged.
                        Defaults to "data/transactions.log".
            time_zone: The time zone to be used for logging. If None, the
                        local time zone is used. Defaults to None.
        """

        print("Initializing log...")
        self.file_name: str = file_name
        self.time_zone: str | None = time_zone
        timestamp: float = time()
        if time_zone is not None:
            self.log(f"The time zone is set to '{time_zone}'.", timestamp)
        else:
            self.log("The time zone is set to the local time zone.", timestamp)
        print("Log initialized.")

    def create(self) -> None:
        """
        Creates the necessary directories and an empty log file.
        This method performs the following steps:
        1. Extracts the directory path from the file name.
        2. Splits the directory path and iterates through each directory.
        3. Checks if each directory exists, and if not, creates it.
        4. Creates an empty log file at the specified file name.
        """
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        for _, directory in enumerate(directories.split("/")):
            if not exists(directory):
                makedirs(directory)

        # Create the log file
        with open(self.file_name, "w"):
            pass

    def format_timestamp(self, timestamp: float) -> str:
        """
        Formats a Unix timestamp to a localized human-readable format.

        Args:
            timestamp: The Unix timestamp to format.
        Returns:
            str: The formatted timestamp.
        """
        if self.time_zone is None:
            # Use local time zone
            timestamp_friendly: str = (
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

        return timestamp_friendly

    def log(self, line: str, timestamp: float) -> None:
        """
        Logs a line of text with a timestamp to a file.
        Args:
            line: The line of text to log.
            timestamp: The Unix timestamp that will be converted to a
                        human-readable format and prepended to the line.
        Returns:
            None
        """

        timestamp_friendly: str = self.format_timestamp(timestamp)

        # Create the log file if it doesn't exist
        if not exists(self.file_name):
            self.create()

        with open(self.file_name, "a") as f:
            timestamped_line: str = f"{timestamp_friendly}: {line}"
            print(timestamped_line)
            f.write(f"{timestamped_line}\n")
# endregion