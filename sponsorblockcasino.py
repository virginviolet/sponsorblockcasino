"""
Scopes:
- applications.commands
- bot

Permissions:
- Send Messages
- Read Message History

Privileged Gateway Intents:
- Server Members Intent
- Message Content Intent
"""

# region Imports
# Local
# print directory tree
import os
for root, dirs, files in os.walk("."):
    level = root.replace(".", "").count(os.sep)
    indent = " " * 4 * (level)
    print(f"{indent}{os.path.basename(root)}/")
    sub_indent = " " * 4 * (level + 1)
    for f in files:
        print(f"{sub_indent}{f}")
from sponsorblockchain.start_sponsorblockchain import start_flask_app_thread


# endregion


# region Main
if __name__ == "__main__":
    start_flask_app_thread()
    from core.bot import setup_bot_environment
    setup_bot_environment()
    from core.register_event_handlers import (register_event_handlers,
                                              register_commands)
    register_event_handlers()
    register_commands()
    from core.bot import run_bot
    run_bot()
# endregion

# region To do
# TODO Track reaction removals
# TODO Make leaderboard
# TODO Add casino jobs
# TODO Add more games
# endregion
