import asyncio
import os
from mcrcon import MCRcon
import discord
import requests

# Function to send a message to Discord using a webhook
def send_to_discord_webhook(username, content, avatar_url=None):
    webhook_url = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"

    payload = {
        "username": username,
        "content": content
    }

    if avatar_url:
        payload["avatar_url"] = avatar_url

    response = requests.post(webhook_url, json=payload)

    if response.status_code != 204:
        print(f"❌ Failed to send to Discord: {response.status_code} - {response.text}")

# Main loop to poll Ark chat and detect join/leave/server messages
async def ark_chat_listener():
    previous_lines = set()

    rcon_host = os.getenv("RCON_HOST")
    rcon_port = int(os.getenv("RCON_PORT", "0"))
    rcon_password = os.getenv("RCON_PASSWORD")

    if not all([rcon_host, rcon_port, rcon_password]):
        print("❌ Missing one or more RCON environment variables.")
        return

    while True:
        try:
            with MCRcon(rcon_host, rcon_password, port=rcon_port) as mcr:
                response = mcr.command("GetChat")
                lines = response.split("\n")

                for line in lines:
                    if line in previous_lines:
                        continue
                    previous_lines.add(line)

                    # Detect player chat
                    if ": " in line:
                        name, message = line.split(": ", 1)
                        send_to_discord_webhook(
                            username=name.strip(),
                            content=message.strip()
                        )

                    # Detect join/leave/server messages
                    elif any(kw in line.lower() for kw in ["joined", "left", "disconnected", "connected"]):
                        send_to_discord_webhook(
                            username="Serene Branson",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )

        except Exception as e:
            print(f"🔥 Error: {e}")

        await asyncio.sleep(10)

# Run the async loop
if __name__ == "__main__":
    try:
        asyncio.run(ark_chat_listener())
    except KeyboardInterrupt:
        print("Bot shutting down.")
