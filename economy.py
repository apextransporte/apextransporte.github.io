"""economy.py

Pays drivers in UnbelievaBoat coins for every accepted job log and posts a payslip
in the Apex economy channel.

This file runs inside update_stats.py on GitHub Actions. So every value below must be
a GitHub Actions secret AND be listed in the env block of update-stats.yml:

    UNB_TOKEN            UnbelievaBoat application token
    GUILD_ID             your Discord server ID
    ECONOMY_CHANNEL_ID   channel where payslips are posted
    DISCORD_BOT_TOKEN    already set, used to post the payslip

Optional:
    COIN_RATE            coins per euro of job income, default 1
    PAY_FROM             only jobs posted after this time are paid, default below
"""
import hashlib
import json
import os
import time
from datetime import datetime, timezone

import requests

UNB_API = "https://unbelievaboat.com/api/v1"
DISCORD_API = "https://discord.com/api/v10"
OK_EMOJI = "\u2705"
POSTED_FILE = "posted.json"   # the same file update_stats.py already saves, so no new file is needed
MAX_PAYS_PER_RUN = 20
MAX_SLIPS_PER_RUN = 20
RED = 0xC8102E


def env(name, default=""):
    return os.environ.get(name, default).strip()


def coin_rate():
    try:
        return float(env("COIN_RATE", "1"))
    except ValueError:
        return 1.0


def pay_from():
    # Change this date if you want older jobs paid too.
    text = env("PAY_FROM", "2026-10-28T00:00:00+03:00")
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        when = datetime.fromisoformat("2026-10-28T00:00:00+03:00")
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when


def load_posted():
    try:
        with open(POSTED_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_posted(items):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f)


def income_ok(income, km):
    """Same rule as update_stats.py. A job with a doubtful income is never paid."""
    return bool(income) and bool(km) and 4 <= income / km <= 120


def parse_when(text):
    try:
        when = datetime.fromisoformat(str(text))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when


def unb_add_cash(user_id, amount, reason):
    """Adds coins to the driver's cash. Returns (True, balance_dict) or (False, error text)."""
    url = "{}/guilds/{}/users/{}".format(UNB_API, env("GUILD_ID"), user_id)
    headers = {
        "Authorization": env("UNB_TOKEN"),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {"cash": amount, "reason": reason[:200]}
    for attempt in range(3):
        try:
            r = requests.patch(url, headers=headers, json=body, timeout=30)
        except requests.exceptions.RequestException as error:
            print("UnbelievaBoat network problem, try", attempt + 1, "of 3:", error)
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code == 429:
            try:
                wait = float(r.json().get("retry_after", 2000)) / 1000.0
            except Exception:
                wait = 3.0
            time.sleep(min(wait, 30) + 0.5)
            continue
        if r.status_code == 200:
            try:
                return True, r.json()
            except Exception:
                return True, {}
        if r.status_code == 401:
            return False, "401 UNB_TOKEN is wrong"
        if r.status_code == 403:
            return False, "403 add the UnbelievaBoat application to your server and check GUILD_ID"
        return False, "{} {}".format(r.status_code, r.text[:200])
    return False, "no answer from UnbelievaBoat"


def post_payslip(job, coins, balance):
    """Posts the payslip embed in the economy channel. Returns True when Discord accepted it."""
    channel = env("ECONOMY_CHANNEL_ID")
    token = env("DISCORD_BOT_TOKEN")
    if not channel or not token:
        print("ECONOMY_CHANNEL_ID or DISCORD_BOT_TOKEN is missing in GitHub Actions, payslip not sent")
        return False
    author = str(job["author"])
    when = parse_when(job.get("ts", ""))
    fields = [
        {"name": "\U0001F464 Driver", "value": "<@{}>".format(author), "inline": True},
        {"name": "\U0001F6E3\uFE0F Distance", "value": "{:,} km".format(job.get("km", 0)), "inline": True},
        {"name": "\U0001F4B5 Job income", "value": "\u20AC{:,}".format(job.get("income", 0)), "inline": True},
        {"name": "\U0001FA99 Coins paid", "value": "{:,}".format(coins), "inline": True},
    ]
    if balance is not None:
        fields.append({"name": "\U0001F4B0 New balance", "value": "{:,}".format(balance), "inline": True})
    embed = {
        "title": "\U0001F9FE Apex Transporte Payslip",
        "description": "Your job log was accepted and your coins are paid.",
        "color": RED,
        "fields": fields,
        "footer": {"text": "Apex Transporte \u2022 1 job = coins paid at once"},
    }
    if when:
        embed["timestamp"] = when.astimezone(timezone.utc).isoformat()
    payload = {
        "content": "<@{}>".format(author),
        "allowed_mentions": {"users": [author]},
        "embeds": [embed],
        "nonce": hashlib.md5(("slip:" + job["id"]).encode()).hexdigest()[:24],
        "enforce_nonce": True,
    }
    url = "{}/channels/{}/messages".format(DISCORD_API, channel)
    headers = {"Authorization": "Bot " + token, "Content-Type": "application/json"}
    for attempt in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as error:
            print("Payslip network problem, try", attempt + 1, "of 3:", error)
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code == 429:
            try:
                wait = float(r.json().get("retry_after", 3))
            except Exception:
                wait = 3.0
            time.sleep(min(wait, 30) + 0.5)
            continue
        if r.status_code in (200, 201):
            return True
        if r.status_code in (403, 404):
            print("Payslip blocked", r.status_code, "- give the bot View Channel, Send Messages and Embed Links "
                  "in the economy channel and check ECONOMY_CHANNEL_ID")
            return False
        print("Payslip failed", r.status_code, r.text[:200])
        return False
    return False


def pay_new_jobs(jobs, plan):
    """Called by update_stats.py after the job cards are posted.
    Each accepted job pays once. The payment and the payslip are remembered separately,
    so a payment is never repeated and a missed payslip is sent again on the next run."""
    if not env("UNB_TOKEN") or not env("GUILD_ID"):
        print("ECONOMY: UNB_TOKEN or GUILD_ID is missing in GitHub Actions secrets, no coins paid. "
              "Add both secrets and list them in the env block of update-stats.yml")
        return

    ok_ids = {m["id"] for m, emoji in plan if emoji == OK_EMOJI}
    posted = load_posted()
    done = set(posted)
    since = pay_from()
    rate = coin_rate()
    paid = slips = fails = 0
    skipped = {"no check mark": 0, "repeat": 0, "before PAY_FROM": 0, "income not trusted": 0,
               "card not posted yet": 0, "already paid": 0, "run limit": 0}

    for j in sorted(jobs, key=lambda x: x.get("ts", "")):
        mid = j["id"].split("-")[0]
        if mid not in ok_ids:
            skipped["no check mark"] += 1
            continue
        if j.get("dup"):
            skipped["repeat"] += 1
            continue
        when = parse_when(j.get("ts", ""))
        if when is None or when < since:
            skipped["before PAY_FROM"] += 1
            continue
        if not income_ok(j.get("income", 0), j.get("km", 0)):
            skipped["income not trusted"] += 1
            continue
        if "msg:" + mid not in done:
            skipped["card not posted yet"] += 1
            continue

        pay_key, slip_key = "paid:" + mid, "slip:" + mid
        coins = int(round(j["income"] * rate))
        balance = None

        if pay_key not in done:
            if paid >= MAX_PAYS_PER_RUN:
                skipped["run limit"] += 1
                continue
            if fails >= 3:
                print("ECONOMY: three payments failed, the next run tries again")
                break
            ok, result = unb_add_cash(j["author"], coins, "Apex job " + j["id"])
            if not ok:
                fails += 1
                print("ECONOMY: payment failed for", j["name"], j["author"], ":", result)
                continue
            posted.append(pay_key)
            done.add(pay_key)
            save_posted(posted)   # saved right away, so a stopped run never pays the same job twice
            paid += 1
            if isinstance(result, dict):
                balance = result.get("total", result.get("cash"))
            print("ECONOMY: paid", coins, "coins to", j["name"], "for", j["id"])
            time.sleep(0.6)
        else:
            skipped["already paid"] += 1

        if slip_key not in done and slips < MAX_SLIPS_PER_RUN:
            if post_payslip(j, coins, balance):
                posted.append(slip_key)
                done.add(slip_key)
                save_posted(posted)
                slips += 1
                time.sleep(0.6)

    print("ECONOMY: paid", paid, "| payslips sent", slips, "| failed", fails, "| skipped", skipped)
