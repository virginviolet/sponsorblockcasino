# region Imports
# Standard library
import json
from os.path import exists
from os import makedirs
from os.path import exists
from typing import Dict, List

# Third party
from discord import Member, User
from discord.ext.commands import (  # pyright: ignore [reportMissingTypeStubs]
    Bot)
# endregion

# region Grifter Suppliers


class GrifterSuppliers:
    """
    Handels which users are grifter suppliers.
    """

    def __init__(self) -> None:
        self.file_name: str = "data/grifter_suppliers.json"
        # IMPROVE Use hash set instead of list
        self.suppliers: List[int] = self.load()

    def load(self) -> List[int]:
        """
        Loads the grifter suppliers from the JSON file.
        """
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        makedirs(directories, exist_ok=True)
        if not exists(self.file_name):
            print("Grifter suppliers file not found.")
            return []

        # Load the data from the file
        with open(self.file_name, "r") as file:
            suppliers_json: Dict[str, List[int]] = json.load(file)
            suppliers: List[int] = suppliers_json.get("suppliers", [])
            if len(suppliers) == 0:
                print("No grifter suppliers found.")
        return suppliers

    async def add(self, user: User | Member) -> None:
        """
        Add user IDs to the list of grifter suppliers.
        """
        user_name: str = user.name
        user_id: int = user.id
        del user
        if user_id not in self.suppliers:
            self.suppliers.append(user_id)
            print(f"User {user_name} ({user_id}) added "
                  "to the grifter suppliers registry.")
        else:
            print(f"User {user_name} ({user_id}) is already in the"
                  "grifter suppliers registry.")
        with open(self.file_name, "w") as file:
            json.dump({"suppliers": self.suppliers}, file)

    async def replace(self, bot: Bot, user_ids: List[int]) -> None:
        """
        Replace the list of grifter suppliers with a new list.
        """
        print("Replacing grifter suppliers registry...")
        for user_id in user_ids:
            user: User = await bot.fetch_user(user_id)
            user_name: str = user.name
            print(f"User {user_name} ({user_id}) will be added to the "
                  "grifter suppliers registry.")
        self.suppliers = user_ids
        with open(self.file_name, "w") as file:
            json.dump({"suppliers": self.suppliers}, file)
        print("Grifter suppliers registry replaced.")

    def remove(self, user: User | Member) -> None:
        """
        Remove user ID from the list of grifter suppliers.
        """
        user_id: int = user.id
        user_name: str = user.name
        if user_id in self.suppliers:
            self.suppliers.remove(user_id)
            print(f"User {user_name} ({user_id}) removed from the "
                  "grifter suppliers registry.")
        else:
            print(f"User {user_name} ({user_id}) is not in the "
                  "grifter suppliers registry.")
        with open(self.file_name, "w") as file:
            json.dump({"suppliers": self.suppliers}, file)
# endregion


def reinitialize_grifter_suppliers() -> None:
    """
    Initializes the grifter suppliers.
    """
    global grifter_suppliers
    grifter_suppliers = GrifterSuppliers()
