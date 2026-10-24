import os
import time
import requests

API = "https://discord.com/api/v10"
RED = 0xE10600
DEFAULT_LOGO = "https://apextransporte.github.io/logo.png"
SHOW_SCREENSHOT = True   # set to False when the screenshot under the card looks like a second card


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
            {"name": "🏆 Level", "value": str(job["level"]), "inline": True},
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
