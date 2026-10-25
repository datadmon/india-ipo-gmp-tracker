"""India IPO GMP tracker: today's grey market premium for open and upcoming IPOs, with history and alerts.

    export APIFY_TOKEN=...          # https://console.apify.com/settings/integrations
    python ipo_gmp_tracker.py       # fetches today's GMP table, appends data/gmp-history.csv, writes data/latest.md, sends alerts
    python ipo_gmp_tracker.py --dry-run

The figures come from the India IPO Tracker Actor on Apify (InvestorGain's GMP report: mainboard and SME IPOs with
GMP, subscription, price band, lot size and the open / close / allotment / listing dates). Each run stores one dated
snapshot, so the repository builds its own GMP history and shows how each IPO's GMP moved since the previous run.
Standard library only; Python 3.9+. GMP is an unofficial, indicative grey-market figure, not investment advice.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.apify.com/v2"
ACTOR = "data_daemon~india-ipo-tracker"  # https://apify.com/data_daemon/india-ipo-tracker
COLUMNS = ["date", "ipoName", "category", "status", "gmp", "gmpPercent", "issuePrice", "estimatedListingPrice", "subscription",
           "issueSizeCr", "lotSize", "openDate", "closeDate", "allotmentDate", "listingDate", "updatedOn", "url"]
ROOT = Path(__file__).resolve().parent
STATUS_ORDER = {"Open": 0, "Upcoming": 1, "Closed": 2}


def request(method, url, token, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.load(res)


def run_actor(run_input, token, max_charge_usd):
    query = urllib.parse.urlencode({"timeout": 600, "maxTotalChargeUsd": max_charge_usd})
    run = request("POST", f"{API}/acts/{ACTOR}/runs?{query}", token, run_input)["data"]
    while run["status"] in ("READY", "RUNNING"):
        time.sleep(4)
        run = request("GET", f"{API}/actor-runs/{run['id']}", token)["data"]
    if run["status"] != "SUCCEEDED":
        raise RuntimeError(f"run {run['id']} ended {run['status']}: {run.get('statusMessage')}")
    return request("GET", f"{API}/datasets/{run['defaultDatasetId']}/items?clean=1&format=json&limit=1000", token), run.get("statusMessage") or ""


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def to_row(today, ipo):
    price, gmp = num(ipo.get("issuePrice")), num(ipo.get("gmp"))
    return {
        "date": today,
        "ipoName": ipo.get("ipoName") or "",
        "category": ipo.get("category") or "",
        "status": ipo.get("statusLabel") or ipo.get("status") or "",
        "gmp": "" if gmp is None else f"{gmp:g}",
        "gmpPercent": "" if ipo.get("gmpPercent") is None else f"{num(ipo.get('gmpPercent')):g}",
        "issuePrice": "" if price is None else f"{price:g}",
        "estimatedListingPrice": "" if price is None or gmp is None else f"{price + gmp:g}",
        "subscription": "" if ipo.get("subscriptionText") in (None, "-") else ipo["subscriptionText"],
        "issueSizeCr": ipo.get("issueSizeCr") if ipo.get("issueSizeCr") is not None else "",
        "lotSize": ipo.get("lotSize") if ipo.get("lotSize") is not None else "",
        "openDate": ipo.get("openDate") or "",
        "closeDate": ipo.get("closeDate") or "",
        "allotmentDate": ipo.get("allotmentDate") or "",
        "listingDate": ipo.get("listingDate") or "",
        "updatedOn": ipo.get("updatedOn") or "",
        "url": ipo.get("url") or "",
    }


def day(iso):
    """2026-10-27 -> 27 Oct"""
    try:
        return dt.date.fromisoformat(iso).strftime("%d %b").lstrip("0")
    except ValueError:
        return iso


def previous_gmp(history_path, today):
    """GMP of each IPO in the most recent snapshot before today."""
    if not history_path.exists():
        return {}
    with history_path.open(encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["date"] < today]
    if not rows:
        return {}
    last = max(r["date"] for r in rows)
    return {r["ipoName"]: num(r["gmp"]) for r in rows if r["date"] == last}


def write_outputs(rows, data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    history = data_dir / "gmp-history.csv"
    today = rows[0]["date"] if rows else dt.date.today().isoformat()
    before = previous_gmp(history, today)
    existing = []
    if history.exists():
        with history.open(encoding="utf-8", newline="") as f:
            existing = [r for r in csv.DictReader(f) if r["date"] != today]  # re-running on the same day replaces the snapshot
    with history.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(existing + rows)
    live = sorted((r for r in rows if r["status"] in ("Open", "Upcoming")),
                  key=lambda r: (STATUS_ORDER.get(r["status"], 9), r["openDate"], -(num(r["gmpPercent"]) or 0)))
    for r in live:
        prev, cur = before.get(r["ipoName"]), num(r["gmp"])
        r["change"] = "" if prev is None or cur is None else f"{cur - prev:+g}"
    lines = [f"# IPO GMP today ({today})", "",
             f"{len(live)} open or upcoming IPOs. GMP is the unofficial grey-market premium in ₹ per share; "
             "estimated listing price = issue price + GMP. History: [gmp-history.csv](gmp-history.csv).", ""]
    if live:
        lines += ["| IPO | Type | Status | Open – close | Listing | Price ₹ | GMP ₹ | GMP % | Est. listing ₹ | Change | Subscription |",
                  "|---|---|---|---|---|---:|---:|---:|---:|---:|---|"]
        lines += [f"| [{r['ipoName']}]({r['url']}) | {r['category']} | {r['status']} | {day(r['openDate'])} – {day(r['closeDate'])} | "
                  f"{day(r['listingDate'])} | {r['issuePrice']} | {r['gmp']} | {r['gmpPercent']} | {r['estimatedListingPrice']} | "
                  f"{r['change']} | {r['subscription']} |" for r in live]
    (data_dir / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return live


def post_json(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    urllib.request.urlopen(req, timeout=60).read()


def notify(live, cfg):
    picked = [r for r in live if (not cfg.get("mainboardOnly") or r["category"] == "Mainboard")
              and (num(r["gmpPercent"]) or 0) >= cfg.get("minGmpPercent", 0)]
    if not picked:
        print("nothing to send")
        return
    text = f"IPO GMP today ({live[0]['date']})\n" + "\n".join(
        f"• {r['ipoName']} ({r['category']}, {r['status'].lower()} {day(r['openDate'])}–{day(r['closeDate'])}): "
        f"GMP ₹{r['gmp']} ({r['gmpPercent']}%){' ' + r['change'] if r['change'] else ''}, price ₹{r['issuePrice']}"
        f"{', subscribed ' + r['subscription'] if r['subscription'] else ''}" for r in picked[:25])
    channels = []
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        channels.append(("Telegram", f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
                         {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:4000], "disable_web_page_preview": True}, None))
    if os.environ.get("SLACK_WEBHOOK_URL"):
        channels.append(("Slack", os.environ["SLACK_WEBHOOK_URL"], {"text": text}, None))
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        channels.append(("Discord", os.environ["DISCORD_WEBHOOK_URL"], {"content": text[:1990]}, None))
    repo, gh = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if cfg.get("githubIssue", False) and repo and gh:
        channels.append(("GitHub issue", f"https://api.github.com/repos/{repo}/issues",
                         {"title": f"IPO GMP {live[0]['date']}", "body": text.replace("• ", "- ")},
                         {"Authorization": f"Bearer {gh}", "Accept": "application/vnd.github+json"}))
    for name, url, payload, headers in channels:
        try:  # a broken channel must not lose the day's snapshot
            post_json(url, payload, headers)
            print("notified:", name)
        except urllib.error.URLError as err:
            print(f"could not notify {name}: {err}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", default=str(ROOT / "config.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    run_input = {"reports": ["gmp"], "category": cfg.get("category", "all")}
    if a.dry_run:
        print(json.dumps(run_input))
        return
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Set APIFY_TOKEN (Apify Console > Settings > Integrations). In GitHub: Settings > Secrets > Actions.")
    items, status = run_actor(run_input, token, cfg.get("maxCostPerRunUsd", 0.5))
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date().isoformat()  # India date
    rows = [to_row(today, i) for i in items if i.get("reportType") == "gmp"]
    print(f"{len(rows)} IPOs in the GMP report | {status}")
    live = write_outputs(rows, ROOT / cfg.get("dataDir", "data"))
    notify(live, cfg.get("notify", {}))


if __name__ == "__main__":
    main()
