# region Imports
import pandas as pd
from os import walk
from os.path import exists, basename
from os.path import exists
from hashlib import sha256
from typing import Dict
# endregion

# region Decrypted tx


class DecryptedTransactionsSpreadsheet:
    """
    Decrypts the transactions spreadsheet.
    """

    def __init__(self) -> None:
        self.decrypted_spreadsheet_file_name: str = (
            "data/transactions_decrypted.tsv")
        self.encrypted_spreadsheet_file_name: str = (
            "data/transactions.tsv")
        self.save_data_directory_name: str = (
            "data/save_data")

    def decrypt(self) -> None:
        """
        Decrypts the transactions spreadsheet.
        """
        if not exists(self.encrypted_spreadsheet_file_name):
            print("Encrypted transactions spreadsheet not found.")
            return None
        if not exists(self.save_data_directory_name):
            print("Save data directory not found.")
            return None

        print("Decrypting transactions spreadsheet...")
        user_names: Dict[str, str] = {}
        for subdir, _, _ in walk(self.save_data_directory_name):
            try:
                user_id: int = int(basename(subdir))
                save_data = UserSaveData(user_id)
                user_name: str = save_data.user_name
                user_id_hashed: str = sha256(str(user_id).encode()).hexdigest()
                user_names[user_id_hashed] = user_name
            except Exception as e:
                print(f"ERROR: Error getting save data: {e}")
                continue

        # Load the data from the file
        transactions: pd.DataFrame = pd.read_csv(  # type: ignore
            self.encrypted_spreadsheet_file_name, sep="\t")
        # Replace hashed user IDs with user names
        transactions["Sender"] = (
            transactions["Sender"].map(user_names))  # type: ignore
        transactions["Receiver"] = (
            transactions["Receiver"].map(user_names))  # type: ignore
        # Save the decrypted transactions to a new file
        transactions.to_csv(
            self.decrypted_spreadsheet_file_name, sep="\t", index=False)
        print("Decrypted transactions spreadsheet saved to file.")
# endregion