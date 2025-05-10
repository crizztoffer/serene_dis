import asyncio
import os
import requests
from mcrcon import MCRcon
import discord

# Hardcoded webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

# Env vars
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# Send to Discord via webhook
def send_to_discord_webhook(username, content, avatar_url=None):
    # Ignore messages marked as coming from Discord
    if content.startswith("[DC]"):
        return

    payload = {
        "username": username,
        "content": content
    }
    if avatar_url:
        payload["avatar_url"] = avatar_url

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        print(f"❌ Failed to send to Discord: {response.status_code} - {response.text}")

# Poll Ark server and relay chat to Discord
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

                        # Skip if the message was sent from Discord
                        if message.strip().startswith("[DC]"):
                            continue

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

# Listen for Discord messages and send to Ark
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != DISCORD_CHANNEL_ID:
        return

    content = f"[DC]{message.author.display_name}: {message.content}"
    print(f"💬 Sending to Ark: {content}")

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {content}")
    except Exception as e:
        print(f"🔥 Failed to send to Ark: {e}")

# Run both loops
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
