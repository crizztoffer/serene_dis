import asyncio
import os
import discord
from mcrcon import MCRcon
import paramiko

# Env variables from Railway (same names as before)
FTP_HOST = os.getenv("FTP_HOST")
FTP_PORT = int(os.getenv("FTP_PORT", "22"))  # SFTP usually uses port 22
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "/path/to/ShooterGame.log")  # Update default as needed

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

        sftp.get(LOG_FILE_PATH, "ShooterGame.log")  # Save locally
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

    # Prevent reposting if message contains "- (Ark: Survival Evolved):"
    if "- (Ark: Survival Evolved):" in display_name:
        return  # Do nothing if the message is from Ark (to prevent reposting)

    # Format the message for Ark
    formatted_for_ark = f"Discord: {display_name}: {content}"

    if formatted_for_ark != last_ark_message:
        send_to_ark_chat(formatted_for_ark)
        last_discord_message = formatted_for_ark

    current_ark_message = monitor_log()
    if last_discord_message == current_ark_message:
        pass
    else:
        pass


# New function to send Ark messages to Discord
async def send_ark_message_to_discord(username, message):
    # Format the message to be posted to Discord
    formatted_message = f"{username} - (Ark: Survival Evolved): {message}"
    
    # Send the message to Discord with the specific avatar URL
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send(formatted_message, avatar_url="https://serenekeks.com/dis_ark.png")


async def poll_ark_chat():
    global last_ark_message, last_discord_message

    await client.wait_until_ready()
    while True:
        current_ark_message = monitor_log()
        if current_ark_message and current_ark_message != last_ark_message:
            last_ark_message = current_ark_message

            # If the current Ark message does not contain Discord, send it to Discord
            if "Discord:" not in current_ark_message:
                # Assuming Ark messages contain the format "Username: Message"
                parts = current_ark_message.split(": ", 1)
                if len(parts) == 2:
                    username, message = parts
                    await send_ark_message_to_discord(username, message)

        await asyncio.sleep(5)


client.run(DISCORD_TOKEN)
