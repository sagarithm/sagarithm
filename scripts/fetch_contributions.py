import datetime
import json
import os
import re
import sys
import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_PROFILE_USER", "sagarithm")
URL = f"https://github.com/users/{USERNAME}/contributions"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "..", "data", "contributions.json")

def fetch_days():
    resp = requests.get(URL, headers={"User-Agent": "profile-readme-bot/1.0"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        print("no calendar cells found -- github markup may have changed", file=sys.stderr)
        sys.exit(1)

    days = []
    for td in cells:
        date = td.get("data-date")
        if not date:
            continue
        td_id = td.get("id")
        tooltip_el = soup.find("tool-tip", attrs={"for": td_id}) if td_id else None
        text = tooltip_el.get_text(strip=True) if tooltip_el else ""
        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            m = re.match(r"(\d+)", text)
            count = int(m.group(1)) if m else 0
        days.append({"date": date, "count": count, "level": int(td.get("data-level") or 0)})

    days.sort(key=lambda d: d["date"])
    return days

def compute_current_streak(days):
    idx = len(days) - 1
    if idx >= 0 and days[idx]["count"] == 0:
        idx -= 1
    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    start = days[idx + 1]["date"] if streak else ""
    end = days[end_idx]["date"] if streak and end_idx >= 0 else ""
    return {"length": streak, "start": start, "end": end}

def compute_longest_streak(days):
    best, best_s, best_e = 0, "", ""
    cur, cur_s = 0, ""
    for d in days:
        if d["count"] > 0:
            if cur == 0:
                cur_s = d["date"]
            cur += 1
            if cur > best:
                best = cur
                best_s = cur_s
                best_e = d["date"]
        else:
            cur = 0
    return {"length": best, "start": best_s, "end": best_e}

def compute_monthly(days):
    by_m = {}
    for d in days:
        m = d["date"][:7]
        by_m[m] = by_m.get(m, 0) + d["count"]
    return [{"month": m, "total": by_m[m]} for m in sorted(by_m)]

def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    days = fetch_days()
    total = sum(d["count"] for d in days)
    active = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"]) if days else {"date": "", "count": 0}

    out = {
        "user": USERNAME,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_contributions": total,
        "active_days": active,
        "current_streak": compute_current_streak(days),
        "longest_streak": compute_longest_streak(days),
        "best_day": best,
        "monthly": compute_monthly(days),
        "days": days,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {OUT_PATH}: {total} contributions across {len(days)} days (active: {active})")

if __name__ == "__main__":
    main()
