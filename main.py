import asyncio
import os
import discord
from discord.ext import commands
from mcrcon import MCRcon
import paramiko
import aiohttp
import re

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
AVATAR_URL = "https://serenekeks.com/dis_ark.png"
LOG_FILE_PATH = "/path/to/ShooterGame/Saved/Logs/ShooterGame.log"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASS")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

last_line = ""

async def read_latest_chat_line():
    global last_line
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)
        with sftp.file(LOG_FILE_PATH, 'r') as file:
            lines = file.readlines()
            for line in reversed(lines):
                if "Chat" in line and "[DISCORD]" not in line:
                    if line != last_line:
                        last_line = line
                        return parse_chat_line(line)
        sftp.close()
        transport.close()
    except Exception as e:
        print("Error reading log:", e)
    return None, None

def parse_chat_line(line):
    match = re.search(r'(\w+)\s+Global\s+Chat:\s+(.*)', line)
    if match:
        username = match.group(1)
        message = match.group(2)
        return username, message
    return None, None

async def send_to_discord(username, message):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(
            content=message,
            username=username,
            avatar_url=AVATAR_URL
        )

async def monitor_ark_chat():
    await bot.wait_until_ready()
    while not bot.is_closed():
        username, message = await read_latest_chat_line()
        if username and message:
            await send_to_discord(username, message)
        await asyncio.sleep(5)

@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f'broadcast {rcon_message}')
    except Exception as e:
        print("RCON Error:", e)

    await bot.process_commands(message)

bot.loop.create_task(monitor_ark_chat())
bot.run(DISCORD_TOKEN)
