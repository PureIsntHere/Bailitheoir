import os
import re
import json
import discord
import aiohttp
import configparser
from datetime import datetime, timezone

# Directories and files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.ini')
DATA_DIR = os.path.join(BASE_DIR, 'data')
UNMATCH_LOG = os.path.join(BASE_DIR, 'unmatched.log')

# Discord and channel settings (modify if needed)
GUILD_ID = 1207550411024769024
CHANNEL_ID = 1348415113228718151

# Default config values
DEFAULT_CONFIG = {
    'DISCORD_TOKEN': '',
    'DISCORD_WEBHOOK_URL': '',
    'TEST_MODE': 'False'
}

def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        config['DEFAULT'] = DEFAULT_CONFIG
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
    config.read(CONFIG_FILE)
    return config['DEFAULT']

# Load config
cfg = load_config()
DISCORD_TOKEN = cfg.get('DISCORD_TOKEN', '')
DISCORD_WEBHOOK_URL = cfg.get('DISCORD_WEBHOOK_URL', '')
TEST_MODE = cfg.getboolean('TEST_MODE', False)

# Helper to load JSON files
def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required data file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load data modules
SKIP_BOSSES      = set(load_json('skip_bosses.json'))
SERVER_KEYWORDS  = set(load_json('server_keywords.json'))
BOSS_LIST        = load_json('boss_list.json')
REGION_LIST      = load_json('region_list.json')
REGION_ALIASES   = load_json('region_aliases.json')
BOSS_ATTRIBUTES  = load_json('boss_attributes.json')
BOSS_PING_ROLES  = load_json('boss_ping_roles.json')

# Constants for parsing
STOP_WORDS        = {"for", "invite", "lf", "pre"}
SERVER_BLACKLIST  = {"tree", "tront", "treat", "elder", "licht", "elden", "treant"}
WEAK_PREFIXES     = {"axe","mace","talisman","amulet","staff","banner","relic","torch","chalice","idol","mask"}
PING_ROLES_ENABLED = True

# Discord client
client = discord.Client()

# Text normalization helpers

def sanitize_text(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9 \-]", "", text)

def normalize_text(msg: str) -> str:
    return re.sub(r"(.)\1{2,}", r"\1\1", msg)

def levenshtein(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 1:
        return 2
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            ins = prev[j] + 1
            dele = curr[j - 1] + 1
            rep = prev[j - 1] + (ca != cb)
            curr.append(min(ins, dele, rep))
        prev = curr
        if min(prev) > 1:
            return 2
    return prev[-1]

# Parsing functions

def get_boss(msg: str):
    low = msg.lower()
    if re.search(r"\bmama spider\b|\bmother spider\b|\bspider\b", low):
        return "Mother Spider"
    if re.search(r"\bice dragon\b|\bdragon\b", low):
        return "Dragon"
    if re.search(r"\bwhale\b", low):
        return "Runic Whale"
    if re.search(r"\btront|treat|trent|tree|elder|treant\b", low):
        return "Elder Treant"
    if re.search(r"\blicht king\b", low):
        return "Licht King"
    for b in BOSS_LIST:
        if b.lower() in low:
            return b
    tokens = msg.replace("-", " ").split()
    boss_lowers = [b.lower() for b in BOSS_LIST]
    for size in (2, 1):
        for i in range(len(tokens) - size + 1):
            phrase = " ".join(tokens[i:i + size]).lower()
            for bl in boss_lowers:
                if levenshtein(phrase, bl) <= 1:
                    return BOSS_LIST[boss_lowers.index(bl)]
    return None


def get_region(msg: str, exclude_words=None):
    low = re.sub(r"[^A-Za-z0-9\s]", "", msg.lower())
    words = low.split()
    for region, aliases in REGION_ALIASES.items():
        for alias in aliases:
            if alias in words and (not exclude_words or alias not in exclude_words):
                return region
    tail = words[-3:] if len(words) >= 3 else words
    for region, aliases in REGION_ALIASES.items():
        for alias in aliases:
            if alias in tail:
                return region
    return "N/A"


def strip_region(msg: str, region: str) -> str:
    for alias in REGION_ALIASES.get(region, []):
        msg = re.sub(rf"[\,\s]*{re.escape(alias)}[\,\s]*", " ", msg, flags=re.IGNORECASE)
    return msg.strip()


def find_best_server_candidate(tokens):
    best_count = 0
    best_chunk = None
    used_fuzzy = []
    for window in (3, 4):
        for i in range(len(tokens) - window + 1):
            chunk = tokens[i:i + window]
            lows = [w.lower() for w in chunk]
            if any(w in STOP_WORDS or w in SERVER_BLACKLIST for w in lows):
                continue
            if lows[0] in WEAK_PREFIXES:
                continue
            count = 0
            fuzzy_info = []
            for j, w in enumerate(lows):
                if w == "king":
                    continue
                if w in SERVER_KEYWORDS:
                    if ((j > 0 and lows[j-1] in SERVER_KEYWORDS) or (j < len(lows)-1 and lows[j+1] in SERVER_KEYWORDS)):
                        count += 1
                else:
                    for kw in SERVER_KEYWORDS:
                        if levenshtein(w, kw) == 1 and ((j > 0 and lows[j-1] in SERVER_KEYWORDS) or (j < len(lows)-1 and lows[j+1] in SERVER_KEYWORDS)):
                            count += 1
                            fuzzy_info.append((w, kw))
                            break
            if count > best_count:
                best_count, best_chunk, used_fuzzy = count, chunk, fuzzy_info
    if best_chunk and best_count >= 3:
        corrected = []
        for w in best_chunk:
            lw = w.lower()
            if lw in SERVER_KEYWORDS:
                corrected.append(lw.capitalize())
            else:
                match = next((kw for kw in SERVER_KEYWORDS if levenshtein(lw, kw) == 1), lw)
                corrected.append(match.capitalize())
        return " ".join(corrected), best_count, used_fuzzy
    return None, 0, []

def find_valid_server(tokens):
    server, count, fuzzy_used = find_best_server_candidate(tokens)
    return (server, fuzzy_used) if count >= 3 else (None, [])


def parse_message(raw: str):
    if re.search(r"\b(dm me|farm|farming|chat|invite|trading)\b", raw.lower()):
        return None, "chat-invite"
    single = normalize_text(raw)
    boss = get_boss(single)
    if not boss:
        return None, "no boss match"
    if boss.lower() in SKIP_BOSSES:
        return {"boss": boss}, "hourly"
    region = get_region(single, exclude_words=SERVER_KEYWORDS)
    cleaned = strip_region(single, region) if region != "N/A" else single
    cleaned = re.sub(re.escape(boss), "", cleaned, flags=re.IGNORECASE).strip()
    tokens = re.sub(r"[^A-Za-z0-9\s\-]", "", cleaned).split()
    server, fuzzy_used = find_valid_server(tokens)
    if not server:
        return None, "no server match"
    if fuzzy_used:
        for orig, corr in fuzzy_used:
            print(f"\033[95m[~]\033[0m Fuzzy match: '{orig}' → '{corr}'")
    return {"boss": boss, "server": server, "region": region, "content": f"{sanitize_text(raw)}\npureontop"}, None

# Stats counters
success_count = fail_count = skip_count = chat_count = 0

async def handle_message(raw: str):
    global success_count, fail_count, skip_count, chat_count
    single = " ".join(raw.split())
    payload, error = parse_message(single)
    if error == "chat-invite":
        chat_count += 1
    elif error == "hourly":
        skip_count += 1
        print(f"\033[93m⚠\033[0m Skipped hourly boss: {payload['boss']} | \"{single}\"")
    elif error is None:
        success_count += 1
        print(f"\033[92m✔\033[0m {payload['boss']} | {payload['region']} | {payload['server']} | \"{single}\"")
        if not TEST_MODE:
            await send_discord_webhook(payload)
    else:
        fail_count += 1
        boss_guess = get_boss(single) or "None"
        server_cand, _, _ = find_best_server_candidate(single.replace("-", " ").split())
        with open(UNMATCH_LOG, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} | {single} | boss_guess={boss_guess} | server_cand={server_cand!r}\n")
    print(
        f"\033[94mStats:\033[0m ✅ {success_count}  ❌ {fail_count}  ⏭️ {skip_count}  💬 {chat_count}",
        end="\r",
        flush=True
    )

async def send_discord_webhook(payload: dict):
    boss = payload['boss']
    attr = BOSS_ATTRIBUTES.get(boss, {})
    embed = {
        'description': (
            f"**{boss} Has Spawned**\n"
            f"**Server Name:**  \n{payload['server']}\n"
            f"**Server Region:**  \n{payload['region']}"
        ),
        'color': attr.get('color', 0x5BCEFA),
        'footer': {'text': 'Purity Scraper | Made with <3 by Pure'},
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    if 'thumbnail' in attr:
        embed['thumbnail'] = {'url': attr['thumbnail']}  
    content = f"<@&{BOSS_PING_ROLES[boss]}>" if PING_ROLES_ENABLED and boss in BOSS_PING_ROLES else None
    json_body = {'embeds': [embed]}
    if content:
        json_body['content'] = content
    async with aiohttp.ClientSession() as session:
        await session.post(DISCORD_WEBHOOK_URL, json=json_body)

@client.event
async def on_ready():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"[READY] Logged in as {client.user} (ID: {client.user.id})")
    print(f"Monitoring Guild {GUILD_ID}, Channel {CHANNEL_ID}\n")

@client.event
async def on_message(message):
    if message.guild and message.guild.id == GUILD_ID and message.channel.id == CHANNEL_ID:
        await handle_message(message.content)

client.run(DISCORD_TOKEN)
