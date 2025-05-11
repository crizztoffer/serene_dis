import asyncio
import os
from ftplib import FTP
import discord
from mcrcon import MCRcon
import time

# Environment variables for Discord and FTP credentials
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PORT = int(os.getenv("FTP_PORT", 21))  # Default FTP port is 21
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "/ShooterGame/Saved/Logs/ShooterGame.log")  # Path to ARK log file

# RCON configuration (if you still use RCON for sending messages back to ARK)
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", 0))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

last_discord_message = ""
last_ark_message = ""

# Tracking log file position to avoid re-reading the same content
log_file_position = 0

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Function to fetch the log file from FTP server
def fetch_log_file():
    ftp = FTP()
    ftp.connect(FTP_HOST, FTP_PORT)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd(os.path.dirname(LOG_FILE_PATH))

    with open("ShooterGame.log", "wb") as local_file:
        ftp.retrbinary("RETR " + os.path.basename(LOG_FILE_PATH), local_file.write)

    ftp.quit()

# Function to monitor the log file for new lines
def monitor_log():
    global log_file_position

    # Fetch the latest log file from FTP
    fetch_log_file()

    # Read the log file and check for new lines
    with open("ShooterGame.log", "r") as file:
        file.seek(log_file_position)
        new_lines = file.readlines()

        if new_lines:
            log_file_position = file.tell()  # Update position after reading
            for line in new_lines:
                handle_log_line(line.strip())

# Function to handle each line in the log
def handle_log_line(line):
    if "Chat" in line and ": " in line:
        parts = line.split("]:")[-1].strip()
        if ": " in parts:
            player, message = parts.split(": ", 1)
            formatted_message = f"[Ark] {player} >> {message}"
            print(f"[ARK CHAT] {formatted_message}")

            # If the message is not a duplicate, send it to Discord
            if formatted_message != last_ark_message:
                send_to_discord(formatted_message)
                last_ark_message = formatted_message

# Function to send messages to Discord channel
async def send_to_discord(message):
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send(message)

# Function to handle messages from Discord
@client.event
async def on_message(message):
    global last_discord_message, last_ark_message

    if message.channel.id != DISCORD_CHANNEL_ID or message.author == client.user:
        return

    # Format the Discord message and prevent reposting the same message
    display_name = message.author.display_name
    content = message.content.strip()
    formatted = f"[Discord] {display_name} >> {content}"
    print(f"[DISCORD] {formatted}")

    if formatted != last_discord_message:
        send_to_ark_chat(formatted)
        last_discord_message = formatted
    else:
        print("[SKIP] Message from Discord matches last Ark message. Skipping repost.")

# Function to send messages to ARK server (using RCON)
def send_to_ark_chat(message):
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f'serverchat {message}')
    except Exception as e:
        print(f"Ark send error: {e}")

# Function to poll Discord chat periodically
async def poll_discord_chat():
    while True:
        # Poll ARK log every 5 seconds
        monitor_log()
        await asyncio.sleep(5)

# Run the bot
@client.event
async def on_ready():
    print("Bot is ready.")
    asyncio.create_task(poll_discord_chat())

client.run(DISCORD_TOKEN)
