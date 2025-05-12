import asyncio
import os
import re
import aiohttp
import discord
from discord.ext import commands
from mcrcon import MCRcon

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

last_chat_lines = set()

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
        await webhook.send(content=message, username=username, avatar_url=AVATAR_URL)

async def monitor_ark_chat():
    global last_chat_lines
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("GetChat")
                if response:
                    lines = response.strip().split('\n')
                    for line in lines:
                        if line not in last_chat_lines and "[DISCORD]" not in line:
                            last_chat_lines.add(line)
                            username, message = parse_chat_line(line)
                            if username and message:
                                await send_to_discord(username, message)
        except Exception as e:
            print(f"[ERROR] Failed to read chat: {e}")
        await asyncio.sleep(5)

@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f'ServerChat {rcon_message}')
            print(f"[INFO] Sent to ARK: {rcon_message}")
    except Exception as e:
        print(f"[ERROR] RCON command failed: {e}")

    await bot.process_commands(message)

async def main():
    bot.loop.create_task(monitor_ark_chat())
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
