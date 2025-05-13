import os
import asyncio
import discord
from discord.ext import commands
from mcrcon import MCRcon
from flask import Flask, request, jsonify
import re
import aiohttp
from threading import Thread

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
ARK_AVATAR_URL = "https://serenekeks.com/dis_ark.png"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)
last_seen_ark_message = None

# ───────────────────────────────
# Send Helpers
# ───────────────────────────────

async def send_to_discord(username, message, avatar_url=ARK_AVATAR_URL):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(content=message, username=username, avatar_url=avatar_url)

async def send_from_ark_to_discord(username, message):
    await send_to_discord(f"[ARK] {username}", message, ARK_AVATAR_URL)

async def send_from_gmod_to_discord(username, message, avatar_url=ARK_AVATAR_URL):
    await send_to_discord(f"[GMod] {username}", message, avatar_url)

async def send_from_discord_to_discord(username, message):
    await send_to_discord(f"[DISCORD] {username}", message)

# ───────────────────────────────
# Flask → GMod → ARK + Discord
# ───────────────────────────────

@app.route('/from_gmod.php', methods=['POST'])
def handle_gmod():
    try:
        data = request.get_json()
        username = data.get("username", "Unknown")
        message = data.get("message", "")
        avatar_url = data.get("Avatar_Url", ARK_AVATAR_URL)

        print(f"[GMod → Discord+ARK] {username}: {message}")

        # Send to Discord
        asyncio.run_coroutine_threadsafe(
            send_from_gmod_to_discord(username, message, avatar_url),
            bot.loop
        )

        # Send to ARK
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                ark_message = f"[GMod] {username}: {message}"
                mcr.command(f"serverchat {ark_message}")
        except Exception as e:
            print("[ERROR] Failed to send to ARK:", e)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("[ERROR] /from_gmod.php:", e)
        return jsonify({"status": "error", "detail": str(e)}), 500

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ───────────────────────────────
# ARK → GMod + Discord
# ───────────────────────────────

async def debug_get_chat():
    global last_seen_ark_message
    await bot.wait_until_ready()

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
                        full_message_id = f"{raw_username}|{message}"

                        if full_message_id != last_seen_ark_message:
                            last_seen_ark_message = full_message_id

                            # To Discord
                            await send_from_ark_to_discord(raw_username, message)

                            # To GMod
                            if GMOD_ENABLED:
                                try:
                                    with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as gmod_rcon:
                                        gmod_message = f"ARK|{raw_username}|Ark: Survival Unleashed|{message}"
                                        gmod_rcon.command(f"lua_run PrintChatFromConsole([[{gmod_message}]])")
                                except Exception as e:
                                    print("[ERROR] GMod relay failed:", e)

        except Exception as e:
            print("[ERROR] debug_get_chat:", e)

        await asyncio.sleep(1)

# ───────────────────────────────
# Discord → ARK + GMod
# ───────────────────────────────

@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    # Ignore webhook echo
    if message.webhook_id is not None:
        return

    author = message.author.display_name
    content = message.content

    # Echo to Discord
    await send_from_discord_to_discord(author, content)

    # Relay to ARK
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"serverchat [DISCORD] {author}: {content}")
    except Exception as e:
        print("[ERROR] Discord → ARK failed:", e)

    # Relay to GMod
    try:
        GMOD_RCON_IP = os.getenv("GMOD_RCON_IP")
        GMOD_RCON_PORT = int(os.getenv("GMOD_RCON_PORT", "0"))
        GMOD_RCON_PASSWORD = os.getenv("GMOD_RCON_PASS")
        if GMOD_RCON_IP and GMOD_RCON_PORT and GMOD_RCON_PASSWORD:
            with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as gmod_rcon:
                gmod_message = f"DISCORD|{author}|Discord|{content}"
                gmod_rcon.command(f"lua_run PrintChatFromConsole([[{gmod_message}]])")
    except Exception as e:
        print("[ERROR] Discord → GMod failed:", e)

    await bot.process_commands(message)

# ───────────────────────────────
# Entrypoint
# ───────────────────────────────

@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    bot.loop.create_task(debug_get_chat())

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    asyncio.run(bot.start(DISCORD_TOKEN))
