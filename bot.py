import datetime
import json
import os
import re
import time
import unicodedata

import aiohttp
import discord
from aiohttp import web
from discord import app_commands
from discord.ext import tasks

from joblog_guard import guard
from top10_embed import build_top10_embed

TOKEN = os.getenv("TOKEN") or os.environ["DISCORD_BOT_TOKEN"]
DATA_URL = os.getenv(
    "APEX_DATA_URL",
    "https://apextransporte.github.io/data.json",
)
CACHE_SECONDS = 60
FETCH_TIMEOUT = 8

# If your apex_drivers.json uses other field names, change them here.
FIELDS = {
    "name": ["name", "driver", "username", "display_name", "displayName", "nickname", "discord_name"],
    "level": ["level", "lvl"],
    "net_worth": [
        "net_worth", "networth", "netWorth", "net", "balance", "money",
        "net_value", "total_net_worth", "totalNetWorth", "worth", "wealth", "assets",
    ],
    "distance": ["distance", "distance_km", "distanceKm", "total_distance", "km", "kms", "kilometers"],
    "income": ["income", "total_income", "earnings", "revenue"],
    "time": ["time", "driving_time", "drivingTime", "total_time", "hours", "driving_hours", "playtime"],
    "last_km": ["last_km"],
    "last_income": ["last_income"],
    "last_date": ["last_date"],
    "jobs": ["jobs", "job_count", "job_log", "jobLog", "runs", "total_runs", "totalRuns", "deliveries", "total_jobs"],
}

# East Africa Time (Uganda) is UTC+3 all year. No daylight saving.
EAT = datetime.timezone(datetime.timedelta(hours=3), name="EAT")

RED = discord.Color.from_rgb(200, 16, 46)
LEADERBOARD_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID", "0"))

# Logo file sits in the repo next to bot.py.
LOGO_PATH = "apex_logo.png"
HAS_LOGO = os.path.exists(LOGO_PATH)
FOOTER = "Apex Transporte \u2022 Use /leaderboard for rankings"

RANKS = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}

DOT = "\U0001F539"

_cache = {"data": None, "time": 0.0, "raw": None}

# Last known net worth for each driver. This keeps the value on screen
# when the data file loses it. It is saved to a file so it survives restarts.
NW_FILE = "networth_cache.json"
NET_WORTH_SAVED = {}
try:
    with open(NW_FILE, "r", encoding="utf-8") as _f:
        NET_WORTH_SAVED = json.load(_f)
except Exception:
    NET_WORTH_SAVED = {}


def save_net_worth():
    try:
        with open(NW_FILE, "w", encoding="utf-8") as f:
            json.dump(NET_WORTH_SAVED, f)
    except Exception as error:
        print(f"Net worth save error: {error!r}", flush=True)


def words(text):
    """Lower case words of a name, without Apex tags, flags and symbols."""
    text = str(text).replace("\u2122", " ").replace("_", " ")
    text = unicodedata.normalize("NFKC", text).lower()
    found = re.split(r"[^\w]+", text)
    return [w for w in found if w and w not in ("apex", "the", "tm")]


def find_driver(drivers, query):
    """Find a driver by exact name, part of a name, or the words of a Discord name like Apex | keem."""
    q = str(query).strip().lower().lstrip("@")
    for d in drivers:
        if str(get(d, "name", "")).lower() == q:
            return d
    for d in drivers:
        if q and q in str(get(d, "name", "")).lower():
            return d
    qw = words(q)
    if qw:
        for d in drivers:
            dw = words(get(d, "name", ""))
            if dw and (all(w in dw for w in qw) or all(w in qw for w in dw)):
                return d
    return None


def squash(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def find_in(obj, wanted, depth=0):
    """Look for a field in the driver and also inside any nested block like stats."""
    if not isinstance(obj, dict) or depth > 3:
        return None
    for key, value in obj.items():
        if squash(key) in wanted and value not in (None, "") and not isinstance(value, (dict, list)):
            return value
    for value in obj.values():
        if isinstance(value, dict):
            found = find_in(value, wanted, depth + 1)
            if found is not None:
                return found
    return None


def get(driver, field, default=0):
    for key in FIELDS[field]:
        if key in driver and driver[key] not in (None, ""):
            return driver[key]
    wanted = {squash(k) for k in FIELDS[field]}
    found = find_in(driver, wanted)
    if found is not None:
        return found
    return default


def num(value):
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).lower()
        for junk in (",", "km", "$", "\u20ac", " "):
            text = text.replace(junk, "")
        if text.endswith("m"):
            return float(text[:-1]) * 1_000_000
        if text.endswith("k"):
            return float(text[:-1]) * 1_000
        return float(text)
    except ValueError:
        return 0.0


def fmt(value):
    return f"{num(value):,.0f}"


def worth_text(driver):
    """Net worth as text. Shows n/a when the value is missing, never a fake zero."""
    value = num(get(driver, "net_worth"))
    return f"\u20AC{value:,.0f}" if value > 0 else "n/a"


def short(value):
    n = num(value)
    return f"{n / 1000:.1f}k" if n >= 1000 else f"{n:,.0f}"


def compact(value):
    """1250000 becomes 1.25M, 48200 becomes 48.2k."""
    n = num(value)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return f"{n:,.0f}"


def hours(value):
    """Turn 13918h 41m, 971 or 1.1k into hours as a number."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).lower()
    match = re.search(r"(\d[\d,]*)\s*h(?:\D+(\d+)\s*m)?", text)
    if match:
        return float(match.group(1).replace(",", "")) + float(match.group(2) or 0) / 60
    return num(value)


def fmt_time(total_hours):
    whole = int(total_hours)
    minutes = int(round((total_hours - whole) * 60))
    return f"{whole}h {minutes}m"


def job_count(value):
    if isinstance(value, list):
        return len(value)
    return int(num(value))


def logo_file():
    """A fresh file object is needed for every message."""
    return discord.File(LOGO_PATH) if HAS_LOGO else discord.utils.MISSING


def style(embed):
    if HAS_LOGO:
        embed.set_thumbnail(url="attachment://apex_logo.png")
    embed.set_footer(text=FOOTER)
    return embed


def parse_date(text):
    try:
        when = datetime.datetime.fromisoformat(str(text))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return when


DIVIDER = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"


def totals_embed(drivers):
    """Company wide numbers for every Apex driver, shown as full figures."""
    total_km = sum(num(get(d, "distance")) for d in drivers)
    total_worth = sum(num(get(d, "net_worth")) for d in drivers)
    total_income = sum(num(get(d, "income")) for d in drivers)
    total_time = sum(hours(get(d, "time")) for d in drivers)
    total_jobs = sum(job_count(get(d, "jobs")) for d in drivers)

    embed = discord.Embed(
        title="🏢  APEX TRANSPORTE  •  COMPANY TOTALS",
        description=f"All time results from **{len(drivers):,} Apex drivers**.\n{DIVIDER[:12]}",
        color=RED,
    )
    embed.add_field(name="📦  Total Jobs", value=f"{total_jobs:,}", inline=True)
    embed.add_field(name="🛣️  Distance", value=f"{total_km:,.0f} km", inline=True)
    embed.add_field(name="⏱️  Driving Time", value=f"{total_time:,.0f} hours", inline=True)
    embed.add_field(name="💎  Net Worth", value=f"\u20AC{total_worth:,.0f}", inline=True)
    embed.add_field(name="💵  Income", value=f"€{total_income:,.0f}", inline=True)
    embed.add_field(name="👥  Drivers", value=f"{len(drivers):,}", inline=True)
    if HAS_LOGO:
        embed.set_thumbnail(url="attachment://apex_logo.png")
    return embed


def board_embed(title, emoji, drivers, key, unit="", daily=False):
    getter = (lambda d: hours(get(d, key))) if key == "time" else (lambda d: num(get(d, key)))
    ranked = sorted(drivers, key=getter, reverse=True)[:5]

    lines = []
    for i, d in enumerate(ranked, start=1):
        level = num(get(d, "level"))
        lvl = f"  •  Level {level:,.0f}" if level else ""
        lines.append(
            f"{RANKS.get(i, DOT)}  **{get(d, 'name', 'Unknown')}**{lvl}\n"
            f"> {fmt(get(d, 'distance'))} km   |   {worth_text(d)}   |   {job_count(get(d, 'jobs')):,} jobs"
        )
    legend = "🛣️ Distance   💰 Net Worth   📦 Jobs"
    body = "\n\n".join(lines) or "No data yet."
    return discord.Embed(
        title=f"🏆  {title}  {emoji}",
        description=f"{legend}\n{DIVIDER}\n\n{body}",
        color=RED,
    )


def active_embed(drivers):
    """Drivers who logged a job in the last 24 hours."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    active = []
    for d in drivers:
        when = parse_date(get(d, "last_date", ""))
        if when and when >= cutoff:
            active.append((when, d))
    active.sort(key=lambda item: item[0], reverse=True)

    embed = discord.Embed(title="🔥  ON THE ROAD TODAY", color=discord.Color.from_rgb(46, 204, 113))
    if not active:
        embed.description = "No jobs logged in the last 24 hours.\nBe the first on the road today! 🚛"
        return embed

    lines = []
    for when, d in active[:10]:
        stamp = int(when.timestamp())
        lines.append(
            f"🟢  **{get(d, 'name', 'Unknown')}**\n"
            f"> {fmt(get(d, 'last_km'))} km   |   €{fmt(get(d, 'last_income'))}   |   <t:{stamp}:R>"
        )
    extra = len(active) - 10
    if extra > 0:
        lines.append(f"➕  **{extra}** more drivers delivered today")
    plural = "s" if len(active) != 1 else ""
    embed.description = (
        f"**{len(active)}** driver{plural} finished a job in the last 24 hours. Great work, Apex! 👏\n"
        f"🛣️ Distance   💵 Earned   🕒 Finished\n{DIVIDER}\n\n" + "\n\n".join(lines)
    )
    return embed


def build_report(drivers, title, emoji, key):
    """Three embeds in one message: company totals, top 10, drivers active today."""
    embeds = [totals_embed(drivers), board_embed(title, emoji, drivers, key), active_embed(drivers)]
    date_text = datetime.datetime.now(EAT).strftime("%d %b %Y")
    footer = f"🔴⚫ Apex Transporte • {date_text} • Log your jobs to get featured!"
    if HAS_LOGO:
        embeds[-1].set_footer(text=footer, icon_url="attachment://apex_logo.png")
    else:
        embeds[-1].set_footer(text=footer)
    return embeds


def keep_net_worth(drivers):
    """Save each driver's net worth. Fill it back in when the data file loses it."""
    changed = False
    for d in drivers:
        name = squash(get(d, "name", ""))
        if not name:
            continue
        current = num(get(d, "net_worth"))
        if current > 0:
            if NET_WORTH_SAVED.get(name) != current:
                NET_WORTH_SAVED[name] = current
                changed = True
        elif name in NET_WORTH_SAVED:
            d["net_worth"] = NET_WORTH_SAVED[name]
    if changed:
        save_net_worth()


async def load_drivers():
    """Return driver data. Uses a 60 second cache and falls back to old data on errors."""
    now = time.time()
    if _cache["data"] is not None and now - _cache["time"] < CACHE_SECONDS:
        return _cache["data"]

    # The changing query value skips the GitHub Pages cache so new job logs show up sooner.
    url = f"{DATA_URL}?t={int(now)}"
    try:
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
        async with bot.session.get(url, timeout=timeout) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)
    except Exception:
        if _cache["data"] is not None:
            return _cache["data"]
        raise

    _cache["raw"] = data
    if isinstance(data, dict):
        found = []
        for key in ("members", "drivers"):  # data.json also has a text field named drivers, so only a list counts
            if isinstance(data.get(key), list):
                found = data[key]
                break
        data = found
    data = [d for d in data if isinstance(d, dict)]
    keep_net_worth(data)
    _cache["data"] = data
    _cache["time"] = now
    return data


async def start_web_server():
    """Small web page so Render sees an open port. Ping it every 5 minutes to stop sleep."""
    app = web.Application()

    async def health(request):
        return web.Response(text="ok")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "10000")))
    await site.start()


class ApexBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # needed so the bot sees screenshots in the joblog channel
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.session = None

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        await start_web_server()
        await self.tree.sync()

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()


bot = ApexBot()

DATA_ERROR = "Apex data is not available right now. Try again in a minute."


async def find_channel(channel_id):
    """Find a channel in the cache first, then ask Discord directly."""
    if not channel_id:
        return None
    channel = bot.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await bot.fetch_channel(channel_id)
    except Exception as error:
        print(f"Channel {channel_id} error: {error!r}", flush=True)
        return None


@bot.tree.command(name="stats", description="Show Apex Transporte team stats")
async def stats(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        drivers = await load_drivers()
    except Exception:
        await interaction.followup.send(DATA_ERROR)
        return
    total_distance = sum(num(get(d, "distance")) for d in drivers)
    total_worth = sum(num(get(d, "net_worth")) for d in drivers)
    total_income = sum(num(get(d, "income")) for d in drivers)
    total_time = sum(hours(get(d, "time")) for d in drivers)
    total_jobs = sum(job_count(get(d, "jobs")) for d in drivers)

    avg_km = total_distance / total_jobs if total_jobs else 0
    embed = discord.Embed(
        title="\U0001F3E2 Apex Transporte",
        description=f"Average run: **{avg_km:,.0f} km**",
        color=RED,
    )
    embed.add_field(name="\U0001F6E3\uFE0F Distance", value=f"{total_distance:,.0f} km", inline=True)
    embed.add_field(name="\u23F1\uFE0F Driving Time", value=fmt_time(total_time), inline=True)
    embed.add_field(name="\U0001F69A Total Runs", value=f"{total_jobs:,}", inline=True)
    embed.add_field(name="\U0001F4B5 Total Income", value=f"\u20AC{total_income:,.0f}", inline=True)
    embed.add_field(name="\U0001F4B0 Net Worth", value=f"\u20AC{total_worth:,.0f}", inline=True)
    embed.add_field(name="\U0001F464 Drivers", value=f"{len(drivers):,}", inline=True)
    await interaction.followup.send(embed=style(embed), file=logo_file())


@bot.tree.command(name="datacheck", description="Show the raw data fields the bot reads")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def datacheck(interaction: discord.Interaction):
    # Second lock: even if a server changes the command permissions, only admins get through.
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    try:
        drivers = await load_drivers()
    except Exception as error:
        await interaction.followup.send(f"{DATA_ERROR} ({error!r})")
        return
    raw = _cache["raw"]
    top = list(raw.keys()) if isinstance(raw, dict) else "a plain list"
    first = json.dumps(drivers[0], default=str)[:1200] if drivers else "no drivers"
    names = ", ".join(str(get(d, "name", "?")) for d in drivers[:15])
    with_worth = sum(1 for d in drivers if num(get(d, "net_worth")) > 0)
    text = (
        f"Top level: {top}\nDrivers: {len(drivers)}\nDrivers with net worth: {with_worth}\n"
        f"First entry: {first}\nNames: {names}"
    )
    await interaction.followup.send(text[:1900], ephemeral=True)


@bot.tree.command(name="joblog", description="Show the job log for one driver")
@app_commands.describe(driver="Driver name")
async def joblog(interaction: discord.Interaction, driver: str):
    await interaction.response.defer()
    try:
        drivers = await load_drivers()
    except Exception:
        await interaction.followup.send(DATA_ERROR)
        return
    match = find_driver(drivers, driver)
    if match is None:
        await interaction.followup.send(f"No driver found named {driver}.")
        return

    embed = discord.Embed(title=str(get(match, "name", driver)), color=RED)
    embed.add_field(name="\u2B50 Level", value=fmt(get(match, "level")))
    embed.add_field(name="\U0001F4B0 Net worth", value=worth_text(match))
    embed.add_field(name="\U0001F6E3\uFE0F Distance", value=f"{fmt(get(match, 'distance'))} km")
    embed.add_field(name="\U0001F4B5 Income", value=f"\u20AC{fmt(get(match, 'income'))}")
    embed.add_field(name="\u23F1\uFE0F Driving time", value=str(get(match, "time", "n/a")))
    embed.add_field(name="\U0001F69A Jobs", value=str(get(match, "jobs", "n/a")))
    await interaction.followup.send(embed=style(embed), file=logo_file())


@joblog.autocomplete("driver")
async def joblog_autocomplete(interaction: discord.Interaction, current: str):
    """Show real driver names from the data while the user types."""
    try:
        drivers = await load_drivers()
    except Exception:
        return []
    names = [str(get(d, "name", "")) for d in drivers]
    found = [n for n in names if n and current.lower() in n.lower()]
    return [app_commands.Choice(name=n[:100], value=n[:100]) for n in found[:25]]


@bot.tree.command(name="leaderboard", description="Show the top 5 Apex drivers")
@app_commands.describe(category="What to rank by")
@app_commands.choices(
    category=[
        app_commands.Choice(name="Distance", value="distance"),
        app_commands.Choice(name="Level", value="level"),
        app_commands.Choice(name="Net worth", value="net_worth"),
        app_commands.Choice(name="Income", value="income"),
        app_commands.Choice(name="Driving time", value="time"),
    ]
)
async def leaderboard(
    interaction: discord.Interaction,
    category: app_commands.Choice[str] = None,
):
    await interaction.response.defer()
    key = category.value if category else "distance"
    label = category.name if category else "Distance"
    try:
        drivers = await load_drivers()
    except Exception:
        await interaction.followup.send(DATA_ERROR)
        return
    emojis = {"distance": "\U0001F6E3\uFE0F", "level": "\u2B50", "net_worth": "\U0001F4B0",
              "income": "\U0001F4B5", "time": "\u23F1\uFE0F"}
    embeds = build_report(drivers, f"Top 5 by {label}", emojis[key], key)
    await interaction.followup.send(embeds=embeds, file=logo_file())


# Posts every day at 21:00 UTC, which is 00:00 East Africa Time.
@tasks.loop(time=datetime.time(hour=21, minute=0, tzinfo=datetime.timezone.utc))
async def post_leaderboard():
    channel = await find_channel(LEADERBOARD_CHANNEL_ID)
    if channel is None:
        return
    try:
        drivers = await load_drivers()
    except Exception:
        return
    ranked = sorted(drivers, key=lambda d: num(get(d, "distance")), reverse=True)[:10]
    rows = [(str(get(d, "name", "Unknown")), int(round(num(get(d, "distance"))))) for d in ranked]
    embed, file = build_top10_embed(rows)
    await channel.send(embed=embed, file=file or discord.utils.MISSING)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    """Always answer the user, and write the real error to the Render logs."""
    print(f"Command error: {error!r}", flush=True)
    message = "Something went wrong. Please try again in a minute."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message)
        else:
            await interaction.response.send_message(message)
    except Exception:
        pass


@bot.event
async def on_message(message):
    try:
        await guard(bot, message)
    except Exception as error:
        print(f"Joblog guard error: {error!r}", flush=True)


@bot.event
async def on_ready():
    if not post_leaderboard.is_running():
        post_leaderboard.start()


bot.run(TOKEN)
