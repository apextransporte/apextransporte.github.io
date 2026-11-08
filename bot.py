import asyncio
import datetime
import json
import os
import re
import time
import traceback
import unicodedata

import aiohttp
import discord
from aiohttp import web
from discord import app_commands
from discord.ext import tasks

from joblog_guard import guard, start_rebuild
from daily_top10 import build_daily_embed, rows_for_day
from wallet import add_wallet
import apex_economy_plus
import rank_runner
import anniversary
import driver_of_the_week
from convoy import setup_convoy
from pingroles import setup_pingroles
from routevote import setup_routevote
from invites import setup_invites
from verification import setup_verification

TOKEN = os.getenv("TOKEN") or os.environ["DISCORD_BOT_TOKEN"]
DATA_URL = os.getenv(
    "APEX_DATA_URL",
    "https://apextransporte.github.io/data.json",
)
CACHE_SECONDS = 60

# Starts the GitHub job card run the moment a screenshot is posted in the joblog channel.
GITHUB_TOKEN = os.getenv("GITHUB_DISPATCH_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "apextransporte/apextransporte.github.io")
GITHUB_WORKFLOW = os.getenv("GITHUB_WORKFLOW", "update-stats.yml")
JOBLOG_CHANNEL_ID = int(os.getenv("JOBLOG_CHANNEL_ID", "0"))
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
    """Find a driver by Discord ID, exact name, part of a name, or the words of a Discord name like Apex | keem."""
    digits = re.sub(r"\D", "", str(query))
    if len(digits) >= 15:  # a Discord ID or a mention like <@123456789012345678>
        for d in drivers:
            if str(d.get("id", "")) == digits:
                return d
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


MEDALS = {1: "\U0001F947", 2: "\U0001F948", 3: "\U0001F949"}


def card_name(name, width=13):
    """Name without emojis and the Apex tag, so table columns stay straight."""
    name = re.sub(r"[\U00010000-\U0010FFFF\u2600-\u27BF\u200d\ufe0f]", "", str(name))
    name = re.sub(r"^\s*apex\s*\|\s*", "", name, flags=re.IGNORECASE).strip() or "Unknown"
    return name if len(name) <= width else name[: width - 1] + "\u2026"


def euro_text(value):
    if isinstance(value, (int, float)):
        return f"\u20AC{value:,.0f}"
    text = str(value).strip()
    return text if text.startswith("\u20AC") else f"\u20AC{text}"


def km_text(value):
    if isinstance(value, (int, float)):
        return f"{value:,.0f} km"
    text = str(value).strip()
    return text if "km" in text.lower() else f"{text} km"


def pct_text(value):
    text = str(value).strip()
    return text if text.endswith("%") else f"{text}%"


def delivery_embed(kind, rankings):
    """Clean delivery rank or worst delivery rank, read from the rankings block of data.json."""
    rows = (rankings or {}).get(kind) or []
    seen, unique = set(), []
    for r in rows:   # each driver appears once, at the best place
        if r["name"] in seen or "deleted user" in str(r["name"]).lower():
            continue
        seen.add(r["name"])
        unique.append(r)
    unique = unique[:10]

    if kind == "clean":
        embed = discord.Embed(
            title="CLEANEST DRIVERS",
            description="Jobs with no damage and no time penalty",
            color=RED,
        )
        if not unique:
            embed.add_field(name="\u200b", value="No data yet.", inline=False)
            return embed
        lines = [f"{'#':<3}{'DRIVER':<14}{'CLEAN':>9}{'RATE':>6}", "\u2500" * 32]
        for i, r in enumerate(unique, start=1):
            record = f"{r['clean']}/{r['jobs']}"
            lines.append(f"{i:<3}{card_name(r['name']):<14}{record:>9}{pct_text(r['rate']):>6}")
        embed.add_field(name="\u200b", value="```\n" + "\n".join(lines) + "\n```", inline=False)
        podium = "   ".join(
            f"{MEDALS[i]} **{card_name(r['name'], 18)}**" for i, r in enumerate(unique[:3], start=1)
        )
        embed.add_field(name="Podium", value=podium, inline=False)
        return embed

    embed = discord.Embed(
        title="WORST DELIVERIES",
        description="Each driver's single most costly job",
        color=RED,
    )
    if not unique:
        embed.add_field(name="\u200b", value="No data yet.", inline=False)
        return embed
    for i, r in enumerate(unique, start=1):
        when = parse_date(r.get("date", ""))
        date = when.strftime("%d %b %Y") if when else ""
        badge = MEDALS.get(i, f"`#{i}`")
        embed.add_field(
            name=f"{badge}  {card_name(r['name'], 24)}",
            value=(
                f"**{euro_text(r['total'])}** total cost\n"
                f"Damage `{euro_text(r['damage'])}`  \u00B7  Time `{euro_text(r['time_penalty'])}`\n"
                f"{km_text(r['km'])}  \u00B7  {date}"
            ),
            inline=False,
        )
    return embed


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
    """Save each driver's net worth. Fill it back in when the data file loses it.
    The Discord ID is the key when data.json has it, so a new name or emoji keeps the value."""
    changed = False
    for d in drivers:
        name = squash(get(d, "name", ""))
        key = str(d.get("id") or "") or name
        if not key:
            continue
        current = num(get(d, "net_worth"))
        if current > 0:
            if NET_WORTH_SAVED.get(key) != current:
                NET_WORTH_SAVED[key] = current
                changed = True
        elif key in NET_WORTH_SAVED:
            d["net_worth"] = NET_WORTH_SAVED[key]
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
        intents.members = True  # needed so the rank system finds each driver by name
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.session = None

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        await start_web_server()
        await apex_economy_plus.install(self)
        await rank_runner.install(self, load_drivers, get, num, words)
        await anniversary.install(self)  # join anniversary cards, posts in the promotion channel
        await driver_of_the_week.install(self)  # Driver of the Week card, posts in the leaderboard channel
        await setup_convoy(self)  # convoy planner, must run before the tree sync
        await setup_pingroles(self)  # ping role buttons, must run before the tree sync
        await setup_routevote(self)  # route vote, must run before the tree sync
        await setup_invites(self)  # invite tracker, must run before the tree sync
        setup_verification(self)  # verification tickets, must run before the tree sync
        await self.tree.sync()

    async def close(self):
        if self.session:
            await self.session.close()
        await apex_economy_plus.shutdown()
        await super().close()


bot = ApexBot()
add_wallet(bot)

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
@app_commands.describe(driver="Driver name", member="Pick the driver from the server list")
async def joblog(interaction: discord.Interaction, driver: str = None, member: discord.Member = None):
    await interaction.response.defer()
    try:
        drivers = await load_drivers()
    except Exception:
        await interaction.followup.send(DATA_ERROR)
        return
    if member is None and not driver:
        await interaction.followup.send("Type a driver name or pick a member.")
        return
    match = None
    if member is not None:
        match = find_driver(drivers, str(member.id)) or find_driver(drivers, member.display_name)
    if match is None and driver:
        match = find_driver(drivers, driver)
    if match is None:
        await interaction.followup.send(f"No driver found named {driver or member.display_name}.")
        return

    embed = discord.Embed(title=str(get(match, "name", driver or "Driver")), color=RED)
    # Row 1: Level and Jobs
    embed.add_field(name="\u2B50 Level", value=fmt(get(match, "level")), inline=True)
    embed.add_field(name="\U0001F69A Jobs", value=str(get(match, "jobs", "n/a")), inline=True)
    # Row 2: Distance and Driving time
    embed.add_field(name="\U0001F6E3\uFE0F Distance", value=f"{fmt(get(match, 'distance'))} km", inline=True)
    embed.add_field(name="\u23F1\uFE0F Driving time", value=str(get(match, "time", "n/a")), inline=True)
    # Row 3: Income and Net worth
    embed.add_field(name="\U0001F4B5 Income", value=f"\u20AC{fmt(get(match, 'income'))}", inline=True)
    embed.add_field(name="\U0001F4B0 Net worth", value=worth_text(match), inline=True)
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


@bot.tree.command(name="leaderboard", description="Show Apex driver rankings")
@app_commands.describe(category="What to rank by")
@app_commands.choices(
    category=[
        app_commands.Choice(name="Distance", value="distance"),
        app_commands.Choice(name="Level", value="level"),
        app_commands.Choice(name="Net worth", value="net_worth"),
        app_commands.Choice(name="Income", value="income"),
        app_commands.Choice(name="Driving time", value="time"),
        app_commands.Choice(name="Clean deliveries", value="clean"),
        app_commands.Choice(name="Worst deliveries", value="worst"),
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
    if key in ("clean", "worst"):
        raw = _cache.get("raw")
        rankings = raw.get("rankings") if isinstance(raw, dict) else None
        embed = style(delivery_embed(key, rankings))
        await interaction.followup.send(embed=embed, file=logo_file())
        return
    emojis = {"distance": "\U0001F6E3\uFE0F", "level": "\u2B50", "net_worth": "\U0001F4B0",
              "income": "\U0001F4B5", "time": "\u23F1\uFE0F"}
    embeds = build_report(drivers, f"Top 5 by {label}", emojis[key], key)
    await interaction.followup.send(embeds=embeds, file=logo_file())


# ---------------------------------------------------------------------------
# Daily Top 10 card
# The card is due at 00:00 East Africa Time, which is 21:00 UTC.
# Three triggers share one function: the 21:00 UTC schedule, a check every
# 10 minutes, and the bot start. The function posts only when no card exists
# in the channel since 00:00 EAT today, so a restart never makes a double card
# and a missed card is posted as soon as the bot is back.
# ---------------------------------------------------------------------------
_last_daily_day = None
_daily_lock = None


def daily_lock():
    """One lock for all daily checks. It is created inside the running event loop."""
    global _daily_lock
    if _daily_lock is None:
        _daily_lock = asyncio.Lock()
    return _daily_lock


async def card_already_posted(channel):
    """True when the bot posted a Top 10 card in this channel since 00:00 EAT today."""
    start = datetime.datetime.now(EAT).replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        async for message in channel.history(limit=200, after=start):
            if message.author.id != bot.user.id:
                continue
            if any(e.title and "Top 10" in e.title for e in message.embeds):
                return True
    except Exception as error:
        print(f"Daily post: cannot read channel history, give the bot Read Message History: {error!r}", flush=True)
    return False


async def ensure_daily_post(reason):
    global _last_daily_day
    async with daily_lock():
        day = (datetime.datetime.now(EAT) - datetime.timedelta(days=1)).date()
        if _last_daily_day == day:
            return

        channel = await find_channel(LEADERBOARD_CHANNEL_ID)
        if channel is None:
            print("Daily post: leaderboard channel not found, check LEADERBOARD_CHANNEL_ID", flush=True)
            return

        if await card_already_posted(channel):
            _last_daily_day = day
            print(f"Daily post ({reason}): card for {day} is already in the channel", flush=True)
            return

        print(f"Daily post ({reason}): building the card for {day}", flush=True)
        rows = None
        for attempt in range(1, 4):
            try:
                _cache["time"] = 0.0  # force a fresh download of data.json
                await load_drivers()
                rows = rows_for_day(_cache.get("raw"), day)
            except Exception as error:
                print(f"Daily post: data load failed on attempt {attempt}: {error!r}", flush=True)
            if rows is not None:
                break
            print(f"Daily post: no daily data on attempt {attempt}", flush=True)
            if attempt < 3:
                await asyncio.sleep(20)

        if rows is None:
            print("Daily post: data.json has no daily section, the next check tries again", flush=True)
            return

        try:
            embed, file = build_daily_embed(rows, day)
            await channel.send(embed=embed, file=file or discord.utils.MISSING)
        except Exception:
            print("Daily post: sending failed. Check the channel permissions: View Channel, "
                  "Send Messages, Embed Links, Attach Files.", flush=True)
            print(traceback.format_exc(), flush=True)
            return

        _last_daily_day = day
        print(f"Daily post: card for {day} sent", flush=True)


# Runs every day at 21:00 UTC, which is 00:00 East Africa Time.
@tasks.loop(time=datetime.time(hour=21, minute=0, tzinfo=datetime.timezone.utc))
async def post_leaderboard():
    try:
        await ensure_daily_post("schedule")
    except Exception:
        print(traceback.format_exc(), flush=True)  # an error here must never stop the loop


# Runs at the bot start and then every 10 minutes. It posts a missed card.
@tasks.loop(minutes=10)
async def daily_catch_up():
    try:
        await ensure_daily_post("catch-up")
    except Exception:
        print(traceback.format_exc(), flush=True)


@bot.tree.command(name="dailysample", description="Preview the daily leaderboard card")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.describe(days_ago="0 for today, 1 for yesterday")
async def dailysample(interaction: discord.Interaction, days_ago: int = 1):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    try:
        await load_drivers()
    except Exception:
        await interaction.followup.send(DATA_ERROR, ephemeral=True)
        return
    day = (datetime.datetime.now(EAT) - datetime.timedelta(days=days_ago)).date()
    rows = rows_for_day(_cache.get("raw"), day)
    if rows is None:
        await interaction.followup.send(
            "data.json has no daily section yet. Push update_stats.py first.", ephemeral=True
        )
        return
    embed, file = build_daily_embed(rows, day)
    await interaction.followup.send(embed=embed, file=file or discord.utils.MISSING, ephemeral=True)


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


async def start_stats_run():
    """Asks GitHub to run the update stats workflow now, so the job card goes out in about a minute."""
    if not GITHUB_TOKEN:
        print("GITHUB_DISPATCH_TOKEN is not set, the job card waits for the next scheduled run", flush=True)
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    headers = {
        "Authorization": "Bearer " + GITHUB_TOKEN,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with bot.session.post(url, headers=headers, json={"ref": "main"},
                                    timeout=aiohttp.ClientTimeout(total=15)) as response:
            print(f"Job card run requested, GitHub answered {response.status}", flush=True)
    except Exception as error:
        print(f"Job card run request failed: {error!r}", flush=True)


def has_image(message):
    for att in message.attachments:
        ctype = att.content_type or ""
        name = (att.filename or "").lower()
        if ctype.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            return True
    return False


@bot.event
async def on_message(message):
    # The guard checks for duplicates first and reacts only after the check.
    accepted = False
    try:
        accepted = await guard(bot, message)
    except Exception as error:
        print(f"Joblog guard error: {error!r}", flush=True)

    # The job card run starts only for an accepted screenshot.
    if (accepted and JOBLOG_CHANNEL_ID and message.channel.id == JOBLOG_CHANNEL_ID
            and not message.author.bot and has_image(message)):
        await start_stats_run()
    try:
        await apex_economy_plus.handle_message(message)
    except Exception as error:
        print(f"Economy plus error: {error!r}", flush=True)


@bot.event
async def on_ready():
    print(f"Bot ready as {bot.user}", flush=True)
    start_rebuild(bot)  # loads the used-screenshot list in the background
    if not post_leaderboard.is_running():
        post_leaderboard.start()
    if not daily_catch_up.is_running():
        daily_catch_up.start()


bot.run(TOKEN)
