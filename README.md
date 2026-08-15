# ETF Downloader — Intervals + Custom Date Ranges + Automatic Daily Snapshot

This version adds exact historical date-range selection.

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
