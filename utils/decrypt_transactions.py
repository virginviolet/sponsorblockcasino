# region Imports
import os
import pandas as pd
from os.path import exists, basename
from pathlib import Path
from hashlib import sha256
from typing import Dict
from models.user_save_data import UserSaveData
from utils.get_project_root import get_project_root
from utils.formatting import format_timestamp
# endregion

# region Decrypted tx


class DecryptedTransactionsSpreadsheet:
    """
    Decrypts the transactions spreadsheet.
    """

    def __init__(self, time_zone: str | None = None) -> None:
        project_root: Path = get_project_root()
        decrypted_spreadsheet_full_path: Path = (
            project_root / "data" / "transactions_decrypted.tsv")
        self.decrypted_spreadsheet_path: Path = (
            decrypted_spreadsheet_full_path.relative_to(project_root))
        encrypted_spreadsheet_full_path: Path = (
            project_root / "data" / "transactions.tsv")
        self.encrypted_spreadsheet_path: Path = (
            encrypted_spreadsheet_full_path.relative_to(project_root))
        save_data_dir_full_path: Path = (
            project_root / "data" / "save_data")
        self.save_data_dir_path: Path = (
            save_data_dir_full_path.relative_to(project_root))
        self.time_zone: str | None = time_zone

    def decrypt(self,
                user_id: int | None = None,
                user_name: str | None = None) -> None:
        """
        Decrypts the transactions spreadsheet.
        """
        if not exists(self.encrypted_spreadsheet_path):
            print("Encrypted transactions spreadsheet not found.")
            return None
        if not exists(self.save_data_dir_path):
            print("Save data directory not found.")
            return None

        print("Decrypting transactions spreadsheet...")
        user_names: Dict[str, str] = {}
        for subdir, _, _ in os.walk(self.save_data_dir_path):
            try:
                subdir_user_id: int = int(basename(subdir))
                subdir_save_data = UserSaveData(subdir_user_id)
                subdir_user_name: str = subdir_save_data.user_name
                subdir_user_id_hashed: str = (
                    sha256(str(subdir_user_id).encode()).hexdigest())
                user_names[subdir_user_id_hashed] = subdir_user_name
            except Exception as e:
                print(f"ERROR: Error getting save data: {e}")
                continue

        # Load the data from the file
        transactions: pd.DataFrame = pd.read_csv(  # type: ignore
            self.encrypted_spreadsheet_path, sep="\t")

        # IMPROVE if user_id and user_name
        # Only keep transactions that involve the specified user as
        # identified by the ID or name

        if user_id:
            # Only keep transactions that involve the specified user
            user_id_hashed: str = sha256(str(user_id).encode()).hexdigest()
            transactions = transactions[
                (transactions["Sender"] == user_id_hashed) |
                (transactions["Receiver"] == user_id_hashed)]

        # Replace hashed user IDs with user names
        transactions["Sender"] = (
            transactions["Sender"].map(user_names))  # type: ignore
        transactions["Receiver"] = (
            transactions["Receiver"].map(user_names))  # type: ignore
        # Replace unix timestamps
        transactions["Time"] = (
            transactions["Time"].map(format_timestamp))  # type: ignore

        if user_name:
            # Only keep transactions that involve the specified user
            transactions = transactions[
                (transactions["Sender"] == user_name) |
                (transactions["Receiver"] == user_name)]

        # Save the decrypted transactions to a new file
        transactions.to_csv(
            self.decrypted_spreadsheet_path, sep="\t", index=False)

        print("Decrypted transactions spreadsheet saved to file.")
# endregion
