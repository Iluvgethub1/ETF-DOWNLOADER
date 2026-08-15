# ETF Downloader — Intervals + Custom Date Ranges + Automatic Daily Snapshot

This version adds one-click historical year blocks plus exact custom date ranges.

### Easy year blocks
Choose **Year block**, then choose 1, 2, 3, 5, or 10 years per block.
- Block 1 = most recent block
- Block 2 = immediately preceding block
- Block 3 = the block before that

Example with 2-year blocks on August 15, 2026:
- Block 1: Aug 15, 2024 → Aug 15, 2026
- Block 2: Aug 15, 2022 → Aug 15, 2024
- Block 3: Aug 15, 2020 → Aug 15, 2022

You do not need to type dates unless you choose Custom date range.

For each major section you can choose:

- **Recent period** — examples: 2y, 5y, 10y, max
- **Custom date range** — choose an exact Start Date and End Date

Example:

- First download: 2024-08-15 to 2026-08-15
- Previous two years: 2022-08-15 to 2024-08-15
- Earlier two years: 2020-08-15 to 2022-08-15

This works especially well for Daily data.

Intraday data (Hourly, 30-minute, 15-minute) is subject to the upstream provider's historical intraday limits. Choosing an old custom range does not guarantee Yahoo Finance will provide that older intraday history.

The package still includes:
- Institution-based ETF batches
- Short-term bond / defensive analyzer
- Market indicators
- Daily / Hourly / 30-minute / 15-minute interval choices
- Optional automatic weekday snapshots through GitHub Actions

## Update your live site

Copy all files and folders into the root of your existing `ETF-DOWNLOADER` repository.

Replace the old:
- app.py
- README.md
- requirements.txt

Keep/add:
- auto_download.py
- auto_tickers.txt
- .github/workflows/daily_market_update.yml

Then in GitHub Desktop:
1. Commit to main
2. Push origin

Streamlit should redeploy automatically.
