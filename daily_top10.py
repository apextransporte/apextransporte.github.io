import os
from datetime import timedelta

import discord

LOGO_PATH = "apex_logo.png"
RED = 0xC8102E
MEDALS = ["\U0001F947", "\U0001F948", "\U0001F949"]

THANKS = [
    "Thank you for your hard work on the road today. Drive safe.",
    "Your effort keeps Apex moving. Thank you for every kilometer.",
    "Great work, drivers. Rest well and come back strong.",
    "Thank you for representing Apex on the road. We are proud of you.",
    "Every job counts. Thank you for your dedication.",
]


def rows_for_day(raw, day):
    """Returns the drivers of one day, or None when data.json has no daily section yet."""
    if not isinstance(raw, dict) or "daily" not in raw:
        return None
    rows = raw["daily"].get(day.isoformat(), [])
    return sorted(rows, key=lambda r: r["km"], reverse=True)


def build_daily_embed(rows, day):
    """Returns (embed, file). The file is the Apex logo, or None when it is missing."""
    has_logo = os.path.exists(LOGO_PATH)
    embed = discord.Embed(title="Daily Top 10 by Distance", color=RED)
    header = day.strftime("%A, %d %B %Y")
    if not rows:
        embed.description = (
            f"{header}\n\nNo driver was on the road today. "
            "Rest well, the road waits for you tomorrow."
        )
    else:
        lines = []
        for i, r in enumerate(rows[:10]):
            tag = MEDALS[i] if i < 3 else f"{i + 1}."
            lines.append(f"{tag} **{r['name']}** - {r['km']:,} km")
        km = sum(r["km"] for r in rows)
        jobs = sum(r["jobs"] for r in rows)
        summary = f"{len(rows)} drivers | {jobs} jobs | {km:,} km as a team"
        thanks = THANKS[day.toordinal() % len(THANKS)]
        embed.description = f"{header}\n\n" + "\n".join(lines) + f"\n\n{summary}\n\n{thanks}"
    footer = f"Apex Transporte - {day.strftime('%d %b %Y')}"
    if has_logo:
        embed.set_thumbnail(url="attachment://apex_logo.png")
        embed.set_footer(text=footer, icon_url="attachment://apex_logo.png")
    else:
        embed.set_footer(text=footer)
    return embed, (discord.File(LOGO_PATH) if has_logo else None)
