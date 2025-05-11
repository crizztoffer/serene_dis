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
last_sent_message = ""  # Track the last sent message

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

    # Final message format: Discord: Username: Message
    formatted_for_ark = f"Discord: {display_name}: {content}"

    if formatted_for_ark != last_ark_message:
        send_to_ark_chat(formatted_for_ark)
        last_discord_message = formatted_for_ark

    current_ark_message = monitor_log()
    if last_discord_message == current_ark_message:
        pass
    else:
        pass


async def poll_ark_chat():
    global last_ark_message, last_discord_message, last_sent_message

    await client.wait_until_ready()
    while True:
        current_ark_message = monitor_log()

        if current_ark_message and current_ark_message != last_ark_message:
            last_ark_message = current_ark_message

            # Check if the message contains "Server: Discord:"
            if "SERVER: Discord:" in current_ark_message:
                continue  # Skip sending this message as it has already been processed

            # Remove everything after the "SERVER: Discord:" portion
            # Trim the message starting from "SERVER: Discord:"
            trimmed_message = current_ark_message.split("SERVER: Discord:")[1].strip() if "SERVER: Discord:" in current_ark_message else current_ark_message

            # Ensure this is a new message before sending to Discord
            if trimmed_message != last_sent_message:
                last_sent_message = trimmed_message  # Update the last sent message
                # Send the message to Discord
                channel = client.get_channel(DISCORD_CHANNEL_ID)
                await channel.send(trimmed_message)

        await asyncio.sleep(5)


client.run(DISCORD_TOKEN)
