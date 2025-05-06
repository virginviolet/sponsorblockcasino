# Imports
# Third party
import lazyimports

# Local
# Import all core components
from .global_state import (
    waitress_process,
    log,
    blockchain,
    slot_machine,
    grifter_suppliers,
    transfers_waiting_approval,
    decrypted_transactions_spreadsheet,
    bot,
    coin,
    Coin,
    coins,
    Coins,
    coin_emoji_id,
    coin_emoji_name,
    casino_house_id,
    administrator_id,
    all_channel_checkpoints,
    casino_channel_id,
    blockchain_name,
    Blockchain_name,
    about_command_formatted,
    grifter_swap_id,
    sbcoin_id,
    auto_approve_transfer_limit,
    aml_office_thread_id,
    DISCORD_TOKEN,
    per_channel_checkpoint_limit,
    active_slot_machine_players,
    starting_bonus_timeout,
    time_zone
)

with lazyimports.lazy_imports(
        "core.bot:run_bot",
        "core.bot:setup_bot_environment",
        "core.bot:intents"):
    from .bot import (
        run_bot,
        setup_bot_environment,
        intents
    )

# Commented because it causes issue with blockchain extension somehow
# With lazy imports, I would have assumed that the event handlers
# would only get imported after the blockchain extension is imported,
# but that doesn't seem to be the case
# with lazyimports.lazy_imports(
#         ".register_event_handlers:register_event_handlers",
#         ".register_event_handlers:register_commands"):
#     from .register_event_handlers import (
#         register_event_handlers, register_commands)

with lazyimports.lazy_imports(".terminate_bot:terminate_bot"):
    from .terminate_bot import terminate_bot

# Define what symbols are exported when using 'from core import *'
__all__: list[str] = [
    'waitress_process',
    'slot_machine',
    'grifter_suppliers',
    'transfers_waiting_approval',
    'decrypted_transactions_spreadsheet',
    'bot',
    'coin',
    'Coin',
    'coins',
    'Coins',
    'coin_emoji_id',
    'coin_emoji_name',
    'casino_house_id',
    'administrator_id',
    'all_channel_checkpoints',
    'casino_channel_id',
    'blockchain_name',
    'Blockchain_name',
    'about_command_formatted',
    'grifter_swap_id',
    'sbcoin_id',
    'auto_approve_transfer_limit',
    'aml_office_thread_id',
    'DISCORD_TOKEN',
    'per_channel_checkpoint_limit',
    'active_slot_machine_players',
    'starting_bonus_timeout',
    'log',
    'blockchain',
    'run_bot',
    'setup_bot_environment',
    'intents',
    'terminate_bot',
    # 'register_event_handlers',
    # 'register_commands',
    'time_zone'
]