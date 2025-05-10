import asyncio
import os
from mcrcon import MCRcon
import discord
import requests

# Hardcoded webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

# Discord bot token and channel
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# RCON details
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")


# Function to send messages to Discord via webhook
def send_to_discord_webhook(username, content, avatar_url=None):
    if content.startswith("[DC]"):
        return  # Prevent echo loops

    if not avatar_url:
        avatar_url = "https://serenekeks.com/dis_ark.png"

    payload = {
        "username": username,
        "avatar_url": avatar_url,
        "content": content
    }

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code not in [200, 204]:
        print(f"❌ Failed to send to Discord: {response.status_code} - {response.text}")


# Async function to read Ark chat
async def ark_chat_listener():
    previous_lines = set()

    if not all([RCON_HOST, RCON_PORT, RCON_PASSWORD]):
        print("❌ Missing one or more RCON environment variables.")
        return

    while True:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("GetChat")
                lines = response.split("\n")

                for line in lines:
                    if line in previous_lines:
                        continue
                    previous_lines.add(line)

                    # Player chat
                    if ": " in line:
                        name, message = line.split(": ", 1)
                        send_to_discord_webhook(
                            username=name.strip(),
                            content=message.strip()
                        )

                    # Server messages
                    elif any(kw in line.lower() for kw in ["joined", "left", "disconnected", "connected"]):
                        send_to_discord_webhook(
                            username="Serene Branson",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )

        except Exception as e:
            print(f"🔥 Error reading Ark chat: {e}")

        await asyncio.sleep(10)


# Discord bot client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    asyncio.create_task(ark_chat_listener())


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id != CHANNEL_ID:
        return

    if message.content.strip():
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                player_name = message.author.display_name
                msg = f"[DC] {player_name}: {message.content}"
                mcr.command(f"broadcast {msg}")
        except Exception as e:
            print(f"🔥 Failed to send message to Ark: {e}")


if __name__ == "__main__":
    try:
        client.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("Bot shutting down.")
