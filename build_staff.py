"""Builds staff.json from Discord server roles.

Runs in the same GitHub Actions workflow as update_stats.py.
Uses the secrets you already have: DISCORD_BOT_TOKEN and DISCORD_STATS_CHANNEL_ID.
The guild ID is read from the stats channel, so no new secret is needed.

Needs "Server Members Intent" turned on for the bot in the Discord developer portal.
"""
import json
import os
import sys
import urllib.request

API = "https://discord.com/api/v10"
TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = os.environ["DISCORD_STATS_CHANNEL_ID"]

# Role names exactly as they appear in Discord. Order = display priority.
# The first role a person holds becomes their main role on the site.
ROLE_ORDER = [
    "Founder",
    "CEO",
    "Vice CEO",
    "Manager",
    "Upper management",
    "Moderator",
    "Support team",
    "Skin team",
    "Social Media Manager",
]
# People holding any of these roles show under Leadership.
LEAD_ROLES = {"Founder", "CEO", "Vice CEO", "Manager", "Upper management"}

# Fixed leadership titles and order. Discord has no Founder or CEO role,
# so these are matched by a word in the member name. A person only matches
# when they already hold a leadership role in Discord.
LEAD_TITLES = [
    ("rex", "Founder"),
    ("keem", "CEO"),
    ("sunny", "Vice CEO"),
    ("niel", "Manager"),
]

# Other spellings of a role name in Discord. Emojis, spaces and capitals are
# ignored when matching, so "Moderator", "MODERATORS" and "🛡️ Moderator" all work.
ALIASES = {
    "moderators": "Moderator",
    "mod": "Moderator",
    "mods": "Moderator",
    "staffmoderator": "Moderator",
    "support": "Support team",
    "supports": "Support team",
    "supportteam": "Support team",
    "skin": "Skin team",
    "skins": "Skin team",
    "skinteam": "Skin team",
    "skinner": "Skin team",
    "skindesigner": "Skin team",
    "socialmedia": "Social Media Manager",
    "socialmediamanager": "Social Media Manager",
}


def norm(text):
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


def match_role(role_name):
    n = norm(role_name)
    for official in ROLE_ORDER:
        if norm(official) == n:
            return official
    if n in ALIASES:
        return ALIASES[n]
    if "moderator" in n:
        return "Moderator"
    return None


def call(path):
    req = urllib.request.Request(
        API + path,
        headers={
            "Authorization": "Bot " + TOKEN,
            "User-Agent": "ApexStaffBuilder (apextransporte, 1.0)",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def all_members(guild_id):
    members, after = [], "0"
    while True:
        page = call("/guilds/%s/members?limit=1000&after=%s" % (guild_id, after))
        if not page:
            break
        members.extend(page)
        if len(page) < 1000:
            break
        after = page[-1]["user"]["id"]
    return members


def display_name(m):
    u = m.get("user", {})
    return m.get("nick") or u.get("global_name") or u.get("username") or ""


def name_tokens(name):
    out, cur = [], ""
    for ch in name.lower():
        if ch.isalnum():
            cur += ch
        else:
            if cur:
                out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def main():
    guild_id = call("/channels/%s" % CHANNEL_ID)["guild_id"]
    roles = {r["id"]: r["name"] for r in call("/guilds/%s/roles" % guild_id)}
    rank = {name.lower(): i for i, name in enumerate(ROLE_ORDER)}
    print("Server roles found:", ", ".join(sorted(roles.values())))

    staff = []
    for m in all_members(guild_id):
        if m.get("user", {}).get("bot"):
            continue
        held = []
        for rid in m.get("roles", []):
            official = match_role(roles.get(rid, ""))
            if official and official not in held:
                held.append(official)
        if not held:
            continue
        held.sort(key=lambda n: rank[n.lower()])
        name = display_name(m)
        if not name:
            continue
        tier = "lead" if any(h in LEAD_ROLES for h in held) else "team"
        sort_key = rank[held[0].lower()]
        if tier == "lead":
            toks = name_tokens(name)
            for i, (key, title) in enumerate(LEAD_TITLES):
                if key in toks:
                    held = [title] + [h for h in held if h not in ("Founder", "CEO", "Vice CEO", "Manager", title)]
                    sort_key = i
                    break
            else:
                sort_key = 100 + sort_key
        staff.append({"name": name, "roles": held, "tier": tier, "_r": sort_key})

    staff.sort(key=lambda p: (p["tier"] != "lead", p["_r"], p["name"].lower()))
    for p in staff:
        del p["_r"]

    if not staff:
        print("No staff found. Check role names and Server Members Intent. staff.json left unchanged.")
        sys.exit(0)

    with open("staff.json", "w", encoding="utf-8") as f:
        json.dump({"staff": staff}, f, ensure_ascii=False, indent=2)
    print("Wrote staff.json with %d people" % len(staff))


if __name__ == "__main__":
    main()
