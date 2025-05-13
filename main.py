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
GMOD_AVATAR_URL = "https://serenekeks.com/dis_gmod.png"

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
# Helpers
# ───────────────────────────────

async def send_to_discord(username, message, avatar_url):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(content=message, username=username, avatar_url=avatar_url)

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ───────────────────────────────
# GMod → ARK + Discord
# ───────────────────────────────

@app.route('/from_gmod.php', methods=['POST'])
def handle_gmod():
    try:
        data = request.get_json()
        username = data.get("username", "Unknown")
        message = data.get("message", "")
        
        # Use provided Avatar_Url, fallback to GMOD_AVATAR_URL if missing/blank
        avatar_url = data.get("Avatar_Url")
        if not avatar_url or avatar_url.strip() == "":
            avatar_url = GMOD_AVATAR_URL

        unique_id = f"{username}|{message}"
        if unique_id == getattr(handle_gmod, "last_msg", None):
            print("[SKIP] Duplicate GMod message.")
            return jsonify({"status": "duplicate"}), 200
        handle_gmod.last_msg = unique_id

        print(f"[GMod → Discord+ARK] {username}: {message}")

        # Send to Discord
        asyncio.run_coroutine_threadsafe(
            send_to_discord(f"[GMod] {username}", message, avatar_url),
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

                            # Send to Discord
                            await send_to_discord(f"[ARK] {raw_username}", message, ARK_AVATAR_URL)

                            # Relay to GMod
                            if GMOD_ENABLED:
                                try:
                                    gmod_message = f"ARK|{raw_username}|Ark: Survival Unleashed|{message}"
                                    print(f"[ARK → GMod] Relaying: {gmod_message}")
                                    with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as gmod_rcon:
                                        gmod_rcon.command(f"lua_run PrintChatFromConsole([[{gmod_message}]])")
                                    print("[ARK → GMod] Sent successfully.")
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
    # Only proceed if it's the correct channel and not a bot or webhook
    if message.channel.id != DISCORD_CHANNEL_ID:
        return
    if message.author.bot:
        return
    if message.webhook_id is not None:
        return  # ✅ Prevent loop: ignore webhook-based messages

    author = message.author.display_name
    content = message.content

    print(f"[DISCORD] Message from {author}: {content}")

    # Relay to ARK
    try:
        print("[DISCORD → ARK] Attempting to send...")
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            ark_message = f"[DISCORD] {author}: {content}"
            mcr.command(f"serverchat {ark_message}")
            print("[DISCORD → ARK] Sent successfully.")
    except Exception as e:
        print(f"[ERROR] Discord → ARK failed: {e}")

    # Relay to GMod
    try:
        GMOD_RCON_IP = os.getenv("GMOD_RCON_IP")
        GMOD_RCON_PORT = int(os.getenv("GMOD_RCON_PORT", "0"))
        GMOD_RCON_PASSWORD = os.getenv("GMOD_RCON_PASS")
        if GMOD_RCON_IP and GMOD_RCON_PORT and GMOD_RCON_PASSWORD:
            print("[DISCORD → GMod] Attempting to send...")
            with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as gmod_rcon:
                gmod_message = f"DISCORD|{author}|Discord|{content}"
                gmod_rcon.command(f"lua_run PrintChatFromConsole([[{gmod_message}]])")
                print("[DISCORD → GMod] Sent successfully.")
    except Exception as e:
        print(f"[ERROR] Discord → GMod failed: {e}")

    await bot.process_commands(message)

# ───────────────────────────────
# Entrypoint
# ───────────────────────────────

@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    print(f"[INFO] Watching Discord channel: {DISCORD_CHANNEL_ID}")
    bot.loop.create_task(debug_get_chat())

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    asyncio.run(bot.start(DISCORD_TOKEN))
