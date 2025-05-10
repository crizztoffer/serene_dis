import asyncio
import os
from mcrcon import MCRcon
import discord

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

async def ark_to_discord():
    while True:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("ListPlayers")
                if response:
                    channel = client.get_channel(CHANNEL_ID)
                    await channel.send(f"[ARK] {response.strip()}")
        except Exception as e:
            print(f"Error reading from Ark RCON: {e}")
        await asyncio.sleep(30)  # polling interval

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    client.loop.create_task(ark_to_discord())

@client.event
async def on_message(message):
    if message.channel.id == CHANNEL_ID and not message.author.bot:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                mcr.command(f"broadcast [DISCORD] {message.author.name}: {message.content}")
        except Exception as e:
            print(f"Error sending message to Ark: {e}")

client.run(DISCORD_TOKEN)
