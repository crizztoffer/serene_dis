import asyncio
import os
import requests
from mcrcon import MCRcon
import discord

# Webhook URL to send messages to Discord
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

# Environment variables from Railway
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Track last Discord-sent message to avoid echo
last_discord_message = {"username": "", "content": ""}

# Send a message to Discord via webhook
def send_to_discord_webhook(username, content, avatar_url=None):
    global last_discord_message

    # Skip message if it matches the last one sent from Discord
    if username == last_discord_message["username"] and content == last_discord_message["content"]:
        return

    payload = {
        "username": f"{username} - (Ark: Survival Evolved):",
        "content": content,
        "avatar_url": avatar_url or "https://serenekeks.com/dis_ark.png"
    }

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code not in [200, 204]:
        print(f"❌ Failed to send to Discord: {response.status_code} - {response.text}")

# Listen to Ark server chat and forward messages to Discord
async def ark_chat_listener():
    seen_lines = set()

    while True:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                chat = mcr.command("GetChat")
                lines = chat.split("\n")

                for line in lines:
                    if line in seen_lines:
                        continue
                    seen_lines.add(line)

                    if ": " in line:
                        name, msg = line.split(": ", 1)
                        send_to_discord_webhook(name.strip(), msg.strip())

                    elif any(event in line.lower() for event in ["joined", "left", "disconnected", "connected"]):
                        send_to_discord_webhook(
                            username="Serene Branson",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )

        except Exception as e:
            print(f"🔥 RCON read error: {e}")
        await asyncio.sleep(10)

# Relay messages from Discord to Ark
@client.event
async def on_message(message):
    global last_discord_message

    if message.author.bot or message.channel.id != DISCORD_CHANNEL_ID:
        return

    display_name = message.author.display_name
    content = message.content.strip()

    # Save message to prevent echo
    last_discord_message["username"] = display_name
    last_discord_message["content"] = content

    ark_message = f"{display_name} (Discord): {content}"

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {ark_message}")
    except Exception as e:
        print(f"🔥 Error sending to Ark: {e}")

# Run Discord bot and Ark listener concurrently
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
