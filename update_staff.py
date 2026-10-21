"""Writes staff.json from the Apex Transporte Discord server roles.

Needs the same secrets as update_stats.py:
  DISCORD_BOT_TOKEN
  DISCORD_STATS_CHANNEL_ID  (used only to find the server id)

The bot needs the Server Members intent, which it already uses for members.json.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

API = "https://discord.com/api/v10"
TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = os.environ["DISCORD_STATS_CHANNEL_ID"]

# Role names exactly as they appear on the site, highest first.
# The first role a person holds becomes the red main tag.
PRIORITY = [
    "Founder",
    "CEO",
    "Vice CEO",
    "Manager",
    "Moderator",
    "Support team",
    "Social Media Manager",
    "Upper management",
    "Skin team",
]
# A person with any of these roles goes under Leadership.
LEAD = {"founder", "ceo", "vice ceo", "manager"}


def key(text):
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def call(path):
    req = urllib.request.Request(
        API + path,
        headers={
            "Authorization": "Bot " + TOKEN,
            "User-Agent": "ApexTransporteBot (https://apextransporte.github.io, 1.0)",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    guild_id = call("/channels/" + CHANNEL_ID)["guild_id"]
    roles = {r["id"]: r["name"] for r in call("/guilds/%s/roles" % guild_id)}
    rank = {key(name): i for i, name in enumerate(PRIORITY)}
    label = {key(name): name for name in PRIORITY}

    members, after = [], "0"
    while True:
        page = call("/guilds/%s/members?limit=1000&after=%s" % (guild_id, after))
        members.extend(page)
        if len(page) < 1000:
            break
        after = page[-1]["user"]["id"]

    staff = []
    for m in members:
        user = m["user"]
        if user.get("bot"):
            continue
        held = {key(roles[rid]) for rid in m.get("roles", []) if rid in roles}
        mine = sorted((k for k in held if k in rank), key=lambda k: rank[k])
        if not mine:
            continue
        name = m.get("nick") or user.get("global_name") or user["username"]
        staff.append(
            {
                "name": name,
                "tier": "lead" if held & LEAD else "team",
                "roles": [label[k] for k in mine],
                "_rank": rank[mine[0]],
            }
        )

    if not staff:
        # Never wipe the site because of an empty or failed read.
        print("No staff found, keeping the current staff.json")
        sys.exit(0)

    staff.sort(key=lambda p: (p["tier"] != "lead", p["_rank"], p["name"].lower()))
    for p in staff:
        del p["_rank"]

    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "staff": staff,
    }
    with open("staff.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("Wrote staff.json with %d people" % len(staff))


if __name__ == "__main__":
    main()
