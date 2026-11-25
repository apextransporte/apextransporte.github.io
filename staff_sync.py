"""Builds staff.json from Discord roles. Run it from the Update stats workflow.

Needs: DISCORD_BOT_TOKEN secret, Server Members Intent turned on for the bot
in the Discord Developer Portal. GUILD_ID is optional.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

API = "https://discord.com/api/v10"
GUILD_ID = os.environ.get("GUILD_ID") or "1408831708882534523"
TOKEN = os.environ["DISCORD_BOT_TOKEN"]

# Highest title first. A member shows the first title they hold as the main label.
# leader = True puts the member in the Leadership tier.
ROLES = [
    {"id": "1409272631877963806", "title": "Founder", "leader": True},
    {"id": "1409773363978571816", "title": "CEO", "leader": True},
    {"id": "1410264308608405554", "title": "Manager", "leader": True},
    {"id": "1573451260823343246", "title": "Convoy and Meetup Manager", "leader": False},
    {"id": "1410264390191812608", "title": "Moderator", "leader": False},
    {"id": "1411213464634003546", "title": "Support team", "leader": False},
    {"id": "1410265926519099505", "title": "Skin team", "leader": False},
]

# True keeps the old staff.json (and the hand typed cards) until every role ID is filled in,
# so nobody drops off the site by mistake.
REQUIRE_ALL_IDS = True
OUT_FILE = "staff.json"


def get(url, params=None):
    for attempt in range(4):
        try:
            r = requests.get(url, headers={"Authorization": "Bot " + TOKEN}, params=params, timeout=60)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print("Network problem, try", attempt + 1, e)
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 429:
            time.sleep(min(float(r.json().get("retry_after", 5)), 60) + 1)
            continue
        return r
    return None


def fetch_members():
    members, after = [], "0"
    while True:
        r = get("{}/guilds/{}/members".format(API, GUILD_ID), {"limit": 1000, "after": after})
        if r is None:
            sys.exit("Discord did not answer.")
        if r.status_code in (401, 403):
            sys.exit("Discord refused. Turn on Server Members Intent for the bot and check the token. " + r.text[:200])
        if r.status_code != 200:
            sys.exit("Discord error {}: {}".format(r.status_code, r.text[:200]))
        page = r.json()
        members.extend(page)
        if len(page) < 1000:
            return members
        after = page[-1]["user"]["id"]


def display_name(m):
    u = m.get("user", {})
    return m.get("nick") or u.get("global_name") or u.get("username") or "Unknown"


def build(members):
    order = {r["id"]: i for i, r in enumerate(ROLES) if r["id"]}
    by_id = {r["id"]: r for r in ROLES if r["id"]}
    leaders, team = [], []
    for m in members:
        if m.get("user", {}).get("bot"):
            continue
        held = sorted((rid for rid in m.get("roles", []) if rid in order), key=lambda rid: order[rid])
        if not held:
            continue
        titles = [by_id[rid]["title"] for rid in held]
        is_leader = any(by_id[rid]["leader"] for rid in held)
        tags = titles[1:]
        if by_id[held[0]]["leader"]:
            tags = ["Upper management"] + tags
        card = {"name": display_name(m), "main": titles[0], "tags": tags, "_rank": order[held[0]]}
        (leaders if is_leader else team).append(card)
    for group in (leaders, team):
        group.sort(key=lambda c: (c["_rank"], c["name"].lower()))
        for c in group:
            c.pop("_rank")
    return {"total": len(leaders) + len(team), "leadership": leaders, "team": team}


def main():
    blank = [r["title"] for r in ROLES if not r["id"]]
    if blank and REQUIRE_ALL_IDS:
        print("Staff sync paused. Missing role IDs for:", ", ".join(blank))
        return
    result = build(fetch_members())
    try:
        with open(OUT_FILE, encoding="utf-8") as f:
            old = json.load(f)
        old.pop("updated", None)
    except (OSError, ValueError):
        old = None
    if old == result:
        print("Staff list unchanged.")
        return
    result["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("Staff list saved:", result["total"], "people")


if __name__ == "__main__":
    main()
