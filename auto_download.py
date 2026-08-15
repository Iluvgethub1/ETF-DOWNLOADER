from pathlib import Path
from datetime import datetime, timezone
import io
import zipfile
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
TICKER_FILE = ROOT / "auto_tickers.txt"
EXPORT_DIR = ROOT / "daily_exports"
EXPORT_DIR.mkdir(exist_ok=True)

def load_tickers():
    raw = TICKER_FILE.read_text(encoding="utf-8")
    tickers = []
    for line in raw.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        for item in line.replace(",", " ").split():
            t = item.strip().upper()
            if t and t not in tickers:
                tickers.append(t)
    return tickers

def main():
    tickers = load_tickers()
    if not tickers:
        raise SystemExit("No tickers found in auto_tickers.txt")

    raw = yf.download(
        tickers=tickers,
        period="5d",
        interval="1d",
        auto_adjust=False,
        actions=False,
        group_by="column",
        threads=True,
        progress=False,
        timeout=30,
    )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    frames = {}
    for ticker in tickers:
        try:
            one = raw.copy()
            if isinstance(one.columns, pd.MultiIndex):
                for level in range(one.columns.nlevels):
                    if ticker in set(map(str, one.columns.get_level_values(level))):
                        one = one.xs(ticker, axis=1, level=level, drop_level=True)
                        break
            if one is None or one.empty:
                continue
            if getattr(one.index, "tz", None) is not None:
                one.index = one.index.tz_localize(None)
            one.index.name = "Date"
            one = one.reset_index()
            one.insert(1, "Ticker", ticker)
            if "Close" in one.columns:
                one = one[one["Close"].notna()]
            if not one.empty:
                frames[ticker] = one
        except Exception:
            pass

    if not frames:
        raise SystemExit("No data returned.")

    zip_path = EXPORT_DIR / f"DAILY_MARKET_SNAPSHOT_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        combined = []
        for ticker, df in sorted(frames.items()):
            z.writestr(f"{ticker}.csv", df.to_csv(index=False))
            combined.append(df)
        z.writestr(
            "ALL_TICKERS.csv",
            pd.concat(combined, ignore_index=True).to_csv(index=False),
        )

    # Keep the repository from growing forever: retain the most recent 45 ZIPs.
    files = sorted(EXPORT_DIR.glob("DAILY_MARKET_SNAPSHOT_*.zip"))
    for old in files[:-45]:
        old.unlink()

    print(f"Created {zip_path}")

if __name__ == "__main__":
    main()
