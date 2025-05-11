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

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Internal state to prevent echo loop
last_discord_message = {"username": "", "content": ""}

# --- Send to Discord using discord.py ---
async def send_to_discord(username, content):
    print(f"Preparing to send to Discord: Username: {username}, Content: {content}")

    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        print("❌ Channel not found!")
        return

    # Skip sending the message if it matches the last one from Discord
    if username == last_discord_message["username"] and content == last_discord_message["content"]:
        print("⚠️ Message is identical to last message from Discord. Skipping.")
        return

    print(f"✔️ Sending to Discord: {username} {content}")
    # Send the message to Discord
    await channel.send(f"{username} {content}")

# --- Poll Ark Chat and Send to Discord ---
async def ark_chat_listener():
    seen_lines = set()

    while True:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("GetChat")
                print(f"Received Ark Chat: {response}")  # Debug print to show received chat from Ark
                lines = response.split("\n")

                for line in lines:
                    if line in seen_lines:
                        continue
                    seen_lines.add(line)

                    if ": " in line:
                        name, msg = line.split(": ", 1)
                        clean_name = name.strip()
                        clean_msg = msg.strip()

                        # Ensure username is just the player's name, no duplication
                        clean_name = clean_name.split("(")[0].strip()

                        print(f"Ark message - Name: {clean_name}, Message: {clean_msg}")  # Debug print for Ark message
                        # Send to Discord
                        await send_to_discord(f"{clean_name} - (Ark: Survival Evolved):", clean_msg)

                    elif any(event in line.lower() for event in ["joined", "left", "disconnected", "connected"]):
                        print(f"Ark event message: {line.strip()}")  # Debug print for Ark event
                        await send_to_discord(
                            username="Server - (Ark: Survival Evolved):",
                            content=line.strip()
                        )

        except Exception as e:
            print(f"🔥 RCON read error: {e}")
        await asyncio.sleep(10)

# --- Relay from Discord → Ark ---
@client.event
async def on_message(message):
    global last_discord_message

    print(f"Received message from Discord - Author: {message.author.display_name}, Content: {message.content}")

    if message.author.bot or message.channel.id != DISCORD_CHANNEL_ID:
        print("⚠️ Message is from a bot or not the correct channel. Ignoring.")
        return

    username = f"{message.author.display_name} - (Discord):"
    content = message.content.strip()

    # Store last Discord message to prevent echo
    last_discord_message["username"] = username
    last_discord_message["content"] = content

    print(f"Storing message from Discord: {username} {content}")
    print(f"💬 Sending to Ark: {username} {content}")
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"ServerChat {username} {content}")
            print(f"✔️ Sent to Ark: {username} {content}")
    except Exception as e:
        print(f"🔥 Failed to send to Ark: {e}")

# --- Launch both tasks ---
async def main():
    await asyncio.gather(
        ark_chat_listener(),
        client.start(DISCORD_TOKEN)
    )

# --- AsyncIO Compatibility Fix for Railway ---
if __name__ == "__main__":
    try:
        print("Starting the bot...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutting down.")
