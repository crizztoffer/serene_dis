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

# Debug GMod RCON connection separately
async def debug_gmod_rcon():
    await bot.wait_until_ready()
    GMOD_RCON_IP = os.getenv("GMOD_RCON_IP")
    GMOD_RCON_PORT = int(os.getenv("GMOD_RCON_PORT", "0"))
    GMOD_RCON_PASSWORD = os.getenv("GMOD_RCON_PASSWORD")

    try:
        with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as mcr:
            print("[INFO] Successfully connected to GMod RCON.")
            test_response = mcr.command("status")
            print(f"[GMOD RCON RESPONSE] {test_response}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to GMod RCON: {e}")

# Schedule the GMod RCON debug task
@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    bot.loop.create_task(debug_get_chat())  # Existing ARK chat debug task
    bot.loop.create_task(debug_gmod_rcon())  # New GMod RCON connection test


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
                        raw_username = match.group(1)
                        message = match.group(2)
                        username = f"(Ark: Survival Evolved) {raw_username}"

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

        await asyncio.sleep(1)

@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    bot.loop.create_task(debug_get_chat())  # Start debugging Ark chat

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
