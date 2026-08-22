# ETF + Mutual Fund Downloader

This app combines the ETF downloader and a mutual-fund downloader into one Streamlit website.

## Tabs

- ETFs
- Mutual Funds

Both use the same workflow:
- institution / fund family
- batch size and batch number
- recent-period downloads
- clickable 1, 2, 3, 5, or 10-year historical blocks
- custom date ranges
- CSV files inside ZIP downloads
- sector/category folders
- combined batch CSV
- failed-ticker list when needed

## ETF data intervals

ETFs support:
- Daily
- Hourly
- 30 minute
- 15 minute

Intraday history depends on upstream Yahoo Finance availability.

## Mutual fund data interval

Mutual funds generally publish one NAV per trading day, so the Mutual Fund tab intentionally uses Daily data.

## Updating your existing Streamlit site

Replace the current app.py, requirements.txt, and README.md in the ETF-DOWNLOADER GitHub repository with the files from this package.

Then in GitHub Desktop:
1. Commit to main
2. Push origin

Streamlit should redeploy automatically.
