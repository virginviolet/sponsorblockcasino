from discord import app_commands, Intents, Interaction, Message, Client, ChannelType
from discord.ext import commands
from os import getenv
from dotenv import load_dotenv
from sqlite3 import connect

# Load .env file for the bot token
load_dotenv()
TOKEN = getenv('DISCORD_TOKEN')

# Intents and bot setup
intents = Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot("!", intents=intents)
client = Client(intents=intents)

# Sync slash commands to Discord


@bot.event
async def on_ready():
    # Sync the commands to Discord
    try:
        await bot.tree.sync()
        print(f"Synced commands for bot {bot.user}. Bot is ready!")
    except Exception as e:
        print(f"Error syncing commands: {e}")


@bot.event
async def on_message(message: Message):
    # The user ID for SBCoin
    SBCOIN_USER_ID = 1323248155055358016

    if message.author.id == SBCOIN_USER_ID:
        # await message.channel.send("Hello, SBCoin!")
        print(f"Message from SBCoin: {message.content}")
        print(f"message.mentions: {message.raw_mentions}")
        for user in message.raw_mentions:
            print(f"The user mentioned is <@{user}>.")

    # This must be at the end to process commands like "/ping"
    await bot.process_commands(message)

# Example slash command


@bot.tree.command(name="ping", description="Replies with Pong!")
async def ping(interaction: Interaction):
    """
    Replies with Pong! The response is visible only to the user who invoked the command.

    Args:
        interaction (Interaction): The interaction object representing the command invocation.
    """
    await interaction.response.send_message("Pong!", ephemeral=True)


@bot.tree.command(name="hello", description="Says hello to the specified user.")
async def hello(interaction: Interaction, name: str):
    await interaction.response.send_message(f"Hello, {name}!")

if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN is not set in the environment variables.")
