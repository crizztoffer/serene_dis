import os
import asyncio
import discord
from discord.ext import commands
from mcrcon import MCRcon
import re

# Constants
AVATAR_URL = os.getenv("AVATAR_URL", "https://serenekeks.com/dis_ark.png")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "27020"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

# Discord client setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store messages sent from Discord to avoid echo
sent_messages = set()


def send_rcon_message(message: str):
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            response = mcr.command(f'serverchat {message}')
            print("[RCON Sent]:", message)
            return response
    except Exception as e:
        print("[RCON Error]:", e)
        return None


@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")


@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != DISCORD_CHANNEL_ID:
        return

    formatted = f"[DISCORD] {message.author.display_name}: {message.content}"
    send_rcon_message(formatted)
    sent_messages.add(formatted)  # store to avoid echo

    await bot.process_commands(message)


# Optional: ARK ➝ Discord relay if log polling is added in future.

if __name__ == "__main__":
    if not all([DISCORD_TOKEN, RCON_HOST, RCON_PASSWORD]):
        raise EnvironmentError("Missing one or more required environment variables.")

    asyncio.run(bot.start(DISCORD_TOKEN))
