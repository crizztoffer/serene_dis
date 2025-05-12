import asyncio
import os
import discord
from discord.ext import commands
from mcrcon import MCRcon
import aiohttp
import re
import time

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
AVATAR_URL = "https://serenekeks.com/dis_ark.png"
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH")  # set in Railway

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Regex to parse chat lines
chat_line_regex = re.compile(r'(\w+)\s+\(.*?\):\s+(.*)')

# Track last line to avoid reprocessing
last_known_line = ""

async def tail_log_file():
    global last_known_line
    if not os.path.exists(LOG_FILE_PATH):
        print(f"[ERROR] Log file not found: {LOG_FILE_PATH}")
        return

    print(f"[INFO] Tailing ARK log file: {LOG_FILE_PATH}")
    with open(LOG_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        f.seek(0, os.SEEK_END)  # Jump to end of file

        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(1)
                continue

            if "Chat" in line and "[DISCORD]" not in line:
                match = chat_line_regex.search(line)
                if match:
                    username, message = match.groups()
                    await send_to_discord(username, message)

async def send_to_discord(username, message):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(content=message, username=username, avatar_url=AVATAR_URL)
        print(f"[INFO] Sent to Discord: {username}: {message}")

@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"
    print(f"[INFO] Sending to ARK: {rcon_message}")

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            response = mcr.command(f'ServerChat "{rcon_message}"')
            print(f"[DEBUG] RCON chat response: {response}")
    except Exception as e:
        print(f"[ERROR] RCON Error: {e}")

    await bot.process_commands(message)

async def main():
    await bot.start(DISCORD_TOKEN)

# Start the log monitoring and Discord bot together
async def runner():
    await asyncio.gather(
        tail_log_file(),
        main()
    )

if __name__ == "__main__":
    asyncio.run(runner())
