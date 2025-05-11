import asyncio
import os
from mcrcon import MCRcon
import discord

# Env variables from Railway
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

last_discord_message = ""
last_ark_message = ""

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def get_ark_chat():
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            result = mcr.command("getchat")  # Replace this with correct Ark chat-fetching command
            return result.strip()
    except Exception as e:
        print(f"Ark chat fetch error: {e}")
        return ""

@client.event
async def on_ready():
    print("Bot is ready.")
    asyncio.create_task(poll_ark_chat())

@client.event
async def on_message(message):
    global last_discord_message, last_ark_message

    # Ignore the bot's own messages and messages from other channels
    if message.channel.id != DISCORD_CHANNEL_ID or message.author == client.user:
        return

    # Get username as seen in Discord (case-sensitive)
    username = message.author.name
    print(f"[DISCORD] {username}: {message.content}")

    # Update last Discord message
    last_discord_message = message.content.strip()

    # Fetch Ark chat message and compare
    current_ark_message = get_ark_chat()
    if last_discord_message == current_ark_message:
        print(f"[MATCH] Discord and Ark message: '{last_discord_message}'")
    else:
        print(f"[DIFFERENT] Discord: '{last_discord_message}'")
        print(f"[DIFFERENT] Ark:     '{current_ark_message}'")

async def poll_ark_chat():
    global last_ark_message, last_discord_message

    await client.wait_until_ready()
    while True:
        current_ark_message = get_ark_chat()
        if current_ark_message and current_ark_message != last_ark_message:
            last_ark_message = current_ark_message
            if current_ark_message == last_discord_message:
                print(f"[MATCH] Ark and Discord message: '{current_ark_message}'")
            else:
                print(f"[DIFFERENT] Ark:     '{current_ark_message}'")
                print(f"[DIFFERENT] Discord: '{last_discord_message}'")
        await asyncio.sleep(5)

client.run(DISCORD_TOKEN)
