import json
import os
import re
import unicodedata
from datetime import datetime, date

BASE_FILES = ("net_worth_base.json", "net_worth.json")


def load_base(path=None):
    """Accepts both formats:
    1) {"base_date": "2026-10-01", "base": {"Name": 123}}
    2) {"Name": 123, "Name2": 456}  (optional "base_date" key inside)"""
    candidates = [path] if path else list(BASE_FILES)
    found = next((p for p in candidates if p and os.path.exists(p)), None)
    if found is None:
        raise FileNotFoundError("net worth base file not found: " + ", ".join(candidates))
    with open(found, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data.get("base"), dict):
        base = data["base"]
        base_date = data.get("base_date")
    else:
        base = {k: v for k, v in data.items() if k != "base_date"}
        base_date = data.get("base_date")
    if not base_date:
        base_date = date.fromtimestamp(os.path.getmtime(found)).isoformat()
    clean = {}
    for k, v in base.items():
        try:
            clean[k] = float(v)
        except (TypeError, ValueError):
            continue
    return base_date, clean


def parse_date(value):
    return datetime.fromisoformat(str(value)[:10]).date()


def norm(name):
    """Safe name key. Removes emojis, symbols like the trademark sign, fancy fonts,
    accents, the Apex tag and all spaces or punctuation."""
    text = str(name or "").strip()
    text = re.sub(r"^\s*apex\s*[|\u2223\uff5c/]\s*", "", text, flags=re.I)
    text = "".join(c for c in text if not unicodedata.category(c).startswith("S"))
    text = unicodedata.normalize("NFKC", text).lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.category(c).startswith("M"))
    return re.sub(r"[^0-9a-z\u00c0-\u024f\u0400-\u04ff]+", "", text)


def estimate_net_worth(jobs, path=None):
    """jobs: list of dicts with keys driver, date, income.
    Returns {driver: base + income of jobs logged after the base date}.
    Drivers with no base start at 0, so they show a value instead of n/a."""
    base_date, base = load_base(path)
    start = parse_date(base_date)
    totals = dict(base)
    lookup = {norm(k): k for k in totals}
    for job in jobs:
        n = norm(job.get("driver"))
        if not n:
            continue
        key = lookup.get(n)
        if key is None:
            key = str(job.get("driver")).strip()
            totals[key] = 0.0
            lookup[n] = key
        try:
            if parse_date(job["date"]) > start:
                totals[key] += float(job.get("income") or 0)
        except (KeyError, ValueError):
            continue
    return totals


def find_net_worth(totals, name):
    """Returns the net worth for a Discord name, or None when the driver is unknown."""
    target = norm(name)
    if not target:
        return None
    for k, v in totals.items():
        if norm(k) == target:
            return v
    for k, v in totals.items():
        nk = norm(k)
        if len(nk) >= 4 and len(target) >= 4 and (nk in target or target in nk):
            return v
    return None


def fmt_money(value):
    """Always returns text. Shows n/a only when the value is None."""
    if value is None:
        return "n/a"
    if value >= 1_000_000:
        return "${:.1f}M".format(value / 1_000_000)
    if value >= 1_000:
        return "${:.1f}k".format(value / 1_000)
    return "${:,.0f}".format(value)
