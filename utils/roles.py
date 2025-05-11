# region Imports
# Standard Library
from typing import List, cast

# Third party
from discord import Guild, Interaction, Member, Role, User, utils

# Local
import core.global_state as g

# region Get role


def get_role(interaction: Interaction,
             role_names: List[str] | str) -> Role | None:
    guild: Guild | None = interaction.guild
    if guild is None:
        print("ERROR: guild is None.")
        return None

    requested_role: Role | None = None
    if isinstance(role_names, str):
        role_names_list: List[str] = [role_names]
    else:
        role_names_list = role_names
    for role_name in role_names_list:
        requested_role = utils.get(guild.roles, name=role_name)
        if requested_role is not None:
            break
    return requested_role
# endregion

# region Get Slot Technician
def get_slot_machine_technician_role(interaction: Interaction) -> Role | None:
    role_names: List[str] = [
        "Slot Machine Technician",
        "Slot machine technician",
        "slot machine technician",
        "slot_machine_technician"
    ]
    slot_machine_technician: Role | None = get_role(interaction, role_names)
    return slot_machine_technician

# region Get IT officer


def get_cybersecurity_officer_role(interaction: Interaction) -> Role | None:
    role_names: List[str] = [
        f"{g.Coin} Security Officer", f"{g.Coin} security officer",
        f"{g.Coin} security officer", f"{g.Coin}_security_officer",
        f"{g.Coin} Casino Security Officer",
        f"{g.Coin} Casino security officer",
        f"{g.Coin} Casino security officer",
        f"{g.Coin}_casino_security_officer",
        "Security Officer", "Security officer",
        "security officer", "security_officer",
        "Information Security Officer", "Information security officer",
        "information security officer", "information_security_officer"
        "Computer Security Officer", "Computer security officer",
        "computer security officer", "computer_security_officer",
        "Cybersecurity Officer", "Cybersecurity officer",
        "cybersecurity officer", "cybersecurity_officer"]
    cybersecurity_officer: Role | None = get_role(interaction, role_names)
    # IMPROVE Partial matching if role is not found
    return cybersecurity_officer
# endregion

# region AML Officer


def get_aml_officer_role(interaction: Interaction) -> Role | None:
    role_names: List[str] = [
        "Anti-Money Laundering Officer",
        "Anti-money laundering officer",
        "anti-money laundering officer",
        "anti_money_laundering_officer",
        "AML Officer", "AML officer" "aml_officer"]
    aml_officer: Role | None = get_role(interaction, role_names)
    return aml_officer


def test_invoker_is_aml_officer(interaction: Interaction) -> bool:
    invoker: User | Member = interaction.user
    invoker_roles: List[Role] = cast(Member, invoker).roles
    role_names: List[str] = [
        "Anti-Money Laundering Officer",
        "Anti-money laundering officer",
        "anti_money_laundering_officer",
        "AML Officer", "AML officer" "aml_officer"]
    aml_officer_role: Role | None = None
    for role_name in role_names:
        aml_officer_role = utils.get(invoker_roles, name=role_name)
        if aml_officer_role is not None:
            break
    del invoker, invoker_roles
    if aml_officer_role is None:
        return False
    else:
        return True
# endregion
