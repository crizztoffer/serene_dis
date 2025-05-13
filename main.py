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
AVATAR_URL = "https://serenekeks.com/dis_ark.png"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)
last_seen_message = None

# ───────────────────────────────
# Flask Endpoint for GMod → Discord + ARK
# ───────────────────────────────

@app.route('/from_gmod.php', methods=['POST'])
def handle_gmod():
    try:
        data = request.get_json()
        username = data.get("username", "Unknown")
        source = data.get("source", "Garry's Mod")
        message = data.get("message", "")
        avatar_url = data.get("Avatar_Url", AVATAR_URL)

        print(f"[GMod → Discord] {username}: {message} (Avatar: {avatar_url})")

        # Send to Discord webhook
        asyncio.run_coroutine_threadsafe(
            send_to_discord(f"({source}) {username}", message, avatar_url),
            bot.loop
        )

        # Send to ARK
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                ark_message = f"[{source}] {username}: {message}"
                mcr.command(f"serverchat {ark_message}")
        except Exception as e:
            print("[ERROR] Failed to send to ARK:", e)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("[ERROR] /from_gmod.php:", e)
        return jsonify({"status": "error", "detail": str(e)}), 500

async def send_to_discord(username, message, avatar_url=AVATAR_URL):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(content=message, username=username, avatar_url=avatar_url)

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ───────────────────────────────
# Ark → Discord + GMod Relay
# ───────────────────────────────

async def debug_get_chat():
    global last_seen_message
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
                        username = f"(Ark) {raw_username}"

                        if message != last_seen_message:
                            last_seen_message = message

                            # Send to Discord with Ark avatar
                            await send_to_discord(username, message)

                            # Relay to GMod
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
# Optional: Check GMod RCON
# ───────────────────────────────

async def debug_gmod_rcon():
    await bot.wait_until_ready()
    GMOD_RCON_IP = os.getenv("GMOD_RCON_IP")
    GMOD_RCON_PORT = os.getenv("GMOD_RCON_PORT")
    GMOD_RCON_PASSWORD = os.getenv("GMOD_RCON_PASS")

    if not GMOD_RCON_IP or not GMOD_RCON_PORT or not GMOD_RCON_PASSWORD:
        print("[ERROR] Missing GMod RCON credentials.")
        return

    try:
        GMOD_RCON_PORT = int(GMOD_RCON_PORT)
        with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as mcr:
            test_response = mcr.command("status")
            print(f"[GMod RCON] Connected: {test_response}")
    except Exception as e:
        print(f"[ERROR] GMod RCON connection failed: {e}")

# ───────────────────────────────
# Discord Events
# ───────────────────────────────

@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    bot.loop.create_task(debug_get_chat())
    bot.loop.create_task(debug_gmod_rcon())

@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    rcon_message = f"[DISCORD] {message.author.display_name}: {message.content}"
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"serverchat {rcon_message}")
    except Exception as e:
        print("[ERROR] Discord → ARK failed:", e)

    await bot.process_commands(message)

# ───────────────────────────────
# Entrypoint
# ───────────────────────────────

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    asyncio.run(bot.start(DISCORD_TOKEN))
