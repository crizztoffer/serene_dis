import asyncio
import os
import requests
from mcrcon import MCRcon
import discord

# Webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

# Env variables from Railway
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Prevent echo loop by storing last Discord message sent
last_discord_msg = {"username": "", "content": ""}

# --- Send to Discord ---
def send_to_discord_webhook(username, content, avatar_url=None):
    if not avatar_url:
        avatar_url = "https://serenekeks.com/dis_ark.png"

    # Skip if Ark is echoing a Discord-sent message
    if username == last_discord_msg["username"] and content == last_discord_msg["content"]:
        return

    payload = {
        "username": f"{username} - (Ark: Survival Evolved):",
        "content": content,
        "avatar_url": avatar_url
    }

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code not in [200, 204]:
        print(f"❌ Discord webhook failed: {response.status_code} - {response.text}")

# --- Poll Ark Chat and Send to Discord ---
async def ark_chat_listener():
    seen_lines = set()

    while True:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("GetChat")
                lines = response.split("\n")

                for line in lines:
                    if line in seen_lines:
                        continue
                    seen_lines.add(line)

                    if ": " in line:
                        name, msg = line.split(": ", 1)
                        clean_name = name.strip()
                        clean_msg = msg.strip()
                        send_to_discord_webhook(clean_name, clean_msg)

                    elif any(event in line.lower() for event in ["joined", "left", "disconnected", "connected"]):
                        send_to_discord_webhook(
                            username="Server",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )

        except Exception as e:
            print(f"🔥 RCON read error: {e}")
        await asyncio.sleep(10)

# --- Send Discord Messages to Ark ---
@client.event
async def on_message(message):
    if message.author.bot or message.channel.id != DISCORD_CHANNEL_ID:
        return

    username = f"{message.author.display_name} - (Discord):"
    content = message.content.strip()

    # Store for echo prevention
    last_discord_msg["username"] = message.author.display_name
    last_discord_msg["content"] = content

    print(f"💬 Sending to Ark: {username} {content}")
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {username} {content}")
    except Exception as e:
        print(f"🔥 Failed to send to Ark: {e}")

# --- Launch both tasks ---
async def main():
    await asyncio.gather(
        ark_chat_listener(),
        client.start(DISCORD_TOKEN)
    )

# --- AsyncIO Compatibility Fix for Railway ---
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot shutting down.")
