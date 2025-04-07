# region Imports

# Third party
import lazyimports
from discord.ext.commands import Bot  # type: ignore

# Standard library
import signal
import asyncio
from sys import exit as sys_exit
from typing import NoReturn
with lazyimports.lazy_imports(
        "subprocess::Popen"):
      from subprocess import Popen

# Local
import core.global_state as g
with lazyimports.lazy_imports(
      "sponsorblockchain.start_sponsorblockchain:waitress_process"):
    from sponsorblockchain.start_sponsorblockchain import waitress_process
# endregion

# region Terminate bot


async def terminate_bot() -> NoReturn:
    """
    Closes the bot, shuts down the blockchain server, and exits the script.

    Returns:
        NoReturn: This function does not return any value.
    """
    assert isinstance(g.bot, Bot), (
        "bot is not initialized")
    assert isinstance(waitress_process, Popen), (
        "waitress_process is not initialized")
    print("Closing bot...")
    await g.bot.close()
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