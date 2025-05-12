import os
import asyncio
import discord
from discord.ext import commands
from mcrcon import MCRcon
import re
import aiohttp

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
AVATAR_URL = "https://serenekeks.com/dis_ark.png"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Used to prevent Discord echo
sent_from_discord = set()
last_seen_message = None

# Debug GMod RCON connection separately
async def debug_gmod_rcon():
    await bot.wait_until_ready()
    GMOD_RCON_IP = os.getenv("GMOD_RCON_IP")
    GMOD_RCON_PORT = os.getenv("GMOD_RCON_PORT")
    GMOD_RCON_PASSWORD = os.getenv("GMOD_RCON_PASS")

    if not GMOD_RCON_IP or not GMOD_RCON_PORT or not GMOD_RCON_PASSWORD:
        print("[ERROR] Missing one or more GMOD RCON environment variables.")
        print(f"GMOD_RCON_IP={GMOD_RCON_IP}, GMOD_RCON_PORT={GMOD_RCON_PORT}, GMOD_RCON_PASSWORD={'SET' if GMOD_RCON_PASSWORD else 'NOT SET'}")
        return

    try:
        GMOD_RCON_PORT = int(GMOD_RCON_PORT)
        with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as mcr:
            print("[INFO] Successfully connected to GMod RCON.")
            test_response = mcr.command("status")
            print(f"[GMOD RCON RESPONSE] {test_response}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to GMod RCON: {e}")

async def debug_get_chat():
    global last_seen_message
    await bot.wait_until_ready()

    # Prepare GMod RCON config
    GMOD_RCON_IP = os.getenv("GMOD_RCON_IP")
    GMOD_RCON_PORT = os.getenv("GMOD_RCON_PORT")
    GMOD_RCON_PASSWORD = os.getenv("GMOD_RCON_PASS")
    GMOD_ENABLED = GMOD_RCON_IP and GMOD_RCON_PORT and GMOD_RCON_PASSWORD

    if GMOD_ENABLED:
        try:
            GMOD_RCON_PORT = int(GMOD_RCON_PORT)
        except ValueError:
            print(f"[ERROR] Invalid GMOD_RCON_PORT: {GMOD_RCON_PORT}")
            GMOD_ENABLED = False

    while not bot.is_closed():
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("getchat")
                lines = response.splitlines()
                for line in lines:
                    match = re.match(r"^(.*?) \([^\)]+\): (.+)$", line)
                    if match:
                        raw_username = match.group(1)
                        message = match.group(2)
                        username = f"(Ark: Survival Evolved) {raw_username}"

                        if message != last_seen_message:
                            last_seen_message = message

                            # Send to Discord webhook
                            async with aiohttp.ClientSession() as session:
                                webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
                                await webhook.send(
                                    content=message,
                                    username=username,
                                    avatar_url=AVATAR_URL
                                )

                            # Send to GMod RCON
                            if GMOD_ENABLED:
                                try:
                                    with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as gmod_rcon:
                                        gmod_message = f"ARK|{raw_username}|Ark: Survival Unleashed|{message}"
                                        print(f"[INFO] Relaying to GMod: {gmod_message}")
                                        gmod_rcon.command(f"lua_run PrintChatFromConsole([[{gmod_message}]])")
                                except Exception as e:
                                    print(f"[ERROR] Failed to send message to GMod: {e}")

        except Exception as e:
            print("[ERROR] debug_get_chat:", e)

        await asyncio.sleep(1)


@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    bot.loop.create_task(debug_get_chat())  # Start debugging Ark chat
    bot.loop.create_task(debug_gmod_rcon())  # Start debugging GMod RCON connection

@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            print(f"[INFO] Sending to ARK: {rcon_message}")
            mcr.command(f"serverchat {rcon_message}")
    except Exception as e:
        print("[ERROR] RCON message failed:", e)

    await bot.process_commands(message)

if __name__ == '__main__':
    asyncio.run(bot.start(DISCORD_TOKEN))
