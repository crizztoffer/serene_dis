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
    except Exception as e:
        print(f"Error getting Ark chat: {e}")
        return ""


def send_to_ark_chat(message):
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f'serverchat {message}')
    except Exception as e:
        print(f"Error sending to Ark chat: {e}")
        pass


def fetch_log_file():
    try:
        transport = paramiko.Transport((FTP_HOST, FTP_PORT))
        transport.connect(username=FTP_USER, password=FTP_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)

        sftp.get(LOG_FILE_PATH, "ShooterGame.log")  # Save locally
        sftp.close()
        transport.close()
    except Exception as e:
        print(f"Error fetching log file: {e}")


def monitor_log():
    fetch_log_file()
    if not os.path.exists("ShooterGame.log"):
        print("Log file not found.")
        return ""

    with open("ShooterGame.log", "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        if lines:
            return lines[-1].strip()
    return ""


async def send_ark_message_to_discord(username, message):
    # Format the message to be sent to Discord in the specified format
    discord_message = f"{username} - (Ark: Survival Evolved): {message}"
    
    # Send the formatted message to Discord
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send(discord_message, avatar_url="https://serenekeks.com/dis_ark.png")
        print(f"Sent message to Discord: {discord_message}")  # Debug print
    else:
        print("Error: Discord channel not found.")  # Debug print


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="Ark: Survival Evolved"))
    

@client.event
async def on_message(message):
    global last_discord_message, last_ark_message

    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    print(f"Received message from Discord: {message.content}")  # Debug print

    # If the message is from Discord, check if it contains "Ark: Survival Evolved"
    if "- (Ark: Survival Evolved):" in message.content:
        print(f"Skipping message (already formatted): {message.content}")  # Debug print
        return  # Do nothing if the message is already in the correct format

    # If it's a new message from Discord, send it to Ark
    if message.channel.id == DISCORD_CHANNEL_ID:
        display_name = message.author.display_name
        content = message.content.strip()

        # Format the message for Ark
        formatted_for_ark = f"Discord: {display_name}: {content}"

        if formatted_for_ark != last_ark_message:
            print(f"Sending to Ark: {formatted_for_ark}")  # Debug print
            send_to_ark_chat(formatted_for_ark)
            last_discord_message = formatted_for_ark

    # If the message is from Ark (detected via log file), send it to Discord
    current_ark_message = monitor_log()
    if current_ark_message and current_ark_message != last_ark_message:
        print(f"Received Ark message: {current_ark_message}")  # Debug print
        last_ark_message = current_ark_message

        if "Discord:" not in current_ark_message:  # Ensure we don't send Discord messages back to Discord
            # Remove the "SERVER: Discord:" part from the Ark message
            clean_message = current_ark_message.split("Discord: ", 1)[-1] if "Discord: " in current_ark_message else current_ark_message

            # Split the Ark message into Username and Message
            parts = clean_message.split(": ", 1)
            if len(parts) == 2:
                username, message = parts
                await send_ark_message_to_discord(username, message)
            else:
                print(f"Failed to split Ark message: {current_ark_message}")  # Debug print


client.run(DISCORD_TOKEN)
