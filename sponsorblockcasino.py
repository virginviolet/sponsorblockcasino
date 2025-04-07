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
# Third party
import lazyimports

# Local
blockchain_extension_register_routes_import: str = (
    "sponsorblockchain_extensions.discord_coin_bot_extension:"
    "register_routes:register_routes")
with lazyimports.lazy_imports(
        "sponsorblockchain.start_sponsorblockchain:start_flask_app_thread",
        "core.bot:setup_bot_environment",
        "core.bot:run_bot",
        "core.register_event_handlers:register_event_handlers",
        "core.register_event_handlers:register_commands"):
    from sponsorblockchain.start_sponsorblockchain import (
        start_flask_app_thread)
    from core.bot import setup_bot_environment, run_bot
    from core.register_event_handlers import (
        register_event_handlers, register_commands)
# endregion

# region Main
if __name__ == "__main__":
    start_flask_app_thread()
    setup_bot_environment()
    register_event_handlers()
    register_commands()
    run_bot()
# endregion

# region To do
# TODO Track reaction removals
# TODO Make leaderboard
# TODO Add casino jobs
# TODO Add more games
# endregion
