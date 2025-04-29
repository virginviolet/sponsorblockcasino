# region Imports
# Local
import core.global_state as g
# endregion

# region Function
def apply_donation_reward() -> None:
    if g.donation_goal is None:
        raise RuntimeError("Donation goal is not set.")
    if g.donation_goal.reward_value is None:
        raise RuntimeError("reward_value is not set.")
    assert g.configuration is not None, (
        "g.configuration has not been initialized.")
    if (g.donation_goal.reward_setting
            == "leaderboard_slots_highest_win_blocked"):
        g.configuration.leaderboard_slots_highest_win_blocked = (
            g.donation_goal.reward_value)
        g.leaderboard_slots_highest_win_blocked = g.donation_goal.reward_value
        print("leaderboard_slots_highest_win_blocked set "
              f"to {g.donation_goal.reward_value}")
# endregion