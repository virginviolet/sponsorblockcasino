from commands.groups.aml import aml_group
from commands.groups.mining.mining_main import mining_group
from commands.groups.slots.slots_main import slots_group
from commands.groups.leaderboard.leaderboard_main import (
    leaderboard_group,
    leaderboard_slots_group)

__all__: list[str] = ["aml_group",
                      "mining_group",
                      "slots_group",
                      "leaderboard_group",
                      "leaderboard_slots_group"]
