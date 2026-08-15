# ETF Downloader — Intervals + Automatic Daily Snapshot

This update keeps the ETF institution batches, short-term bond analyzer, and market indicators.

## New manual data intervals

The Streamlit site now lets you choose:

- Daily (1d)
- Hourly (1h)
- 30 minute (30m)
- 15 minute (15m)

Daily data offers the longest history choices. Intraday choices intentionally use shorter lookback options.

The short 1-to-15-trading-day statistical analysis is calculated only when Daily (1d) is selected. Intraday selections still export the raw CSV files.

## Optional automatic daily snapshot

This package also contains:

- `auto_download.py`
- `auto_tickers.txt`
- `.github/workflows/daily_market_update.yml`

When those files are pushed to GitHub, GitHub Actions can run on weekdays after the U.S. market closes. It downloads a small daily snapshot for the tickers listed in `auto_tickers.txt` and saves a ZIP in `daily_exports/`.

You can edit `auto_tickers.txt` whenever you want to change the automatic list.

The workflow keeps only the most recent 45 automatic ZIP snapshots to reduce repository growth.

## Updating your existing site

Copy all files/folders from this update into the root of your existing `ETF-DOWNLOADER` repository. Replace the old `app.py`, `README.md`, and `requirements.txt`. Keep the new `.github/workflows` folder, `auto_download.py`, and `auto_tickers.txt`.

Then use GitHub Desktop:

1. Commit the changes to `main`.
2. Push origin.

Streamlit should redeploy automatically. GitHub Actions may ask you to enable Actions for the repository the first time.
