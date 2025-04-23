# region Imports
# Standard library
import json
from os.path import exists
from os import makedirs
from os.path import exists
from typing import (Dict, List)

# Third party
from discord import (Guild, Interaction, Role, utils)

# Local
from sponsorblockcasino_types import TransactionRequest
# endregion

# region Transfers waiting


class TransfersWaitingApproval:
    """
    Handles transfers waiting for approval.
    """

    def __init__(self) -> None:
        self.file_name: str = "data/transfers_waiting_approval.json"
        self.transfers: List[TransactionRequest] = self.load()

    def load(self) -> List[TransactionRequest]:
        """
        Loads the transfer requests from the JSON file.
        """
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        makedirs(directories, exist_ok=True)
        if not exists(self.file_name):
            print("Transfers waiting approval file not found.")
            return []

        # Load the data from the file
        with open(self.file_name, "r") as file:
            transfers_json: Dict[str, List[TransactionRequest]] = (
                json.load(file))
            transfers: List[TransactionRequest] = (
                transfers_json.get("transfers", []))
            if len(transfers) == 0:
                print("No transfers waiting approval found.")
        return transfers

    def add(self, transfer: TransactionRequest) -> None:
        """
        Add a transfer to the list of transfers waiting for approval.
        """
        self.transfers.append(transfer)
        with open(self.file_name, "w") as file:
            json.dump({"transfers": self.transfers}, file)

    def remove(self, transfer: TransactionRequest) -> None:
        """
        Remove a transfer from the list of transfers waiting for approval.
        """
        if transfer in self.transfers:
            self.transfers.remove(transfer)
            with open(self.file_name, "w") as file:
                json.dump({"transfers": self.transfers}, file)
            # print("Transfer removed from the approval list.")

# endregion

# region Reinitialize


def reinitialize_transfers_waiting_approval() -> None:
    """
    Initializes the transfers waiting for approval.
    """
    global transfers_waiting_approval
    transfers_waiting_approval = TransfersWaitingApproval()
# endregion

# region AML Officer


def get_aml_officer_role(interaction: Interaction) -> None | Role:
    guild: Guild | None = interaction.guild
    if guild is None:
        print("ERROR: Guild is None.")
        return
    aml_officer: Role | None = None
    role_names: List[str] = [
        "Anti-Money Laundering Officer",
        "Anti-money laundering officer",
        "anti_money_laundering_officer",
        "AML Officer", "AML officer" "aml_officer"]
    for role_name in role_names:
        aml_officer = utils.get(guild.roles, name=role_name)
        if aml_officer is not None:
            break
    return aml_officer
# endregion
