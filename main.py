import asyncio
import os
import requests
from mcrcon import MCRcon
import discord

# Hardcoded webhook for sending messages to Discord
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

# Environment variables from Railway
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))  # <-- Corrected variable name

# Discord setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# Webhook sender
def send_to_discord_webhook(username, content, avatar_url=None):
    # Ignore messages marked as coming from Discord
    if content.startswith("(Discord)"):
        return

    # Set default avatar for Ark player messages
    if not avatar_url:
        avatar_url = "https://serenekeks.com/dis_ark.png"

    payload = {
        "username": username,
        "content": content,
        "avatar_url": avatar_url
    }

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        print(f"❌ Failed to send to Discord: {response.status_code} - {response.text}")

# Poll Ark server chat and send new lines to Discord
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

                    # Player chat
                    if ": " in line:
                        name, message = line.split(": ", 1)

                        if message.strip().startswith("(Discord): "):
                            continue
                        
                        send_to_discord_webhook(name.strip(), message.strip())

                    # Join/leave events
                    elif any(kw in line.lower() for kw in ["joined", "left", "disconnected", "connected"]):
                        send_to_discord_webhook(
                            username="Serene Branson - Ark: Survival Evolved",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )
        except Exception as e:
            print(f"🔥 RCON read error: {e}")
        await asyncio.sleep(10)

# Discord → Ark chat relay
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != DISCORD_CHANNEL_ID:
        return

    content = f"{message.author.display_name}: {message.content}"
    print(f"💬 Sending to Ark: {content}")

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {content}")
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
