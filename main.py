import asyncio
import os
import discord
from mcrcon import MCRcon
import paramiko
import aiohttp

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
AVATAR_URL = "https://serenekeks.com/dis_ark.png"

# Env variables from Railway
FTP_HOST = os.getenv("FTP_HOST")
FTP_PORT = int(os.getenv("FTP_PORT", "22"))
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "/path/to/ShooterGame.log")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

last_discord_message = ""
last_ark_message = ""

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def send_ark_message_to_discord(username, message):
    payload = {
        "username": username,
        "content": message,
        "avatar_url": AVATAR_URL
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(WEBHOOK_URL, json=payload) as response:
            if response.status != 204:
                print(f"Failed to send to Discord. Status: {response.status}")
            else:
                print(f"Sent Ark chat as {username}: {message}")


def get_ark_chat():
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            result = mcr.command("getchat")
            return result.strip()
    except Exception:
        return ""


def send_to_ark_chat(message):
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f'serverchat {message}')
    except Exception:
        pass


def fetch_log_file():
    try:
        transport = paramiko.Transport((FTP_HOST, FTP_PORT))
        transport.connect(username=FTP_USER, password=FTP_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)

        sftp.get(LOG_FILE_PATH, "ShooterGame.log")
        sftp.close()
        transport.close()
    except Exception:
        pass


def monitor_log():
    fetch_log_file()
    if not os.path.exists("ShooterGame.log"):
        return ""

    with open("ShooterGame.log", "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        if lines:
            return lines[-1].strip()
    return ""


@client.event
async def on_ready():
    asyncio.create_task(poll_ark_chat())


@client.event
async def on_message(message):
    global last_discord_message, last_ark_message

    if message.channel.id != DISCORD_CHANNEL_ID or message.author == client.user:
        return

    display_name = message.author.display_name
    content = message.content.strip()

    if "- (Ark: Survival Evolved):" in display_name:
        return

    formatted_for_ark = f"Discord: {display_name}: {content}"

    if formatted_for_ark != last_ark_message:
        send_to_ark_chat(formatted_for_ark)
        last_discord_message = formatted_for_ark


async def poll_ark_chat():
    global last_ark_message, last_discord_message

    await client.wait_until_ready()
    while True:
        current_ark_message = monitor_log()
        if current_ark_message and current_ark_message != last_ark_message:
            last_ark_message = current_ark_message

            if ": Discord:" in current_ark_message:
                continue

            # Extract message from log line
            if "SERVER: " in current_ark_message:
                try:
                    message_text = current_ark_message.split("SERVER: ", 1)[1].strip()
                    if ":" in message_text:
                        username, message = message_text.split(":", 1)
                        username = username.strip() + " = (Ark: Survival Evolved)"
                        message = message.strip()
                        await send_ark_message_to_discord(username, message)
                except Exception as e:
                    print(f"Error parsing message: {e}")

        await asyncio.sleep(5)


client.run(DISCORD_TOKEN)
