import os
import asyncio
import discord
from discord.ext import commands
from arkon import RCON
import aiohttp

# Constants (Webhook + Avatar)
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
AVATAR_URL = "https://serenekeks.com/dis_ark.png"

# Environment Variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === Sends a message into Ark via ServerChat ===
async def send_rcon_message(message: str):
    try:
        async with RCON(RCON_HOST, RCON_PORT, RCON_PASSWORD) as rcon:
            response = await rcon.send(f"ServerChat {message}")
            print("[INFO] Sent to ARK:", message)
            print("[DEBUG] RCON response:", response)
    except Exception as e:
        print("[ERROR] Failed to send RCON message:", e)

# === Sends a message to Discord via webhook ===
async def send_to_discord(username, message):
    try:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
            await webhook.send(
                content=message,
                username=username,
                avatar_url=AVATAR_URL
            )
            print(f"[INFO] Sent to Discord: {username}: {message}")
    except Exception as e:
        print("[ERROR] Failed to send message to Discord:", e)

# === Handle incoming messages from Discord to Ark ===
@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    if '[DISCORD]' in message.content:
        return  # Prevent loopback

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"
    await send_rcon_message(rcon_message)

    await bot.process_commands(message)

# === Optional: background task to read logs or chat ===
# Placeholder: you'd implement actual parsing if log access is possible

async def monitor_ark_chat():
    await bot.wait_until_ready()
    while not bot.is_closed():
        # If in the future we read from logs or API, process them here
        await asyncio.sleep(5)

# === Main entrypoint using asyncio.run() ===
async def main():
    bot.loop.create_task(monitor_ark_chat())
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
