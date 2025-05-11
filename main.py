import asyncio
import os
import requests
from mcrcon import MCRcon
import discord

# Environment variables
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

# Discord client setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Store the last message sent from Discord to prevent echo
last_discord_message = {"username": "", "content": ""}

# Function to send messages to Discord via webhook
def send_to_discord_webhook(username, content, avatar_url=None):
    # Check for echo to prevent duplicate messages
    if username == last_discord_message["username"] and content == last_discord_message["content"]:
        return

    payload = {
        "username": f"{username} - (Ark: Survival Evolved)",
        "content": content,
        "avatar_url": avatar_url or "https://serenekeks.com/dis_ark.png"
    }

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code not in [200, 204]:
        print(f"Failed to send to Discord: {response.status_code} - {response.text}")

# Function to listen to ARK chat and relay messages to Discord
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
                        name = name.strip()
                        msg = msg.strip()

                        # Skip messages that originated from Discord
                        if name.endswith("(Discord)"):
                            continue

                        send_to_discord_webhook(name, msg)

                    elif any(event in line.lower() for event in ["joined", "left", "disconnected", "connected"]):
                        send_to_discord_webhook(
                            username="Server Notification",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )

        except Exception as e:
            print(f"Error reading from ARK server: {e}")
        await asyncio.sleep(10)

# Event handler for messages sent in Discord
@client.event
async def on_message(message):
    global last_discord_message

    if message.author.bot or message.channel.id != DISCORD_CHANNEL_ID:
        return

    username = message.author.display_name
    content = message.content.strip()

    # Save the last message sent to prevent echo
    last_discord_message["username"] = username
    last_discord_message["content"] = content

    ark_message = f"{username} - (Discord): {content}"

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {ark_message}")
    except Exception as e:
        print(f"Error sending message to ARK server: {e}")

# Main function to run both Discord client and ARK chat listener
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
