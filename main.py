import os
import asyncio
import discord
from discord.ext import commands
from mcrcon import MCRcon
import aiohttp

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
AVATAR_URL = "https://serenekeks.com/dis_ark.png"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Keep track of last message to avoid sending duplicates
last_message = ""

# Fetch ARK server chat using RCON
async def fetch_chat_from_ark():
    global last_message
    try:
        # Connect to RCON and get the last global chat message
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            response = mcr.command("listplayers")  # Can be changed to a specific command to read chat logs
            if response:
                # Assuming the response contains chat messages (adjust command accordingly)
                for line in response.splitlines():
                    if line != last_message:
                        last_message = line
                        username, message = parse_chat_line(line)
                        if username and message:
                            await send_to_discord(username, message)
    except Exception as e:
        print("RCON Error:", e)

# Parse chat line into username and message (adjust regex as per ARK chat format)
def parse_chat_line(line):
    match = re.search(r'(\w+):\s*(.*)', line)
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

# Monitor ARK chat and send new messages to Discord
async def monitor_ark_chat():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await fetch_chat_from_ark()
        await asyncio.sleep(5)  # Adjust as needed for polling frequency

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
