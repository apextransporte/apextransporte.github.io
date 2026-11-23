import json
import os
import sys

MEMBERS_FILE = "members.json"
TARGET_FILES = ["jobs.json", "apex_drivers.json"]

# Always kept, even when members.json misses the account.
ALWAYS_IDS = {"958600206432239656"}
ALWAYS_NAMES = {"corprate keem", "apex | keem", "keem"}

BACKUP_FILE = "removed_rows.json"
BACKUP = []   # rows removed in this run, saved so a role mistake never loses data

ID_KEYS = ["discord_id", "user_id", "id", "member_id"]
NAME_KEYS = ["name", "driver", "member", "username", "author", "player", "user"]


def norm(value):
    return str(value).strip().lower()


def load_official():
    with open(MEMBERS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    ids = set()
    names = set()
    for m in data.get("members", []):
        ids.add(str(m["id"]))
        for key in ["name", "username", "global_name", "nick"]:
            if m.get(key):
                names.add(norm(m[key]))
    if not ids:
        sys.exit("members.json has no official members. Stopping to protect your data.")
    ids |= ALWAYS_IDS
    names |= ALWAYS_NAMES
    return ids, names


def is_official(row, ids, names):
    for key in ID_KEYS:
        if key in row and str(row[key]) in ids:
            return True
    for key in NAME_KEYS:
        if key in row and isinstance(row[key], str) and norm(row[key]) in names:
            return True
    return False


def filter_list(rows, ids, names, label):
    kept = []
    removed = []
    for row in rows:
        if isinstance(row, dict) and not is_official(row, ids, names):
            removed.append(row)
        else:
            kept.append(row)
    for row in removed:
        BACKUP.append({"label": label, "row": row})
        shown = next((row[k] for k in NAME_KEYS if k in row), "unknown")
        print(f"{label}: removed {shown}")
    return kept


def filter_data(data, ids, names, label):
    if isinstance(data, list):
        return filter_list(data, ids, names, label)
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                result[key] = filter_list(value, ids, names, f"{label}.{key}")
            elif isinstance(value, dict) and value and all(
                isinstance(v, dict) for v in value.values()
            ):
                kept = {}
                for name, row in value.items():
                    if norm(name) in names or is_official(row, ids, names):
                        kept[name] = row
                    else:
                        print(f"{label}.{key}: removed {name}")
                result[key] = kept
            else:
                result[key] = value
        return result
    return data


def load_backup():
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (OSError, ValueError):
            pass
    return []


def restore_rows(path, data, ids, names, saved):
    """Puts back saved rows of top-level list files when their owner is an official member again."""
    if not isinstance(data, list):
        return data, saved
    have = {str(r.get("id")) for r in data if isinstance(r, dict) and r.get("id") is not None}
    keep_saved = []
    back = 0
    for item in saved:
        row = item.get("row")
        if item.get("label") == path and isinstance(row, dict) and is_official(row, ids, names):
            if str(row.get("id")) not in have:
                data.append(row)
                back += 1
            continue
        keep_saved.append(item)
    if back:
        if all(isinstance(r, dict) and "ts" in r for r in data):
            data.sort(key=lambda r: r["ts"])
        print(f"{path}: restored {back} saved rows")
    return data, keep_saved


def main():
    ids, names = load_official()
    files = sys.argv[1:] or TARGET_FILES
    saved = load_backup()
    for path in files:
        if not os.path.exists(path):
            print(f"Skipped {path}: file not found")
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data, saved = restore_rows(path, data, ids, names, saved)
        cleaned = filter_data(data, ids, names, path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
        print(f"Cleaned {path}")
    saved = saved + BACKUP
    if saved:
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(saved, f, ensure_ascii=False)
        print(f"Saved {len(saved)} removed rows in {BACKUP_FILE}")


if __name__ == "__main__":
    main()
