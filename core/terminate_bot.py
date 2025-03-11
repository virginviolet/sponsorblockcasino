# region Imports
# Standard library
import signal
import asyncio
from sys import exit as sys_exit
from typing import NoReturn

# Third party
from discord.ext.commands import Bot # type: ignore

# Local
from core.global_state import waitress_process, bot
# endregion

# region Terminate bot


async def terminate_bot() -> NoReturn:
    """
    Closes the bot, shuts down the blockchain server, and exits the script.

    Returns:
        NoReturn: This function does not return any value.
    """
    assert isinstance(bot, Bot), "bot is not initialized"
    global waitress_process
    if waitress_process is None:
        raise ValueError("waitress_process is not initialized")
    print("Closing bot...")
    await bot.close()
    print("Bot closed.")
    print("Shutting down the blockchain app...")
    waitress_process.send_signal(signal.SIGTERM)
    waitress_process.wait()
    # print("Shutting down blockchain flask app...")
    # try:
    #     requests.post("http://127.0.0.1:5000/shutdown")
    # except Exception as e:
    #     print(e)
    await asyncio.sleep(1)  # Give time for all tasks to finish
    print("The script will now exit.")
    sys_exit(1)
# endregion