import os
import asyncio
import discord
import ark_rcon
from discord.ext import commands

# Constants
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Optional: for log output via webhook
AVATAR_URL = os.getenv("AVATAR_URL", "https://serenekeks.com/dis_ark.png")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# RCON connection info from Railway env variables
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "27020"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def send_rcon_message(message: str) -> str:
    try:
        with Client(RCON_HOST, RCON_PORT, passwd=RCON_PASSWORD) as client:
            response = client.run(f'serverchat {message}')
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
    # Ignore bot messages or irrelevant channels
    if message.author.bot or message.channel.id != DISCORD_CHANNEL_ID:
        return

    discord_msg = f"[DISCORD] {message.author.display_name}: {message.content}"
    send_rcon_message(discord_msg)

    await bot.process_commands(message)


# If needed, extend this with periodic ARK-to-Discord log reading in future.
# Currently only Discord ➡ ARK direction supported reliably via RCON

if __name__ == "__main__":
    if not all([DISCORD_TOKEN, RCON_HOST, RCON_PORT, RCON_PASSWORD]):
        raise EnvironmentError("Missing one or more required environment variables.")

    asyncio.run(bot.start(DISCORD_TOKEN))
