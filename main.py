import asyncio
import os
import requests
from mcrcon import MCRcon
import discord

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

# Env Vars
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# --- Function: Send to Discord via Webhook ---
def send_to_discord_webhook(username, content, avatar_url=None):
    if username.endswith("(Discord):"):
        return  # prevent loops from Discord-origin messages

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

# --- Function: Listen for Ark Chat ---
async def ark_chat_listener():
    seen_lines = set()
    while True:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                chat_output = mcr.command("GetChat")
                lines = chat_output.split("\n")

                for line in lines:
                    if line in seen_lines:
                        continue
                    seen_lines.add(line)

                    if ": " in line:
                        name, msg = line.split(": ", 1)
                        if name.strip().endswith("(Discord):"):
                            continue  # Don't echo Discord messages
                        send_to_discord_webhook(name.strip(), msg.strip())

                    elif any(x in line.lower() for x in ["joined", "left", "disconnected", "connected"]):
                        send_to_discord_webhook(
                            username="Serene Branson",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )

        except Exception as e:
            print(f"🔥 RCON error: {e}")

        await asyncio.sleep(10)

# --- Function: Discord Message Handler ---
@client.event
async def on_message(message):
    if message.author.bot or message.channel.id != DISCORD_CHANNEL_ID:
        return

    player_name = f"{message.author.display_name} (Discord):"
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f'ServerChat {player_name} {message.content}')
    except Exception as e:
        print(f"🔥 Error sending to Ark: {e}")

# --- Main Runner ---
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
