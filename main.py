import asyncio
import os
import discord
from discord.ext import commands
from mcrcon import MCRcon
import aiohttp
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

last_message = ""

# -- Function to send ARK message to Discord via Webhook
async def send_to_discord(username, message):
    print(f"[INFO] Sending to Discord: {username}: {message}")
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(
            content=message,
            username=username,
            avatar_url=AVATAR_URL
        )

# -- Parses ARK log chat message for username and content
def parse_chat_line(line):
    match = re.search(r'(\w+)\s+Global\s+Chat:\s+(.*)', line)
    if match:
        username = match.group(1)
        message = match.group(2)
        return username, message
    return None, None

# -- Polls ARK RCON for chat and sends new messages to Discord
async def monitor_ark_chat():
    global last_message
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("getchat")  # Make sure this command is valid on your server
                print(f"[DEBUG] RCON chat response: {response}")
                if response and response != last_message:
                    last_message = response
                    username, message = parse_chat_line(response)
                    if username and message and "[DISCORD]" not in message:
                        await send_to_discord(username, message)
        except Exception as e:
            print("[ERROR] RCON Error:", e)
        await asyncio.sleep(5)

# -- Forwards Discord messages into ARK chat using RCON
@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"
    print(f"[INFO] Sending to ARK: {rcon_message}")

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"broadcast {rcon_message}")
    except Exception as e:
        print("[ERROR] RCON Error:", e)

    await bot.process_commands(message)

# -- Launch the monitoring loop
@bot.event
async def on_ready():
    print(f"[INFO] Bot connected as {bot.user}")
    bot.loop.create_task(monitor_ark_chat())

# -- Start the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
