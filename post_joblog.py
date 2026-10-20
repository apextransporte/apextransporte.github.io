import os
import requests

API = "https://discord.com/api/v10"
RED = 0xE10600
DEFAULT_LOGO = "https://apextransporte.github.io/logo.png"


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

    if job.get("image_url"):
        embed["image"] = {"url": job["image_url"]}

    response = requests.post(
        f"{API}/channels/{channel_id}/messages",
        headers={"Authorization": f"Bot {token}"},
        json={"embeds": [embed]},
        timeout=20,
    )
    if not response.ok:
    print("Discord error", response.status_code, response.text)
    
    response.raise_for_status()
    return response.json()["id"]
