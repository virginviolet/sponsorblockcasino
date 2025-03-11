# region Imports
# Standard library
from os.path import exists
from os import makedirs
from os.path import exists
from typing import List, Sequence

# Third party
from discord import Guild
from discord.ext.commands import Bot  # type: ignore
# endregion

# region Guild list
def load_guild_ids(bot: Bot, file_name: str = "data/guild_ids.txt") -> List[int]:
    """
    Loads guild IDs from a specified file and updates the file with any
    new guild IDs.

    Args:
        file_name: The path to the file containing the guild IDs. Defaults
            to "data/guild_ids.txt".

    Returns:
        List[int]: A list of guild IDs.
    """
    print("Loading guild IDs...")
    # Create missing directories
    directories: str = file_name[:file_name.rfind("/")]
    makedirs(directories, exist_ok=True)
    guild_ids: List[int] = []
    read_mode: str = "a+"
    if not exists(file_name):
        read_mode = "w+"
    else:
        read_mode = "r+"
    with open(file_name, read_mode) as file:
        for line in file:
            guild_id = int(line.strip())
            print(f"Adding guild ID {guild_id} from file to the list...")
            guild_ids.append(guild_id)
        bot_guilds: Sequence[Guild] = bot.guilds
        for guild in bot_guilds:
            guild_id: int = guild.id
            if not guild_id in guild_ids:
                print(f"Adding guild ID {guild_id} "
                      "to the list and the file...")
                file.write(f"{guild_id}\n")
                guild_ids.append(guild_id)
    print("Guild IDs loaded.")
    return guild_ids
# endregion