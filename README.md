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


## Mutual-fund directory fix

This build no longer tries to read the retired/broken Nasdaq HTTP mutual-fund URL.

It retrieves `mfundslist.txt` from Nasdaq Trader's official symbol-directory FTP service and parses it line-by-line so malformed/footer lines do not crash the Mutual Funds tab.

It also uses Nasdaq's own **Fund Family Name** field for the mutual-fund institution/fund-family selector instead of trying to guess the family from the fund name.


## Expanded categories for BOTH tabs
ETFs and mutual funds now use the same expanded category engine. Exports include the Sector_Category column and By_Sector folders for equity sectors, bond types/durations, cash, geography, size/style, allocation/target-date, commodities, crypto/currency, derivatives, leveraged/inverse, and thematic products. Unmatched products receive a Diversified_Other label instead of Unclassified.
