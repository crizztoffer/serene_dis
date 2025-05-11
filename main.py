import asyncio
import os
import time
import requests
from collections import deque
from mcrcon import MCRcon
import discord

# Hardcoded webhook for sending messages to Discord
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

# Environment variables from Railway
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Discord setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# Caching messages from Discord -> Ark to prevent echo
recent_discord_msgs = deque()
CACHE_EXPIRY = 10  # seconds

def cache_discord_message(username, message):
    now = time.time()
    recent_discord_msgs.append((username, message, now))

def is_recent_discord_message(username, message):
    now = time.time()
    # Clean old entries
    while recent_discord_msgs and now - recent_discord_msgs[0][2] > CACHE_EXPIRY:
        recent_discord_msgs.popleft()
    return any(u == username and m == message for u, m, _ in recent_discord_msgs)

# Send message to Discord webhook
def send_to_discord_webhook(username, content, avatar_url=None):
    if not avatar_url:
        avatar_url = "https://serenekeks.com/dis_ark.png"

    # Don't send if it matches a recent Discord->Ark message
    if is_recent_discord_message(username, content):
        print("🔁 Skipping echo from Ark to Discord")
        return

    payload = {
        "username": f"{username} (Ark: Survival Evolved):",
        "content": content,
        "avatar_url": avatar_url
    }

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code not in [200, 204]:
        print(f"❌ Failed to send to Discord: {response.status_code} - {response.text}")

# Poll Ark server chat and send messages to Discord
async def ark_chat_listener():
    previous_lines = set()
    while True:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("GetChat")
                lines = response.split("\n")

                for line in lines:
                    if line in previous_lines:
                        continue
                    previous_lines.add(line)

                    if ": " in line:
                        name, message = line.split(": ", 1)
                        send_to_discord_webhook(name.strip(), message.strip())

                    elif any(kw in line.lower() for kw in ["joined", "left", "disconnected", "connected"]):
                        send_to_discord_webhook(
                            username="Serene Branson",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )
        except Exception as e:
            print(f"🔥 RCON read error: {e}")
        await asyncio.sleep(10)

# Relay messages from Discord → Ark
@client.event
async def on_message(message):
    if message.author.bot or message.channel.id != DISCORD_CHANNEL_ID:
        return

    username = f"{message.author.display_name} (Discord):"
    content = message.content

    print(f"💬 Sending to Ark: {username} {content}")
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {username} {content}")
        cache_discord_message(username, content)
    except Exception as e:
        print(f"🔥 Failed to send to Ark: {e}")

# Run both bots together
async def main():
    await asyncio.gather(
        ark_chat_listener(),
        client.start(DISCORD_TOKEN)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutting down.")
