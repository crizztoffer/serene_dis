import os
import asyncio
import re
import discord
from discord.ext import commands
from mcrcon import MCRcon
import aiohttp

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
AVATAR_URL = "https://serenekeks.com/dis_ark.png"
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "/path/to/default/log/file.log")  # Pull path from environment variable

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

last_line = ""

# Read last chat line from ARK log
def read_latest_chat_line():
    global last_line
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if "Chat" in line and "[DISCORD]" not in line:
                    if line != last_line:
                        last_line = line
                        return parse_chat_line(line)
    except Exception as e:
        print("Log read error:", e)
    return None, None

# Parse chat line into username and message
def parse_chat_line(line):
    match = re.search(r'(\w+)\s+Global\s+Chat:\s+(.*)', line)
    if match:
        return match.group(1), match.group(2)
    return None, None

# Send in-game message to Discord via webhook
async def send_to_discord(username, message):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(
            content=message,
            username=username,
            avatar_url=AVATAR_URL
        )

# Monitor ARK log and send new messages to Discord
async def monitor_ark_chat():
    await bot.wait_until_ready()
    while not bot.is_closed():
        username, message = read_latest_chat_line()
        if username and message:
            await send_to_discord(username, message)
        await asyncio.sleep(5)

# Send Discord message to ARK via RCON
@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f'broadcast {rcon_message}')
    except Exception as e:
        print("RCON error:", e)

    await bot.process_commands(message)

# Use setup_hook for async startup tasks
@bot.event
async def setup_hook():
    bot.loop.create_task(monitor_ark_chat())

# Start the bot
bot.run(DISCORD_TOKEN)
