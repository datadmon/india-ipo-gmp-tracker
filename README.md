# India IPO GMP Tracker: today's grey market premium, with history and Telegram alerts

Track the **IPO GMP (grey market premium)** of every open and upcoming **mainboard and SME IPO** in India, once a day, with the **estimated listing price**, **subscription**, price band, lot size and the **open, close, allotment and listing dates**. Each run saves a dated snapshot, so your copy of this repository builds its own **GMP history** and shows how each IPO's GMP moved since the previous run. Alerts go to **Telegram**, Slack, Discord or a GitHub issue.

No scraping code to maintain: a GitHub Actions workflow calls the [India IPO Tracker](https://apify.com/data_daemon/india-ipo-tracker) on Apify, which reads InvestorGain's GMP report.

![Outputs](https://img.shields.io/badge/output-Telegram%20%7C%20Slack%20%7C%20Discord%20%7C%20CSV%20%7C%20Markdown-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Today's table

[`data/latest.md`](data/latest.md) is rewritten on every run. From the run on 26 October 2026 (10 open or upcoming IPOs out of 30 in the report; a few rows):

| IPO | Type | Status | Open – close | Listing | Price ₹ | GMP ₹ | GMP % | Est. listing ₹ |
|---|---|---|---|---|---:|---:|---:|---:|
| [BLS Polymers](https://www.investorgain.com/gmp/bls-polymers-ipo/1849/) | Mainboard | Upcoming | 27 Oct – 29 Oct | 3 Nov | 150 | 38 | 25.33 | 188 |
| [EAAA India Alternatives](https://www.investorgain.com/gmp/eaaa-india-alternatives-ipo/1635/) | Mainboard | Upcoming | 26 Oct – 28 Oct | 2 Nov | 1665 | 121 | 1.98 | 1786 |
| [SFC Environmental Technologies](https://www.investorgain.com/gmp/sfc-environmental-technologies-ipo/1642/) | Mainboard | Upcoming | 27 Oct – 29 Oct | 3 Nov | 330 | 32 | 9.7 | 362 |
| [Bombay Coated and Special Steels](https://www.investorgain.com/gmp/bombay-coated-and-special-steels-ipo/1936/) | Mainboard | Upcoming | 29 Oct – 2 Nov | 5 Nov | 82 | 8 | 9.76 | 90 |
| [Core4 Engineers](https://www.investorgain.com/gmp/core4-engineers-ipo/2229/) | SME | Open (0.08x subscribed) | 23 Oct – 27 Oct | 30 Oct | 93 | 0 | 0 | 93 |

From the second run on, a **Change** column shows the GMP move in ₹ since the previous snapshot. The full history is in [`data/gmp-history.csv`](data/gmp-history.csv): one row per IPO per day with GMP, GMP %, issue price, estimated listing price, subscription, issue size, lot size and all dates. Load it in Excel, Google Sheets or pandas to chart how GMP behaves before listing.

## Set it up in five minutes

1. Click **Use this template → Create a new repository**.
2. Create a free [Apify](https://apify.com) account, copy your API token from **Console → Settings → Integrations**, and add it in your repository under **Settings → Secrets and variables → Actions** as `APIFY_TOKEN`.
3. Add the workflow: **Add file → Create new file**, name it `.github/workflows/ipo-gmp.yml`, paste the contents of [`setup/ipo-gmp.yml`](setup/ipo-gmp.yml) and commit.
4. For Telegram alerts, create a bot with [@BotFather](https://t.me/BotFather) and add `TELEGRAM_BOT_TOKEN` and your chat or channel ID as `TELEGRAM_CHAT_ID`. Then run **Actions → IPO GMP tracker → Run workflow** once. It runs every day at 10:00 and 18:00 IST.

## Configuration

```json
{
  "category": "all",
  "maxCostPerRunUsd": 0.5,
  "notify": {"githubIssue": false, "mainboardOnly": false, "minGmpPercent": 0}
}
```

| Field | What it does |
|---|---|
| `category` | `all`, `mainboard` or `sme`. |
| `notify.mainboardOnly` | Send alerts for mainboard IPOs only (the table and history keep everything). |
| `notify.minGmpPercent` | Only alert about IPOs with at least this GMP %, for example `10`. |
| `notify.githubIssue` | Also open a GitHub issue per run. |
| `maxCostPerRunUsd` | Hard cap per run. |

Slack (`SLACK_WEBHOOK_URL`) and Discord (`DISCORD_WEBHOOK_URL`) work the same way as Telegram: add the secret and the alert is sent there too.

## What it costs

The [India IPO Tracker](https://apify.com/data_daemon/india-ipo-tracker) charges **$0.003 per report row** on Apify's free plan (26 October 2026). The GMP report has about 30 rows, so a run costs about $0.09 and two runs a day about **$5 a month**; Apify's free plan includes $5 of usage every month. Run once a day (edit the `cron` line) to halve it. `maxCostPerRunUsd` caps every run.

## What the columns mean

- **GMP**: the unofficial premium in ₹ per share at which IPO shares change hands in the grey market before listing, as reported by InvestorGain. It is indicative only, changes during the day and is not regulated.
- **GMP %**: GMP divided by the issue price (the upper end of the price band).
- **Estimated listing price**: issue price + GMP. Actual listing prices often differ.
- **Subscription**: times subscribed so far, when the issue is open.
- **Status**: `Open`, `Upcoming` or `Closed` as reported; the table keeps open and upcoming issues.

## Run it without GitHub Actions

```bash
export APIFY_TOKEN=...
python ipo_gmp_tracker.py --dry-run
python ipo_gmp_tracker.py
```

Python 3.9+, standard library only. Schedule it with cron or Windows Task Scheduler if you prefer.

## FAQ

**Is there an official IPO GMP API?**
No. GMP is grey-market information published by sites such as InvestorGain and Chittorgarh. The India IPO Tracker returns their reports as clean JSON rows: GMP, subscription status, the IPO calendar, listing performance and full IPO detail pages.

**Can I get subscription by investor category (QIB, NII, retail) or the listing-day gains?**
Yes, from the same Actor with other reports (`subscription`, `listingPerformance`, `gmpPerformance`, `calendar`); see its [README](https://apify.com/data_daemon/india-ipo-tracker). This repository keeps to the GMP table to stay cheap.

**Why do some SME IPOs show a GMP of 0?**
InvestorGain shows "₹--" until grey-market quotes appear; the tracker records that as 0.

## Related

- [India IPO Tracker](https://apify.com/data_daemon/india-ipo-tracker) on Apify: GMP, subscription, calendar and listing performance as an API.
- [India IPO GMP and subscription data as JSON](https://datadmon.github.io/guides/india-ipo-gmp-subscription-data-json/): guide to the reports and fields.
- [apify-data-actors-examples](https://github.com/datadmon/apify-data-actors-examples): Python, Node.js, curl and n8n examples.

GMP data is unofficial and indicative; nothing here is investment advice. Not affiliated with InvestorGain, Chittorgarh, NSE or BSE.
