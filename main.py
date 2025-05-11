import asyncio
import os
from mcrcon import MCRcon
import discord

# Environment variables (from Railway)
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Keep track of last Discord message to prevent echo
last_discord_message = {"username": "", "content": ""}

# Send to Discord using the bot client
async def send_to_discord(username, content):
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        formatted = f"**{username} - (Ark: Survival Evolved):** {content}"
        await channel.send(formatted)

# Ark chat listener (reads from Ark, sends to Discord)
async def ark_chat_listener():
    seen_lines = set()
    await client.wait_until_ready()

    while True:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                chat = mcr.command("GetChat")
                lines = chat.split("\n")

                for line in lines:
                    if line in seen_lines or ": " not in line:
                        continue

                    seen_lines.add(line)
                    name, msg = line.split(": ", 1)
                    name = name.strip()
                    msg = msg.strip()

                    # Skip if matches last message sent from Discord
                    if (name == last_discord_message["username"] and
                        msg == last_discord_message["content"]):
                        continue

                    await send_to_discord(name, msg)

        except Exception as e:
            print(f"🔥 RCON read error: {e}")

        await asyncio.sleep(5)

# Relay from Discord → Ark
@client.event
async def on_message(message):
    global last_discord_message

    if message.author.bot or message.channel.id != DISCORD_CHANNEL_ID:
        return

    username = f"{message.author.display_name} - (Discord):"
    content = message.content.strip()

    last_discord_message["username"] = message.author.display_name
    last_discord_message["content"] = content

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {username} {content}")
    except Exception as e:
        print(f"🔥 Error sending to Ark: {e}")

# Run both Discord bot and Ark listener
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
