import asyncio
import os
from ark_rcon import ArkRcon
import discord

# Load environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

# Set up Discord client with message intents
intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

# Background task to read Ark chat and send to Discord
async def ark_to_discord():
    async with ArkRcon(RCON_HOST, RCON_PORT, RCON_PASSWORD) as rcon:
        while True:
            try:
                logs = await rcon.command("GetChat")  # Replace with correct log command if needed
                for line in logs.split('\n'):
                    if line.strip():
                        channel = client.get_channel(CHANNEL_ID)
                        await channel.send(f"In-game: {line.strip()}")
            except Exception as e:
                print(f"Error reading from Ark RCON: {e}")
            await asyncio.sleep(5)  # Poll every 5 seconds

# On bot ready, start the background loop
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    client.loop.create_task(ark_to_discord())

# Listen for messages from Discord to send to Ark
@client.event
async def on_message(message):
    if message.channel.id == CHANNEL_ID and not message.author.bot:
        async with ArkRcon(RCON_HOST, RCON_PORT, RCON_PASSWORD) as rcon:
            try:
                await rcon.command(f"broadcast [DISCORD] {message.author}: {message.content}")
            except Exception as e:
                print(f"Error sending message to Ark: {e}")

# Start the Discord bot
client.run(DISCORD_TOKEN)
