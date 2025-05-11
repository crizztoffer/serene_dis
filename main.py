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
            result = mcr.command("getchat")  # Replace with your actual Ark RCON command
            return result.strip()
    except Exception as e:
        print(f"Ark chat fetch error: {e}")
        return ""

def send_to_ark_chat(message):
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f'serverchat {message}')
    except Exception as e:
        print(f"Ark send error: {e}")

@client.event
async def on_ready():
    print("Bot is ready.")
    asyncio.create_task(poll_ark_chat())

@client.event
async def on_message(message):
    global last_discord_message, last_ark_message

    if message.channel.id != DISCORD_CHANNEL_ID or message.author == client.user:
        return

    display_name = message.author.display_name
    content = message.content.strip()
    print(f"[DISCORD] {display_name}: {content}")

    # Format and strip "Server: "
    formatted = f"{display_name}: {content}"
    formatted_for_ark = formatted.replace("Server: ", "")

    # Prevent reposting the same message back to Ark
    if formatted_for_ark != last_ark_message:
        send_to_ark_chat(formatted_for_ark)
        last_discord_message = content
    else:
        print("[SKIP] Message from Discord matches last Ark message. Skipping repost.")

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
                # You can post to Discord here if desired

        await asyncio.sleep(5)

client.run(DISCORD_TOKEN)
