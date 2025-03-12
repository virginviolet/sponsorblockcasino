# region Imports
# Standard library
import json
from os import makedirs
from os.path import exists
from typing import Dict, List

# Third party
from discord.ext.commands import Bot  # type: ignore

# Local
import core.global_state as g
# endregion

# region Checkpoints
class ChannelCheckpoints:
    """
    ChannelCheckpoints is a class that manages checkpoints for a specific
    channel in a guild. It allows for saving, loading, and managing
    message IDs as checkpoints.

    Methods:
        __init__(self,
            guild_name,
            guild_id,
            channel_name,
            channel_id,
            max_checkpoints):
            Initializes checkpoints for a channel in a guild.
        count_lines(self):
        create(self):
            Creates a checkpoint file for the channel, including necessary
            directories and metadata files.
        save(self, message_id):
            Saves the given message ID as a checkpoint in the file.
            If the number of checkpoints exceeds the maximum allowed, the
            oldest checkpoint is removed.
        remove_first_line(self):
        load(self):
            Loads the checkpoints from the file specified by self.file_name.
        """

    def __init__(self,
                 guild_name: str,
                 guild_id: int,
                 channel_name: str,
                 channel_id: int,
                 max_checkpoints: int = 10) -> None:
        """
        Initialize checkpoints for a channel in a guild.

        Args:
            guild_name: The name of the guild
            guild_id: The ID of the guild
            channel_name: The name of the channel
            channel_id: The ID of the channel
            max_checkpoints: The maximum number of checkpoints

        Attributes:
            max_checkpoints: The maximum number of checkpoints
            guild_name: The name of the guild
            guild_id: The ID of the guild
            channel_name: The name of the channel
            channel_id: The ID of the channel
            directory: The directory path for storing checkpoints
            file_name: The file name for storing channel checkpoints
            entry_count: The count of entries in the checkpoints file
            last_message_ids: The last message IDs in the channel
        """
        self.max_checkpoints: int = max_checkpoints
        self.guild_name: str = guild_name
        self.guild_id: int = guild_id
        self.channel_name: str = channel_name
        self.channel_id: int = channel_id
        self.directory: str = (f"data/checkpoints/guilds/{self.guild_id}"
                               f"/channels/{self.channel_id}")
        self.file_name: str = f"{self.directory}/channel_checkpoints.json"
        self.entry_count: int = self.count_lines()
        self.last_message_ids: List[Dict[str, int]] | None = self.load()

    def count_lines(self) -> int:
        """
        Counts the number of lines in the file specified by self.file_name.
        Returns:
            int: The number of lines in the file. Returns 0 if the file
                does not exist.
        """
        if not exists(self.file_name):
            return 0

        with open(self.file_name, "r") as file:
            count: int = sum(1 for _ in file)
            return count

    def create(self) -> None:
        """
        Creates an checkpoint file for the channel.

        This method performs the following tasks:
        1. Creates any missing directories in the path specified
            by `self.file_name`.
        2. Writes the guild name to a JSON file named `guild_name.json` in
            the directory corresponding to the guild ID.
        3. Writes the channel name to a JSON file named `channel_name.json` in
            the directory corresponding to the channel ID.
        4. Creates an empty checkpoints file at the path specified
            by `self.file_name`.

        The directory structure is created based on the path specified
        in `self.file_name`.
        The guild and channel names are written to files in directories named
        after their IDs, allowing bot maintainers to identify guilds and
        channels by their names.
        """
        # Create missing directories
        directories: str = self.file_name[:self.file_name.rfind("/")]
        for i, directory in enumerate(directories.split("/")):
            path: str = "/".join(directories.split("/")[:i+1])
            if not exists(directory):
                makedirs(path, exist_ok=True)
            # Write the guild name and channel name to files in the id
            # directories, so that bot maintainers can identify the guilds and
            # channels
            # Channel names can change, but the IDs will not
            if directory.isdigit() and int(directory) == self.guild_id:
                name_file_name: str = f"{path}/guild_name.json"
                with open(name_file_name, "w") as file:
                    file.write(json.dumps({"guild_name": self.guild_name}))
                    pass
            elif directory.isdigit() and int(directory) == self.channel_id:
                name_file_name: str = f"{path}/channel_name.json"
                with open(name_file_name, "w") as file:
                    file.write(json.dumps({"channel_name": self.channel_name}))
                    pass

        print(f"Creating checkpoints file: '{self.file_name}'")
        with open(self.file_name, "w"):
            pass

    def save(self, message_id: int) -> None:
        """
        Saves the given message ID as a checkpoint in the file.
        If the file does not exist, it creates a new one. The message ID is
        appended to the file in JSON format. If the number of checkpoints
        exceeds the maximum allowed, the oldest checkpoint is removed.
        Args:
            message_id: The ID of the message to save as a checkpoint.
        """
        if not exists(self.file_name):
            self.create()

        # print(f"Saving checkpoint: {message_id}")
        self.entry_count = self.count_lines()
        with open(self.file_name, "a") as file:
            if self.entry_count == 0:
                file.write(json.dumps({"last_message_id": message_id}))
            else:
                file.write("\n" + json.dumps({"last_message_id": message_id}))
        self.entry_count += 1

        while self.entry_count > self.max_checkpoints:
            self.remove_first_line()
            self.entry_count -= 1

    def remove_first_line(self) -> None:
        """
        Removes the first line from the file specified by self.file_name.

        This method reads all lines from the file, then writes all lines except
        the first one
        back to the file, effectively removing the first line.
        """
        with open(self.file_name, "r") as file:
            lines: List[str] = file.readlines()
        with open(self.file_name, "w") as file:
            file.writelines(lines[1:])

    def load(self) -> List[Dict[str, int]] | None:
        """
        Loads checkpoints from a file.
        Returns:
            A list of dictionaries containing checkpoint data if the file
                exists, otherwise None.
        """
        if not exists(self.file_name):
            return None

        with open(self.file_name, "r") as file:
            checkpoints: List[Dict[str, int]] | None = []
            # print("Loading checkpoints...")
            for line in file:
                checkpoint: Dict[str, int] = (
                    {k: int(v) for k, v in json.loads(line).items()})
                # print(f"checkpoint: {checkpoint}")
                checkpoints.append(checkpoint)
                return checkpoints
# endregion

# region CP start



async def start_checkpoints(limit: int = 10) -> Dict[int, ChannelCheckpoints]:
    """
    Initializes checkpoints for all text channels in all guilds the bot is a
    member of; creates instances of ChannelCheckpoints for each channel.

    Args:
        limit: The maximum number of checkpoints to create for each channel.
        Defaults to 10.

    Returns:
        Dict: A dictionary where the keys are channel IDs and the values are
        ChannelCheckpoints objects.
    """
    assert isinstance(g.bot, Bot), "bot has not been initialized."
    all_checkpoints: dict[int, ChannelCheckpoints] = {}
    print("Starting checkpoints...")
    channel_id: int = 0
    channel_name: str = ""
    for guild in g.bot.guilds:
        guild_id: int = guild.id
        guild_name: str = guild.name
        print(f"Guild: {guild_name} ({guild_id})")
        for channel in guild.text_channels:
            channel_id = channel.id
            channel_name = channel.name
            print(f"Channel: {channel_name} ({channel_id})")
            all_checkpoints[channel_id] = ChannelCheckpoints(
                guild_name=guild_name,
                guild_id=guild_id,
                channel_name=channel_name,
                channel_id=channel_id,
                max_checkpoints=limit
            )
    print("Checkpoints started.")
    return all_checkpoints
# endregion
