import os
import discord
import asyncio
import re
import aiohttp
from discord.ext import commands
from mcrcon import MCRcon

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
AVATAR_URL = "https://serenekeks.com/dis_ark.png"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

# Set up the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global variable to track last seen line
last_line = ""

async def send_to_discord(username, message):
    """Send a message from Ark to Discord."""
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(
            content=message,
            username=username,
            avatar_url=AVATAR_URL
        )

async def monitor_ark_chat():
    """Poll ARK server for new chat messages."""
    global last_line
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                # Command to get recent chat messages or logs from the server
                response = mcr.command('getchat')  # Hypothetical command; check with your server

                # Check if there are new messages
                if response:
                    # Here we assume 'response' contains a string with chat messages
                    if response != last_line:
                        last_line = response
                        username, message = parse_chat_line(response)
                        if username and message:
                            await send_to_discord(username, message)
        except Exception as e:
            print(f"[ERROR] RCON Error: {e}")
        
        await asyncio.sleep(1)  # Poll every 5 seconds to avoid server overload

def parse_chat_line(line):
    """Parse chat line from ARK server log."""
    # Example of parsing format "PlayerName: Message"
    # Assuming the chat message follows a format like: 'PlayerName: Message'
    match = re.search(r'(\w+): (.*)', line)
    if match:
        username = match.group(1)
        message = match.group(2)
        return username, message
    return None, None

@bot.event
async def on_message(message):
    """Handle messages from Discord and send them to ARK in-game chat."""
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    # Format the message for RCON
    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            # Send the message to ARK global chat using RCON
            mcr.command(f'ServerChat {rcon_message}')  # Replace 'ServerChat' with appropriate command
    except Exception as e:
        print(f"[ERROR] Sending to ARK via RCON failed: {e}")

    await bot.process_commands(message)

# Update the main function to avoid direct `loop` usage
async def main():
    """Main function to start bot and chat monitoring."""
    await asyncio.gather(bot.start(DISCORD_TOKEN), monitor_ark_chat())  # Start bot and monitoring chat concurrently

# Start the bot using asyncio.run for async execution
if __name__ == "__main__":
    asyncio.run(main())
