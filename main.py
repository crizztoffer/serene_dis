import os
import asyncio
import discord
from discord.ext import commands
from ark_rcon import ArkRcon
import re
import aiohttp

# === Constants ===
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

last_seen_chat = None


# === Send message to Discord via webhook ===
async def send_to_discord(username, message):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(content=message, username=username, avatar_url=AVATAR_URL)


# === Send message to Ark via RCON ===
async def send_to_ark(message):
    try:
        async with ArkRcon(RCON_HOST, RCON_PORT, RCON_PASSWORD) as rcon:
            response = await rcon.send_command(f'ServerChat {message}')
            print("[INFO] Sent to ARK:", message)
            print("[DEBUG] RCON response:", response)
    except Exception as e:
        print("[ERROR] Failed to send RCON message:", e)


# === Monitor Ark chat using GetChat ===
async def monitor_ark_chat():
    global last_seen_chat
    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            async with ArkRcon(RCON_HOST, RCON_PORT, RCON_PASSWORD) as rcon:
                response = await rcon.send_command("GetChat")
                if response and response != last_seen_chat:
                    last_seen_chat = response

                    lines = response.split("\n")
                    for line in lines:
                        if "[DISCORD]" in line or "AdminCmd" in line:
                            continue

                        match = re.search(r'(\w+):\s(.+)', line)
                        if match:
                            username = match.group(1)
                            message = match.group(2)
                            await send_to_discord(username, message)
        except Exception as e:
            print("[ERROR] Failed to fetch chat:", e)

        await asyncio.sleep(5)


# === Handle messages from Discord to Ark ===
@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"
    await send_to_ark(rcon_message)

    await bot.process_commands(message)


# === Run bot ===
async def main():
    asyncio.create_task(monitor_ark_chat())
    await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
