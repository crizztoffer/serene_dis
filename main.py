import os
import asyncio
import discord
from discord.ext import commands
from mcrcon import MCRcon
import re

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
AVATAR_URL = "https://serenekeks.com/dis_ark.png"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Used to prevent Discord echo
sent_from_discord = set()

async def debug_get_chat():
    last_seen = None
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("getchat")
                if response and response != last_seen:
                    last_seen = response
                    match = re.match(r"^(.*?) \([^)]+\): (.*)$", response)
                    if match:
                        username = match.group(1).strip()
                        message = match.group(2).strip()
                        print(f"[ARK CHAT] {username}: {message}")  # Output message to console
        except Exception as e:
            print("[ERROR] getchat failed:", e)
        await asyncio.sleep(1)

@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    bot.loop.create_task(debug_get_chat())

@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            print(f"[INFO] Sending to ARK: {rcon_message}")
            mcr.command(f"serverchat {rcon_message}")
    except Exception as e:
        print("[ERROR] RCON message failed:", e)

    await bot.process_commands(message)

if __name__ == '__main__':
    asyncio.run(bot.start(DISCORD_TOKEN))
