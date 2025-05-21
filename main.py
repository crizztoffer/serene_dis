import os
import asyncio
import discord
from discord.ext import commands
from mcrcon import MCRcon
from flask import Flask, request, jsonify
import re
import aiohttp
import urllib.parse
from threading import Thread

# Constants
WEBHOOK_URL = "https://discord.com/api/webhooks/" + os.getenv("WEBHOOK_URL")
ARK_AVATAR_URL = "https://serenekeks.com/dis_ark.png"
GMOD_AVATAR_URL = "https://serenekeks.com/dis_gmod.png"
SERENE_AVATAR_URL = "https://serenekeks.com/serene2.png"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "0"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)
last_seen_ark_message = None
last_seen_gmod_message = None

# ───────────────────────────────
# Serene Session State
# ───────────────────────────────
serene_sessions = {}

# ───────────────────────────────
# Helper Functions
# ───────────────────────────────

def is_duplicate(source, username, message):
    global last_seen_ark_message, last_seen_gmod_message
    identifier = f"{username}|{message}"
    if source == "ARK":
        if identifier == last_seen_ark_message:
            return True
        last_seen_ark_message = identifier
    elif source == "GMod":
        if identifier == last_seen_gmod_message:
            return True
        last_seen_gmod_message = identifier
    return False

async def send_to_discord(username, message, avatar_url):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(content=message, username=username, avatar_url=avatar_url)

async def get_steam_avatar(steamid: str) -> str:
    if not STEAM_API_KEY:
        return GMOD_AVATAR_URL
    url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_API_KEY}&steamids={steamid}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                players = data.get("response", {}).get("players", [])
                if players:
                    return players[0].get("avatarfull", GMOD_AVATAR_URL)
    except Exception as e:
        print("[ERROR] Failed to fetch Steam avatar:", e)
    return GMOD_AVATAR_URL

async def relay_to_ark_and_gmod(username, message):
    ark_message = f"{username}: {message}"
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"serverchat {ark_message}")
    except Exception as e:
        print("[ERROR] Serene → ARK failed:", e)

    GMOD_RCON_IP = os.getenv("GMOD_RCON_IP")
    GMOD_RCON_PORT = int(os.getenv("GMOD_RCON_PORT", "0"))
    GMOD_RCON_PASSWORD = os.getenv("GMOD_RCON_PASS")

    if GMOD_RCON_IP and GMOD_RCON_PORT and GMOD_RCON_PASSWORD:
        try:
            with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as gmod_rcon:
                gmod_msg = f"SERENE|{username}|Serene|{message}"
                gmod_rcon.command(f"lua_run PrintChatFromConsole([[{gmod_msg}]])")
        except Exception as e:
            print("[ERROR] Serene → GMod failed:", e)

# ───────────────────────────────
# Serene Handlers
# ───────────────────────────────

async def handle_serene_start(source, username, message):
    serene_key = f"{source}|{username}"
    serene_sessions[serene_key] = True

    serene_start = urllib.parse.quote_plus(message)
    p_name = urllib.parse.quote_plus(username)

    url = f"https://serenekeks.com/serene_bot.php?start={serene_start}&player={p_name}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            body = await resp.text()
            await send_to_discord("Serene Branson", body, SERENE_AVATAR_URL)
            await relay_to_ark_and_gmod("Serene", body)

async def handle_serene_question(source, username, message):
    serene_key = f"{source}|{username}"
    if serene_sessions.get(serene_key):
        del serene_sessions[serene_key]

        question = urllib.parse.quote_plus(message)
        p_name = urllib.parse.quote_plus(username)

        url = f"https://serenekeks.com/serene_bot.php?question={question}&player={p_name}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                body = await resp.text()
                await send_to_discord("Serene Branson", body, SERENE_AVATAR_URL)
                await relay_to_ark_and_gmod("Serene", body)
        return True
    return False

# ───────────────────────────────
# Flask Endpoint (GMod → ARK + Discord)
# ───────────────────────────────

@app.route('/from_gmod.php', methods=['POST'])
def handle_gmod():
    try:
        data = request.get_json()
        username = data.get("username", "Unknown")
        message = data.get("message", "")
        steamid = data.get("steamid")
        source = "GMod"

        if is_duplicate(source, username, message):
            return jsonify({"status": "duplicate_skipped"}), 200

        print(f"[GMod → Discord+ARK] {username}: {message}")

        async def process():
            avatar_url = await get_steam_avatar(steamid) if steamid else GMOD_AVATAR_URL
        
            if message.lower() in ("!serene", "/serene"):
                await handle_serene_start("GMod", username, message)
            elif await handle_serene_question("GMod", username, message):
                return
            else:
                await send_to_discord(f"[{source}] {username}", message, avatar_url)

        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                mcr.command(f"serverchat [GMod] {username}: {message}")
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
                        source = "ARK"
                        
                        # Try Serene trigger
                        if message.lower() in ("!serene", "/serene"):
                            await handle_serene_start("ARK", raw_username, message)
                        elif await handle_serene_question("ARK", raw_username, message):
                            continue  # Serene already replied
                        
                        # Else, send normally
                        if is_duplicate(source, raw_username, message):
                            continue
                        
                        username = f"[{source}] {raw_username}"
                        await send_to_discord(username, message, ARK_AVATAR_URL)

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

    content = message.content.strip()
    username = message.author.display_name
    content_lower = content.lower()
    source = "DISCORD"

    if content_lower in ("!serene", "/serene"):
        await handle_serene_start(source, username, content.lstrip("!/"))
        return

    if await handle_serene_question(source, username, content):
        return

    # Relay to ARK and GMod
    discord_message = f"[DISCORD] {username}: {content}"
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            mcr.command(f"serverchat {discord_message}")

        GMOD_RCON_IP = os.getenv("GMOD_RCON_IP")
        GMOD_RCON_PORT = int(os.getenv("GMOD_RCON_PORT", "0"))
        GMOD_RCON_PASSWORD = os.getenv("GMOD_RCON_PASS")

        if GMOD_RCON_IP and GMOD_RCON_PORT and GMOD_RCON_PASSWORD:
            with MCRcon(GMOD_RCON_IP, GMOD_RCON_PASSWORD, port=GMOD_RCON_PORT) as gmod_rcon:
                gmod_msg = f"DISCORD|{username}|Discord|{content}"
                gmod_rcon.command(f"lua_run PrintChatFromConsole([[{gmod_msg}]])")

    except Exception as e:
        print("[ERROR] Discord relay failed:", e)

    await bot.process_commands(message)

# ───────────────────────────────
# Entrypoint
# ───────────────────────────────

def run_flask():
    app.run(host="0.0.0.0", port=8080)

@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user.name}")
    bot.loop.create_task(debug_get_chat())

if __name__ == '__main__':
    Thread(target=run_flask).start()
    asyncio.run(bot.start(DISCORD_TOKEN))
