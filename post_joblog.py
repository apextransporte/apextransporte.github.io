import os
import time
import requests

API = "https://discord.com/api/v10"
RED = 0xE10600
DEFAULT_LOGO = "https://apextransporte.github.io/logo.png"
SHOW_SCREENSHOT = True   # set to False when the screenshot under the card looks like a second card
LEVEL_FIELD = "🏆 Level"


def send_joblog(job):
    token = os.environ["DISCORD_BOT_TOKEN"]
    channel_id = os.environ["DISCORD_OUTPUT_CHANNEL_ID"]

    embed = {
        "title": f"🚛 {job['driver']}",
        "description": f"Delivered a job for **{job['company']}**",
        "color": RED,
        "thumbnail": {"url": os.environ.get("LOGO_URL") or DEFAULT_LOGO},
        "fields": [
            {"name": "🛣️ Distance", "value": f"{job['distance']:,} km", "inline": True},
            {"name": "⏱️ Time", "value": str(job["time"]), "inline": True},
            {"name": "💶 Income", "value": f"€{job['income']:,}", "inline": True},
            {"name": LEVEL_FIELD, "value": str(job["level"]), "inline": True},
            {"name": "💥 Damage", "value": f"-€{job['dmg']:,}", "inline": True},
            {"name": "⌛ Time Penalty", "value": f"-€{job['tmp']:,}", "inline": True},
        ],
        "footer": {"text": f"Apex Transporte • {job['date']}"},
    }
    if job.get("xp") is not None:
        embed["fields"].insert(
            4, {"name": "✨ XP", "value": f"{job['xp']:,}", "inline": True}
        )
    embed["fields"].append({"name": "Status", "value": "✅ Accepted", "inline": False})

    if SHOW_SCREENSHOT and job.get("image_url"):
        embed["image"] = {"url": job["image_url"]}

    body = {"embeds": [embed]}
    if job.get("nonce"):
        # Same nonce on every try, so Discord keeps one message even when a try times out after it posted
        body["nonce"] = job["nonce"]
        body["enforce_nonce"] = True

    response = None
    for attempt in range(3):
        try:
            response = requests.post(
                f"{API}/channels/{channel_id}/messages",
                headers={"Authorization": f"Bot {token}"},
                json=body,
                timeout=20,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
            print("Post network problem, try", attempt + 1, "of 3:", error)
            time.sleep(3 * (attempt + 1))
            continue
        if response.status_code == 429:
            try:
                wait = float(response.json().get("retry_after", 3))
            except Exception:
                wait = 3.0
            time.sleep(min(wait, 30) + 1)
            continue
        break

    if response is None:
        raise RuntimeError("Discord did not answer after 3 tries")
    if not response.ok:
        print("Discord error", response.status_code, response.text)

    response.raise_for_status()
    return response.json()["id"]


def fetch_recent_cards(pages=3):
    """The newest job cards this bot posted, so a wrong level on a card can be corrected in place."""
    token = os.environ["DISCORD_BOT_TOKEN"]
    channel_id = os.environ["DISCORD_OUTPUT_CHANNEL_ID"]
    cards, before = [], None
    for _ in range(pages):
        url = f"{API}/channels/{channel_id}/messages?limit=100"
        if before:
            url += "&before=" + before
        r = requests.get(url, headers={"Authorization": f"Bot {token}"}, timeout=20)
        if not r.ok:
            print("Could not load posted cards:", r.status_code)
            break
        batch = r.json()
        if not batch:
            break
        for m in batch:
            embeds = m.get("embeds") or []
            if m.get("author", {}).get("bot") and embeds and str(embeds[0].get("title", "")).startswith("🚛"):
                cards.append(m)
        before = batch[-1]["id"]
    return cards


def card_value(message, field_name):
    for f in message["embeds"][0].get("fields", []):
        if f.get("name") == field_name:
            return f.get("value")
    return None


def edit_card_level(message, new_level):
    """Changes only the Level field of a posted card."""
    token = os.environ["DISCORD_BOT_TOKEN"]
    channel_id = os.environ["DISCORD_OUTPUT_CHANNEL_ID"]
    old = message["embeds"][0]
    embed = {k: old[k] for k in ("title", "description", "color", "footer") if k in old}
    for key in ("thumbnail", "image"):
        if old.get(key, {}).get("url"):
            embed[key] = {"url": old[key]["url"]}
    embed["fields"] = [
        {"name": f["name"], "value": str(new_level) if f["name"] == LEVEL_FIELD else f["value"],
         "inline": f.get("inline", False)}
        for f in old.get("fields", [])
    ]
    r = requests.patch(
        f"{API}/channels/{channel_id}/messages/{message['id']}",
        headers={"Authorization": f"Bot {token}"},
        json={"embeds": [embed]},
        timeout=20,
    )
    if not r.ok:
        print("Could not edit card", message["id"], r.status_code, r.text)
    return r.ok
