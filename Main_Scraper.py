import re
import os
import discord
import aiohttp
import base64
import json
from datetime import datetime, timezone

# Alt account discord token inside of the RS Discord
DISCORD_TOKEN = ""

# Discord webhook URL for posting boss spawns
DISCORD_WEBHOOK_URL = ""

#Leave as is
GUILD_ID = 1207550411024769024
CHANNEL_ID = 1348415113228718151

#Name of logging file
UNMATCH_LOG = "unmatched.log"

#Testing mode (Disables posting the logs)
TEST_MODE = False

#Stats for logging screen
success_count = 0
fail_count = 0
skip_count = 0
chat_count = 0

SKIP_BOSSES = {"dragon", "ice dragon", "isekal", "mother spider", "runic whale"}

SERVER_KEYWORDS = set(
    k.lower()
    for k in [
        "amulet","ancient","arcane","ash","ashen","ashenblade","ashenforged","axe","baleful","bane",
        "banner","banneret","bear","berserking","blaw","blaze","blazing","bleeding","bless","blessed",
        "blessing","blightwoven","blood","bloodborn","bloodied","bloodspike","bloom","bone-carved",
        "bonecarved""boneforged","born","bracelet","bracers","brand","bright","brimstone","brittle",
        "brutal","bunny","burning","burnished","cairn","carver","cataclysm","celestial","celestine",
        "censer","chalice","chaosforged","charm","chilled","cindersong","cindertouched","coil",
        "corrupted","covenant","cowl","cowlbrand","crescent","crest","crossbow","crown","crownblade",
        "crumbling","crystal","cudgel","curse","cursed","dagger","dark","darkwoven","dawnborn",
        "dawnlit","dazzling","deathblessed","deathless","dimlit","doomed","dreadbound","dreadshard",
        "dreadwoven","dreambound","duskwoven","ebon","echo","echoing","eclipse","edge","ember",
        "emberforged","emblem","enchanted","esclipse","eternal","fangblade","fanged","fangroot",
        "fangshade","feather","feral","firewoven","fissure","flamekissed","flare","flarebound","flaring",
        "flash","flesh","fleshroot","forsaken","frigid","frostbitten","frostfang","frostwoven","frostwrought",
        "frozen","fury","gauntlet","gauntlets","ghostcarved","ghostwoven","gilded","glaive","gleaming",
        "gleamstone","glimmering","gllowing","gloomy","glorybound","glowless","glyph","golden","grave",
        "gravebound","grim","grimdark","grimoire","hallowed","hammer","harmony","heavenly","hellwoven",
        "helm","hollowcore", "howl", "howling","husk","idol","infernim","ironbound","ironclad","ironshod",
        "lantern","lightborn","lightforged","lightshard","lightwoven","lucky","lunar","lurking","lyre","mace",
        "maelstrom","marbled","mark","mask","melodial","mirage","mistforged","mistveil","molten","moonbound",
        "moonkissed","moonlit","moonstone","moonveil","mystic","netherwoven","netherwovern","nightbloom",
        "nightforged", "noble","nullstone","oath","oathbound","oathburned","obsidian","onyx","pact","phantom",
        "plagued","poisonous","pylon","pyrebound","radiant","relic","rimebound","ring","root","runed","runescribed",
        "savage","scalded","scarred","seeker","sentinel","severance","shackle","shade","shadowy","shard","shardblade",
        "shield","shifting","shimmering","silent","silver","singed","sinister","skybound","skybreaker","skyfallen",
        "slowstone","snapped","snare","sootwoven","soul-bound","soulbound","soulcarved","soulforged","sparkwoven",
        "spasmroot","specter","spectral","spellglass","spindle","spindleheart","spine","spiral","spire","spireling",
        "spiritbound","splintered","staff","starborne","starcursed","starfallen","starforged","stoneborn","stonehewn",
        "stormbound","stormcarved","stormkissed","stormlit","stormrender","stormveil","stormwoven","stormy","sunborn",
        "sword","talisman","tarnished","tearful","thorn","thornbound","thrice-blessed","thronw","thunderous","tome","torch",
        "totemstone","tunic","twined","twinkling","unholy","veil","veiled","vengeful","vine","voidcarved","voidtouched",
        "vow","waning","warped","whip","whisperborn","whispering","windcarved","windwoven","wisp","wound","wraithborn",
        "zephyr","sigil","dusken","cage","totem","quiver","vile","emberlit","shadowed","bow","cradle","feathered","phylactery",
        "scepter","emberbound","voidborn","faint","verdict","obelisk","orb","redfang","warden","cuirass","glowing","floe",
        "sting","starlit","twilight","blighted","crownroot","seraphim","flaming","merciless","throne","draconic","thrice",
        "fiery","spear","chime","wild","grave","holy","crownblade","gravebound","stormkissed","Ruin","Lock","crownroot",
        "deathblessed","burnished","medallion","withered","mirrored","glowstone","pendant","runescribed","runed",
        "boots","hollow","blade""relicstone"])

BOSS_LIST = [
    "Razor Fang",
    "Dire Bear",
    "Elder Treant",
    "Rune Golem",
    "Vangar",
    "Wyvern",
    "Licht King",
    "Yeti",
    "Goblin King",
    "Mother Spider",
    "Runic Whale",
    "Darius",
]

REGION_LIST = [
    "Oregon, US",
    "California, US",
    "Texas, US",
    "North West SG",
    "Hesse, DE",
    "Florida, US",
    "North Holland NL",
    "Washington, US",
]

REGION_ALIASES = {
    "Oregon, US": ["oregon", "or", "org"],
    "California, US": ["california", "ca", "cali", "san fran", "los angeles", "la"],
    "Texas, US": ["texas", "tx"],
    "Florida, US": ["florida", "fl"],
    "Washington, US": ["washington", "wa"],
    "North Holland NL": ["north holland", "holland", "nl"],
    "Hesse, DE": ["hesse", "de", "germany"],
    "North West SG": ["north west sg", "sg", "singapore"],
}

BOSS_ATTRIBUTES = {
    "Slime King": {"color": 0x7CFC00, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/8/89/SlimeKing.png"},  # lime green
    "Mandrake King": {"color": 0x006400, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/8/8c/Mandrakeking.png"},  # dark green
    "Goblin Champion": {"color": 0x556B2F, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/5/54/GoblinChampion.png"},  # olive drab
    "The Rat King": {"color": 0xA9A9A9, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/d/d4/RatKing.png"},  # dark gray
    "Razor Fang": {"color": 0xB22222, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/c/c2/RazorFang.png"},  # firebrick red
    "Dire Bear": {"color": 0x5C4033, "thumbnail": "https://i.imgur.com/Nq2ZACt.png"},  # deep brown
    "Basilisk": {"color": 0x2E8B57, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/b/b1/Basilisk.png"},  # sea green
    "Mother Spider": {"color": 0x4B0082, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/2/2f/MotherSpider.png"},  # dark purple
    "Elder Treant": {"color": 0x8FBC8F, "thumbnail": "https://i.imgur.com/vyRfdZA.png"},  # dark sea green
    "Rune Golem": {"color": 0x4169E1, "thumbnail": "https://i.imgur.com/RRPN84j.png"},  # royal blue
    "Drogar": {"color": 0x708090, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/b/bb/Drogar.png"},  # slate gray
    "The Champion of the Colosseum": {"color": 0xFFD700, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/6/6f/Lycanthar_First_phase.png"},  # gold
    "Vangar": {"color": 0xFFD700, "thumbnail": "https://i.imgur.com/FQNt1EW.png"},  # (unchanged)
    "Goblin King": {"color": 0x6B8E23, "thumbnail": "https://i.imgur.com/NUy9UsB.png"},  # olive green
    "Licht King": {"color": 0xDCDCDC, "thumbnail": "https://i.imgur.com/BrSCQXv.png"},  # gainsboro (light gray)
    "Wyvern": {"color": 0xFFFFFF, "thumbnail": "https://i.ytimg.com/vi/6QwrJP_94ag/hq720.jpg?sqp=-oaymwEhCK4FEIIDSFryq4qpAxMIARUAAAAAGAElAADIQj0AgKJD&rs=AOn4CLAosxZp3eZr1J6m9OsspYeYDYL_yQ"},  # snow white
    "Ferdinand": {"color": 0x8B0000, "thumbnail": "https://i.imgur.com/FQNt1EW.png"},  # dark red (vampire)
    "Karlor": {"color": 0x8B0000, "thumbnail": "https://i.imgur.com/FQNt1EW.png"},     # dark red (vampire)
    "Draul": {"color": 0x8B0000, "thumbnail": "https://i.imgur.com/FQNt1EW.png"},      # dark red (vampire)
    "Whale": {"color": 0x1E90FF, "thumbnail": "https://i.ytimg.com/vi/AMosl5yam0c/hq720.jpg?sqp=-oaymwEhCK4FEIIDSFryq4qpAxMIARUAAAAAGAElAADIQj0AgKJD&rs=AOn4CLAyJN0_mG8p_2o8O7BRwRhDKr97lA"},  # dodger blue
    "Yeti": {"color": 0xADD8E6, "thumbnail": "https://static.wikia.nocookie.net/rune-slayerrblx/images/d/d2/Yeti.jpg/revision/latest?cb=20250617023021"},  # light blue
    "Darius": {"color": 0x8B0000, "thumbnail": "https://ddragon.leagueoflegends.com/cdn/img/champion/tiles/Darius_15.jpg"}      # dark red (Darius)
}

STOP_WORDS = {"for", "invite", "lf", "pre"}

SERVER_BLACKLIST = {"tree", "tront", "treat", "elder", "licht", "elden","treant"}

WEAK_PREFIXES = {
    "axe",
    "mace",
    "talisman",
    "amulet",
    "staff",
    "banner",
    "relic",
    "torch",
    "chalice",
    "idol",
    "mask",
}

PING_ROLES_ENABLED = True

#Place Role Ids for pings here if you use that
BOSS_PING_ROLES = {
    "Slime King": 123,
    "Mandrake King": 123 , 
    "Goblin Champion": 123, 
    "The Rat King": 123, 
    "Razor Fang": 123,  
    "Dire Bear": 123,  
    "Basilisk": 123, 
    "Mother Spider": 123 ,  
    "Elder Treant": 123,  
    "Rune Golem": 123,  
    "Vangar": 123, 
    "Goblin King": 123,  
    "Licht King": 123,  
    "Wyvern": 123,  
    "Ferdinand": 123,  
    "Karlor": 123,    
    "Draul": 123,      
    "Whale": 123,
    "Yeti": 123, 
    "Darius": 123 
}

client = discord.Client()

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
            if any(alias == w for w in tail):
                return region
    return "N/A"

def strip_region(msg: str, region: str) -> str:
    for alias in REGION_ALIASES.get(region, []):
        msg = re.sub(rf"[,\s]*{re.escape(alias)}[,\s]*", " ", msg, flags=re.IGNORECASE)
    return msg.strip()

def find_best_server_candidate(tokens):
    best_count = 0
    best_chunk = None
    used_fuzzy = []

    for window in [3, 4]:
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
                    if (j > 0 and lows[j - 1] in SERVER_KEYWORDS) or (j < len(lows) - 1 and lows[j + 1] in SERVER_KEYWORDS):
                        count += 1
                else:
                    for kw in SERVER_KEYWORDS:
                        if levenshtein(w, kw) == 1:
                            if (j > 0 and lows[j - 1] in SERVER_KEYWORDS) or (j < len(lows) - 1 and lows[j + 1] in SERVER_KEYWORDS):
                                count += 1
                                fuzzy_info.append((w, kw))
                                break
            if count > best_count:
                best_count = count
                best_chunk = chunk
                used_fuzzy = fuzzy_info

    if best_chunk and best_count >= 3:
        corrected = []
        for w in [w.lower() for w in best_chunk]:
            if w in SERVER_KEYWORDS:
                corrected.append(w.capitalize())
            else:
                match = next((kw for kw in SERVER_KEYWORDS if levenshtein(w, kw) == 1), w)
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
        for original, corrected in fuzzy_used:
            print(f"\033[95m[~]\033[0m Fuzzy match: '{original}' → '{corrected}'")
    return {
        "boss": boss,
        "server": server,
        "region": region,
        "content": f"{sanitize_text(raw)}\npureontop"
    }, None

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
        with open(UNMATCH_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} | {single} | boss_guess={boss_guess} | server_cand={server_cand!r}\n")

    print(
        f"\033[94mStats:\033[0m ✅ {success_count}  ❌ {fail_count}  ⏭️ {skip_count}  💬 {chat_count}",
        end="\r",
        flush=True,
    )

async def send_discord_webhook(payload: dict):
    boss = payload["boss"]
    attr = BOSS_ATTRIBUTES.get(boss, {})

    embed = {
        "description": (
            f"**{boss} Has Spawned**\n"
            f"**Server Name:**  \n{payload['server']}\n"
            f"**Server Region:**  \n{payload['region']}"
        ),
        "color": attr.get("color", 0x5BCEFA),
        "footer": {"text": "Purity Scraper | Made with <3 by Pure"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if "thumbnail" in attr:
        embed["thumbnail"] = {"url": attr["thumbnail"]}

    content = None
    if PING_ROLES_ENABLED and boss in BOSS_PING_ROLES:
        role_id = BOSS_PING_ROLES[boss]
        content = f"<@&{role_id}>"

    json_body = {"embeds": [embed]}
    if content:
        json_body["content"] = content

    async with aiohttp.ClientSession() as session:
        await session.post(DISCORD_WEBHOOK_URL, json=json_body)

@client.event
async def on_ready():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"[READY] Logged in as {client.user} (ID: {client.user.id})")
    print(f"Monitoring Guild {GUILD_ID}, Channel {CHANNEL_ID}\n")

@client.event
async def on_message(message):
    if message.guild and message.guild.id == GUILD_ID and message.channel.id == CHANNEL_ID:
        await handle_message(message.content)

client.run(DISCORD_TOKEN)
