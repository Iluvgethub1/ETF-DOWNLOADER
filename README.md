# Batched Mutual Fund Downloader

GitHub-ready Streamlit app for downloading mutual-fund historical prices in ZIP batches.

## Files

- `app.py` — Streamlit web application
- `requirements.txt` — Python packages for Streamlit Community Cloud
- `mutual_funds.csv` — mutual-fund database used by the app

## Mutual-fund database format

`mutual_funds.csv` must contain at least one ticker column named:

- `symbol`, or
- `ticker`

Recommended columns:

```text
symbol,fund_name,institution,category
VFIAX,Vanguard 500 Index Fund Admiral Shares,Vanguard,Large Blend
FXAIX,Fidelity 500 Index Fund,Fidelity,Large Blend
```

The app also recognizes `fund_family`, `family`, `sponsor`, `issuer`, or
`fund_company` as the institution/fund-family column.

Replace the sample CSV with your full mutual-fund database when ready.

## Put it on GitHub

1. Create a new GitHub repository.
2. Upload:
   - `app.py`
   - `requirements.txt`
   - `mutual_funds.csv`
3. Commit the files.
4. Open Streamlit Community Cloud.
5. Choose **New app**.
6. Select your GitHub repository and branch.
7. Set the main file path to:
   `app.py`
8. Deploy.

When you later update the mutual-fund database, replace `mutual_funds.csv`
in GitHub and commit it. Streamlit will pick up the repository update.

## What a ZIP contains

For every successful mutual-fund ticker:

- one CSV named after the ticker

It also contains:

- `ALL_MUTUAL_FUNDS_COMBINED.csv`
- `MANIFEST.csv`
- `ERRORS.csv` when failures occur
- `README.txt`

## Important

The app downloads historical data from Yahoo Finance through `yfinance`.

Mutual funds may be renamed, merged, liquidated, converted, or unavailable
from Yahoo Finance. Failed symbols are written to `ERRORS.csv` rather than
stopping the whole batch.
