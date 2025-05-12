import os
import asyncio
import discord
from discord.ext import commands
from mcrcon import MCRcon
import re
import aiohttp

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
last_seen_message = None

def parse_chat_response(rcon_response):
    lines = rcon_response.splitlines()
    for line in reversed(lines):
        if "[DISCORD]" not in line and "Chat" in line:
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
    last_seen = None
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("broadcast ping")
                username, message = parse_chat_response(response)
                if username and message and message != last_seen:
                    last_seen = message
                    await send_to_discord(username, message)
        except Exception as e:
            print("[ERROR] monitor_ark_chat:", e)
        await asyncio.sleep(1)

async def debug_get_chat():
    global last_seen_message
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("getchat")
                lines = response.splitlines()
                for line in lines:
                    match = re.match(r"^(.*?) \([^\)]+\): (.+)$", line)
                    if match:
                        username = match.group(1)
                        message = match.group(2)

                        if message != last_seen_message:
                            last_seen_message = message
                            async with aiohttp.ClientSession() as session:
                                webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
                                await webhook.send(
                                    content=message,
                                    username=username,
                                    avatar_url=AVATAR_URL
                                )

        except Exception as e:
            print("[ERROR] debug_get_chat:", e)

        await asyncio.sleep(2)

@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    bot.loop.create_task(monitor_ark_chat())
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
