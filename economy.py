"""Apex economy. Pays every accepted job log in UnbelievaBoat coins.

Lives in the repo apextransporte/apextransporte.github.io, next to update_stats.py.
1 coin = 1 euro of job income. No taxes. Drivers keep everything.

Fun parts:
  Rank pay raise    Pro +5 percent, Legend +10 percent, by lifetime distance
  Daily streak      3 days in a row +5 percent, 7 days in a row +15 percent
  Long haul         jobs of 500 km or more +10 percent
  Lucky job         5 percent chance that the whole pay doubles
  Driver of week    every Monday the top distance driver of last week wins a prize

Safety rules:
  A job is paid once. The paid mark is saved inside posted.json, the same file the job cards use.
  Jobs posted before PAY_FROM are never paid, so old history never pays out.
  A job with an income that does not fit its distance is never paid.
"""
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone

import requests

UNB_API = "https://unbelievaboat.com/api/v1"
DISCORD_API = "https://discord.com/api/v10"
UNB_TOKEN = os.environ.get("UNB_TOKEN", "")
UNB_GUILD = os.environ.get("UNB_GUILD_ID", "")

# ---------- settings, change them here ----------
COINS_PER_EURO = 1
PAY_TO = "bank"   # "bank" is safe from robbing, "cash" can be robbed with the UnbelievaBoat rob command
PAY_FROM = datetime.fromisoformat(os.environ.get("PAY_FROM", "2026-10-28T00:00:00+03:00"))
LOCAL = timezone(timedelta(hours=3))   # East Africa Time

RANKS = [(50000, "Legend", 0.10), (10000, "Pro", 0.05), (0, "Rookie", 0.0)]   # lifetime km, name, bonus
LONG_HAUL_KM = 500
LONG_HAUL_BONUS = 0.10
STREAK_BONUS = [(7, 0.15), (3, 0.05)]   # days in a row, bonus
LUCKY_CHANCE = 0.05
WEEKLY_PRIZE = 5000
MAX_PAYS_PER_RUN = 10

RED = 0xC8102E
REACTION_OK = "\u2705"


class StopPaying(Exception):
    """UnbelievaBoat refused the token or the server, so the run stops paying."""


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_posted(posted):
    with open("posted.json", "w", encoding="utf-8") as f:
        json.dump(posted, f)


def income_fits(income, km):
    return bool(income) and bool(km) and 4 <= income / km <= 120


def when(ts):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def local_day(ts):
    w = when(ts)
    return w.astimezone(LOCAL).date() if w else None


# ---------- UnbelievaBoat ----------

def unb_pay(user_id, coins, reason):
    """Adds coins to the driver. Returns the new balance dictionary or None."""
    url = "{}/guilds/{}/users/{}".format(UNB_API, UNB_GUILD, user_id)
    headers = {"Authorization": UNB_TOKEN, "Content-Type": "application/json"}
    body = {PAY_TO: int(coins), "reason": reason[:200]}
    for attempt in range(4):
        try:
            r = requests.patch(url, headers=headers, json=body, timeout=30)
        except requests.exceptions.RequestException as error:
            print("Economy: network problem, try", attempt + 1, error)
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code == 429:
            try:
                wait = float(r.json().get("retry_after", 5))
            except Exception:
                wait = 5.0
            wait = wait / 1000 if wait > 100 else wait   # the API may give milliseconds
            time.sleep(min(wait, 30) + 1)
            continue
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                return {}
        print("Economy: UnbelievaBoat answered", r.status_code, r.text[:200])
        if r.status_code in (401, 403):
            raise StopPaying("UnbelievaBoat refused the token or the server permission")
        return None
    return None


def balance_total(data):
    try:
        return int(data.get("total", int(data.get("cash", 0)) + int(data.get("bank", 0))))
    except Exception:
        return None


# ---------- Discord pay slips ----------

def announce(embed):
    # Pay slips go to the economy channel. The job card channel is the backup when it is not set.
    channel = os.environ.get("ECONOMY_CHANNEL_ID") or os.environ.get("DISCORD_OUTPUT_CHANNEL_ID")
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not channel or not token:
        return
    url = "{}/channels/{}/messages".format(DISCORD_API, channel)
    headers = {"Authorization": "Bot " + token}
    body = {"embeds": [embed], "allowed_mentions": {"parse": []}}
    for attempt in range(2):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=30)
        except requests.exceptions.RequestException as error:
            print("Economy: pay slip not sent", error)
            return
        if r.status_code == 429:
            time.sleep(5)
            continue
        if r.status_code == 403:
            print("Economy: pay slip blocked, give the bot View Channel, Send Messages and Embed Links in the economy channel")
        elif r.status_code not in (200, 201):
            print("Economy: pay slip failed", r.status_code)
        return


# ---------- pay rules ----------

def rank_for(km_total):
    for need, name, bonus in RANKS:
        if km_total >= need:
            return name, bonus
    return "Rookie", 0.0


def km_until(jobs, author, moment):
    total = 0
    for j in jobs:
        if j["author"] != author or j.get("dup"):
            continue
        w = when(j.get("ts", ""))
        if w and w <= moment:
            total += j["km"]
    return total


def streak_days(jobs, author, day):
    days = {local_day(j.get("ts", "")) for j in jobs if j["author"] == author and not j.get("dup")}
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


def work_out_pay(job, jobs):
    """Returns the pay and the lines for the pay slip."""
    moment = when(job.get("ts", ""))
    base = int(job["income"] * COINS_PER_EURO)
    lines, pct = [], 0.0

    rank_name, rank_bonus = rank_for(km_until(jobs, job["author"], moment))
    if rank_bonus:
        pct += rank_bonus
        lines.append("{} rank +{:.0f}%".format(rank_name, rank_bonus * 100))

    if job["km"] >= LONG_HAUL_KM:
        pct += LONG_HAUL_BONUS
        lines.append("Long haul +{:.0f}%".format(LONG_HAUL_BONUS * 100))

    days = streak_days(jobs, job["author"], local_day(job.get("ts", "")))
    for need, bonus in STREAK_BONUS:
        if days >= need:
            pct += bonus
            lines.append("{} day streak +{:.0f}%".format(days, bonus * 100))
            break

    total = base + int(round(base * pct))
    lucky = random.Random(job["id"]).random() < LUCKY_CHANCE   # the same job always gives the same answer
    if lucky:
        total *= 2
        lines.append("Lucky job, pay doubled")
    return base, total, lines


def pay_job(job, jobs):
    base, total, lines = work_out_pay(job, jobs)
    data = unb_pay(job["author"], total, "Apex job {} km".format(job["km"]))
    if data is None:
        return False
    wallet = balance_total(data)
    fields = [
        {"name": "Job pay", "value": "{:,} coins".format(base), "inline": True},
        {"name": "You earned", "value": "{:,} coins".format(total), "inline": True},
    ]
    if wallet is not None:
        fields.append({"name": "Wallet", "value": "{:,} coins".format(wallet), "inline": True})
    if lines:
        fields.append({"name": "Bonuses", "value": "\n".join(lines), "inline": False})
    announce({
        "title": "\U0001F4B0 Pay slip",
        "description": "<@{}> delivered {:,} km and got paid.".format(job["author"], job["km"]),
        "color": RED,
        "fields": fields,
        "footer": {"text": "Apex Transporte \u2022 Use /wallet to see your coins"},
    })
    return True


def pay_weekly_prize(jobs, posted, posted_set):
    """Every Monday the driver with the most distance last week (Monday to Sunday) wins the prize."""
    today = datetime.now(LOCAL).date()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    if this_monday <= PAY_FROM.astimezone(LOCAL).date():
        return
    key = "weekly:" + last_monday.isoformat()
    if key in posted_set:
        return
    km = {}
    for j in jobs:
        if j.get("dup"):
            continue
        day = local_day(j.get("ts", ""))
        if day and last_monday <= day < this_monday:
            km[j["author"]] = km.get(j["author"], 0) + j["km"]
    if km:
        winner = max(km, key=km.get)
        data = unb_pay(winner, WEEKLY_PRIZE, "Apex driver of the week")
        if data is None:
            return   # the next run tries again
        wallet = balance_total(data)
        fields = [
            {"name": "Distance", "value": "{:,} km".format(km[winner]), "inline": True},
            {"name": "Prize", "value": "{:,} coins".format(WEEKLY_PRIZE), "inline": True},
        ]
        if wallet is not None:
            fields.append({"name": "Wallet", "value": "{:,} coins".format(wallet), "inline": True})
        announce({
            "title": "\U0001F3C6 Driver of the week",
            "description": "<@{}> drove the most last week.".format(winner),
            "color": RED,
            "fields": fields,
            "footer": {"text": "Apex Transporte \u2022 A new prize is paid every Monday"},
        })
    posted.append(key)
    posted_set.add(key)
    save_posted(posted)


def pay_new_jobs(jobs, plan):
    """Called from update_stats.py after the job cards are posted. Safe to call many times."""
    if not UNB_TOKEN or not UNB_GUILD:
        print("Economy: UNB_TOKEN or UNB_GUILD_ID is not set, no pay this run")
        return
    ok_ids = {m["id"] for m, emoji in plan if emoji == REACTION_OK}
    posted = load_json("posted.json", [])
    posted_set = set(posted)
    paid, waiting = 0, 0
    try:
        for j in jobs:
            mid = j["id"].split("-")[0]
            key = "paid:" + j["id"]
            if mid not in ok_ids or j.get("dup") or key in posted_set:
                continue
            w = when(j.get("ts", ""))
            if w is None or w <= PAY_FROM:
                continue
            if not income_fits(j.get("income", 0), j.get("km", 0)):
                continue
            if paid >= MAX_PAYS_PER_RUN:
                waiting += 1
                continue
            if pay_job(j, jobs):
                posted.append(key)
                posted_set.add(key)
                save_posted(posted)   # saved at once, so a stopped run never pays the same job twice
                paid += 1
                time.sleep(0.5)
        pay_weekly_prize(jobs, posted, posted_set)
    except StopPaying as error:
        print("Economy stopped:", error)
    print("Economy: jobs paid", paid, "| waiting for the next run", waiting)
