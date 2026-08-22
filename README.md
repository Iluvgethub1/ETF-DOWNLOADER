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


## Mutual-fund source update (NFN Web Service)

This build no longer depends on Nasdaq Trader's legacy FTP path.

It first uses Nasdaq Fund Network's documented `InstrumentDirectory` web service and requests CSV.
If that fails, it tries the legacy Nasdaq web-hosted directory. The parser accepts multiple current
and historical field names because Nasdaq's NFN directory schema has evolved.

There is also a manual mutual-fund ticker fallback. If Nasdaq changes the public directory again,
you can still enter mutual-fund symbols and use the same year-block, batch, CSV and ZIP workflow.


## SEC mutual-fund directory source

This build uses the SEC's public `company_tickers_mf.json` file for mutual-fund
ticker/series/class associations instead of Nasdaq's FTP/NFN endpoints.

That SEC file is intended for fund CIK, series, class and ticker associations.
Historical NAV/price downloads still come from Yahoo Finance through yfinance.

The manual ticker fallback remains available if the SEC endpoint is temporarily unavailable.


## One representative share class per fund
The Mutual Funds tab now defaults to one representative ticker per SEC Series_ID. This removes most duplicate retail, institutional, advisor, and other share classes of the same underlying fund. You can still switch to All share classes if needed. The chosen representative class is for data deduplication only, not an investment recommendation.
