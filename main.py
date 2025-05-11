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
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Discord setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# Bridge: Keep track of last Ark and Discord messages
last_ark_message = None
last_discord_message = None

def get_last_messages():
    """ Get the latest messages from both Ark and Discord """
    return {
        "ark": last_ark_message,
        "discord": last_discord_message
    }

def set_last_ark_message(message):
    """ Set the last Ark message """
    global last_ark_message
    last_ark_message = message

def set_last_discord_message(message):
    """ Set the last Discord message """
    global last_discord_message
    last_discord_message = message

# Send message to Discord webhook
def send_to_discord_webhook(username, content, avatar_url=None):
    global last_ark_message, last_discord_message

    # Check if the message from Ark should be skipped
    if last_ark_message and content == last_ark_message['content'] and username == last_ark_message['username']:
        return

    if not avatar_url:
        avatar_url = "https://serenekeks.com/dis_ark.png"

    payload = {
        "username": f"{username} - Ark: Survival Evolved",
        "content": content,
        "avatar_url": avatar_url
    }

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code != 204:
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
                        if name.strip().endswith("(Discord)"):
                            continue
                        
                        send_to_discord_webhook(name.strip(), message.strip())
                        set_last_ark_message({'username': name.strip(), 'content': message.strip()})

                    elif any(kw in line.lower() for kw in ["joined", "left", "disconnected", "connected"]):
                        send_to_discord_webhook(
                            username="Serene Branson - Ark: Survival Evolved",
                            content=line.strip(),
                            avatar_url="https://serenekeks.com/serene2.png"
                        )
        except Exception as e:
            print(f"🔥 RCON read error: {e}")
        await asyncio.sleep(10)

# Relay messages from Discord → Ark
@client.event
async def on_message(message):
    global last_discord_message

    if message.author.bot:
        return
    if message.channel.id != DISCORD_CHANNEL_ID:
        return

    content = f"{message.author.display_name} (Discord): {message.content}"
    print(f"💬 Sending to Ark: {content}")

    # Store the last Discord message
    set_last_discord_message({'username': message.author.display_name, 'content': message.content})

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {content}")

        # Store the Ark message (to avoid sending the same message back to Discord)
        set_last_ark_message({'username': message.author.display_name + " (Discord)", 'content': message.content})

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
