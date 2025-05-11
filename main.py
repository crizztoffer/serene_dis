import asyncio
import os
import requests
from mcrcon import MCRcon
import discord

# Discord Webhook for Ark → Discord
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

# Environment Variables from Railway
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Discord bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# Track messages sent from Discord to avoid echoes
sent_messages = set()

# Send to Discord via webhook
def send_to_discord_webhook(username, content, avatar_url=None):
    # Skip if it's a message we already sent from Discord
    identifier = (username, content)
    if identifier in sent_messages:
        sent_messages.remove(identifier)  # Remove after detecting it once
        return

    # Default avatar for Ark messages
    if not avatar_url:
        avatar_url = "https://serenekeks.com/dis_ark.png"

    payload = {
        "username": f"{username} (Ark: Survival Evolved):",
        "content": content,
        "avatar_url": avatar_url
    }

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code not in [200, 204]:
        print(f"❌ Failed to send to Discord: {response.status_code} - {response.text}")

# Read from Ark and send to Discord
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
                            username="Server",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )
        except Exception as e:
            print(f"🔥 RCON error: {e}")

        await asyncio.sleep(10)

# Relay from Discord → Ark
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != DISCORD_CHANNEL_ID:
        return
    if not message.content.strip():
        return

    username = f"{message.author.display_name} (Discord):"
    content = message.content.strip()

    full_message = f"{username} {content}"
    print(f"💬 Sending to Ark: {full_message}")

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {full_message}")
        # Track to suppress echo
        sent_messages.add((message.author.display_name, content))
    except Exception as e:
        print(f"🔥 Failed to send to Ark: {e}")

# Launch both bots
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
