# region Imports
# Standard Library
from datetime import datetime

# Third party
import pytz
from core.global_state import coin, coins
# endregion

# region Coin label


def format_coin_label(number: int) -> str:
    """
    Returns the appropriate label for the given number of coins.

    Args:
        number (int): The number of coins.

    Returns:
        str: "coin" if the number is 1 or -1, otherwise "coins".
    """
    if number == 1 or number == -1:
        return coin
    else:
        return coins
# endregion


# region Format timestamp
def format_timestamp(timestamp: float, time_zone: str | None = None) -> str:
    """
    Formats a Unix timestamp to a localized human-readable format.

    Args:
        timestamp: The Unix timestamp to format.
    Returns:
        str: The formatted timestamp.
    """
    timestamp_friendly: str
    if time_zone is None:
        # Use local time zone
        timestamp_friendly = (
            datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"))
    else:
        # Convert Unix timestamp to datetime object
        timestamp_dt: datetime = (
            datetime.fromtimestamp(timestamp, pytz.utc))

        # Adjust for time zone
        timestamp_dt = (
            timestamp_dt.astimezone(pytz.timezone(time_zone)))

        # Format the timestamp
        timestamp_friendly = (
            timestamp_dt.strftime("%Y-%m-%d %H:%M:%S"))

    return timestamp_friendly
# endregion