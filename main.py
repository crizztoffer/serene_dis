import os
import asyncio
import discord
from discord.ext import commands
from mcrcon import MCRcon
from flask import Flask, request, jsonify
import json
import re
import aiohttp
from threading import Thread

# ─────────── Configuration ───────────

WEBHOOK_URL = "https://discord.com/api/webhooks/1030875305784655932/CmwhTWO-dWmGjCpm9LYd4nAWXZe3QGxrSUVfpkDYfVo1av1vgLxgzeXRMGLE7PmVOdo8"
ARK_AVATAR_URL = "https://serenekeks.com/dis_ark.png"
GMOD_AVATAR_URL = "https://serenekeks.com/dis_gmod.png"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

GMOD_RCON_IP = os.getenv("GMOD_RCON_IP")
GMOD_RCON_PORT = int(os.getenv("GMOD_RCON_PORT", "0"))
GMOD_RCON_PASSWORD = os.getenv("GMOD_RCON_PASS")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
app = Flask(__name__)
last_seen_ark_message = None

# ─────────── Discord Webhook Sender ───────────

async def send_to_discord(username, message, avatar_url):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(content=message, username=username, avatar_url=avatar_url)

# ─────────── Flask Endpoint for GMod Messages ───────────

@app.route('/from_gmod.php', methods=['POST'])
def handle_gmod():
    try:
        data = request.get_json()
        if not data:
            data = json.loads(request.data.decode("utf-8"))

        print("[FROM GMOD] Data received:", data)

        username = data.get("username", "Unknown")
        message = data.get("message", "")
        source = "Garry's Mod"
        avatar_url = data.get("Avatar_Url") or GMOD_AVATAR_URL

        # Send to Discord
        asyncio.run_coroutine_threadsafe(
            send_to_discord(f"[{source}] {username}", message, avatar_url),
            bot.loop
        )

        # Relay to ARK
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

# ─────────── ARK → Discord + GMod ───────────

async def debug_get_chat():
    global last_seen_ark_message
    await bot.wait_until_ready()

    GMOD_ENABLED = GMOD_RCON_IP and GMOD_RCON_PORT and GMOD_RCON_PASSWORD

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
                        username = f"[Ark] {raw_username}"
                        full_message_id = f"{raw_username}|{message}"

                        if full_message_id != last_seen_ark_message:
                            last_seen_ark_message = full_message_id

                            # Send to Discord
                            await send_to_discord(username, message, ARK_AVATAR_URL)

                            # Relay to GMod
                            if GMOD_ENABLED:
                                try:
                                    gmod_message = f"ARK|{raw_username}|Ark: Survival Unleashed|{message}"
                                    with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as gmod_rcon:
                                        gmod_rcon.command(f"lua_run PrintChatFromConsole([[{gmod_message}]])")
                                except Exception as e:
                                    print("[ERROR] GMod relay failed:", e)

        except Exception as e:
            print("[ERROR] debug_get_chat:", e)

        await asyncio.sleep(1)

# ─────────── Discord → ARK + GMod ───────────

@bot.event
async def on_message(message):
    if message.channel.id != DISCORD_CHANNEL_ID or message.author.bot:
        return

    discord_message = f"[DISCORD] {message.author.display_name}: {message.content}"

    try:
        # Relay to ARK
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"serverchat {discord_message}")

        # Relay to GMod
        if GMOD_RCON_IP and GMOD_RCON_PORT and GMOD_RCON_PASSWORD:
            gmod_message = f"DISCORD|{message.author.display_name}|Discord|{message.content}"
            with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as gmod_rcon:
                gmod_rcon.command(f"lua_run PrintChatFromConsole([[{gmod_message}]])")

    except Exception as e:
        print("[ERROR] Discord relay failed:", e)

    await bot.process_commands(message)

# ─────────── Flask Thread + Bot Entry ───────────

def run_flask():
    app.run(host="0.0.0.0", port=8080)

@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    bot.loop.create_task(debug_get_chat())

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    asyncio.run(bot.start(DISCORD_TOKEN))
