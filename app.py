
import io
import math
import re
import time
import zipfile
from datetime import date

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Batched ETF Downloader",
    page_icon="📦",
    layout="wide",
)

NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"

st.title("📦 Batched ETF Downloader")
st.write(
    "Download large ETF universes in smaller ZIP batches so the app is less likely "
    "to hit memory or rate limits."
)

ISSUER_PATTERNS = [
    ("BlackRock_iShares", [r"\biShares\b", r"\bBlackRock\b"]),
    ("Vanguard", [r"\bVanguard\b"]),
    ("State_Street_SPDR", [r"\bSPDR\b", r"\bState Street\b"]),
    ("Invesco", [r"\bInvesco\b", r"\bPowerShares\b"]),
    ("Charles_Schwab", [r"\bSchwab\b"]),
    ("Fidelity", [r"\bFidelity\b"]),
    ("JPMorgan", [r"\bJPMorgan\b", r"\bJ\.P\. Morgan\b", r"\bJPM\b"]),
    ("Goldman_Sachs", [r"\bGoldman Sachs\b"]),
    ("Franklin_Templeton", [r"\bFranklin\b", r"\bTempleton\b"]),
    ("PIMCO", [r"\bPIMCO\b"]),
    ("First_Trust", [r"\bFirst Trust\b"]),
    ("ProShares", [r"\bProShares\b"]),
    ("Direxion", [r"\bDirexion\b"]),
    ("Global_X", [r"\bGlobal X\b"]),
    ("VanEck", [r"\bVanEck\b"]),
    ("WisdomTree", [r"\bWisdomTree\b"]),
    ("ARK_Invest", [r"\bARK\b"]),
    ("Innovator", [r"\bInnovator\b"]),
    ("Amplify", [r"\bAmplify\b"]),
    ("Simplify", [r"\bSimplify\b"]),
    ("Roundhill", [r"\bRoundhill\b"]),
    ("Defiance", [r"\bDefiance\b"]),
    ("Janus_Henderson", [r"\bJanus Henderson\b"]),
    ("PGIM", [r"\bPGIM\b"]),
    ("YieldMax", [r"\bYieldMax\b"]),
]

SECTOR_PATTERNS = [
    ("Technology", [r"technology", r"\btech\b", r"semiconductor", r"software", r"cyber", r"cloud", r"artificial intelligence", r"robot"]),
    ("Financials", [r"financial", r"bank", r"insurance", r"capital markets", r"fintech"]),
    ("Energy", [r"\benergy\b", r"\boil\b", r"\bgas\b", r"midstream", r"pipeline", r"uranium"]),
    ("Healthcare", [r"health", r"biotech", r"pharma", r"medical", r"genomic"]),
    ("Industrials", [r"industrial", r"aerospace", r"defense", r"transport", r"construction", r"infrastructure", r"machinery"]),
    ("Consumer_Discretionary", [r"consumer discretionary", r"retail", r"e-commerce", r"travel", r"leisure", r"automotive"]),
    ("Consumer_Staples", [r"consumer staples", r"food", r"beverage"]),
    ("Utilities", [r"utilities", r"utility"]),
    ("Materials", [r"materials", r"metals", r"mining", r"steel", r"copper", r"lithium", r"chemicals", r"timber"]),
    ("Real_Estate", [r"real estate", r"\bREIT"]),
    ("Communication_Services", [r"communication services", r"telecom", r"media", r"internet", r"social media"]),
    ("Fixed_Income", [r"bond", r"treasury", r"municipal", r"muni", r"credit", r"fixed income", r"debt", r"high yield", r"corporate", r"floating rate"]),
    ("Commodities", [r"gold", r"silver", r"commodity", r"commodities", r"precious metals", r"natural gas", r"crude oil"]),
    ("International", [r"international", r"emerging market", r"developed market", r"Europe", r"Asia", r"Japan", r"China", r"India", r"Brazil", r"Latin America"]),
    ("Broad_Market", [r"S&P 500", r"total stock", r"total market", r"Russell 1000", r"Russell 2000", r"Russell 3000", r"large[- ]cap", r"mid[- ]cap", r"small[- ]cap", r"dividend", r"\bvalue\b", r"\bgrowth\b", r"quality", r"momentum"]),
    ("Thematic_Other", [r"clean energy", r"solar", r"wind", r"water", r"space", r"cannabis", r"blockchain", r"bitcoin", r"crypto", r"metaverse", r"gaming", r"innovation"]),
]

def classify(text, patterns, default):
    text = str(text or "")
    for label, pats in patterns:
        if any(re.search(p, text, flags=re.IGNORECASE) for p in pats):
            return label
    return default

@st.cache_data(ttl=3600)
def read_pipe(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), sep="|")
    first = df.columns[0]
    return df[~df[first].astype(str).str.startswith("File Creation Time", na=False)]

@st.cache_data(ttl=3600)
def get_universe():
    n = read_pipe(NASDAQ_LISTED)
    o = read_pipe(OTHER_LISTED)

    n = n[(n["ETF"] == "Y") & (n["Test Issue"] == "N")].copy()
    n = n.rename(columns={"Symbol":"Ticker", "Security Name":"Fund_Name"})
    n["Exchange"] = "Nasdaq"

    o = o[(o["ETF"] == "Y") & (o["Test Issue"] == "N")].copy()
    o = o.rename(columns={"ACT Symbol":"Ticker", "Security Name":"Fund_Name"})

    u = pd.concat(
        [n[["Ticker","Fund_Name","Exchange"]], o[["Ticker","Fund_Name","Exchange"]]],
        ignore_index=True
    )
    u["YahooTicker"] = u["Ticker"].astype(str).str.replace(".", "-", regex=False)
    u["Issuer_Group"] = u["Fund_Name"].map(lambda x: classify(x, ISSUER_PATTERNS, "Other_or_Unknown"))
    u["Sector_Category"] = u["Fund_Name"].map(lambda x: classify(x, SECTOR_PATTERNS, "Unclassified"))
    return u.drop_duplicates("YahooTicker").sort_values("YahooTicker").reset_index(drop=True)

def normalize(df, ticker, meta):
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        for level in range(out.columns.nlevels):
            if ticker in set(map(str, out.columns.get_level_values(level))):
                out = out.xs(ticker, axis=1, level=level, drop_level=True)
                break

    if out.empty:
        return pd.DataFrame()

    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_localize(None)

    out.index.name = "Date"
    out = out.reset_index()
    out.insert(1, "Ticker", ticker)
    out.insert(2, "Issuer_Group", meta["Issuer_Group"])
    out.insert(3, "Sector_Category", meta["Sector_Category"])
    out.insert(4, "Fund_Name", meta["Fund_Name"])

    if "Close" in out.columns:
        out = out[out["Close"].notna()]

    return out

def safe_name(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("_") or "Unknown"

def download_chunk(chunk_df, period):
    tickers = chunk_df["YahooTicker"].tolist()
    raw = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=False,
        actions=False,
        group_by="column",
        threads=True,
        progress=False,
        timeout=30,
    )

    meta = chunk_df.set_index("YahooTicker")
    results = {}
    failed = []

    for ticker in tickers:
        row = meta.loc[ticker]
        one = pd.DataFrame()

        try:
            one = normalize(raw, ticker, row)
        except Exception:
            pass

        if one.empty:
            try:
                retry = yf.download(
                    ticker,
                    period=period,
                    interval="1d",
                    auto_adjust=False,
                    actions=False,
                    progress=False,
                    timeout=20,
                )
                one = normalize(retry, ticker, row)
            except Exception:
                one = pd.DataFrame()

        if one.empty:
            failed.append(ticker)
        else:
            results[ticker] = one

    return results, failed

def build_batch_zip(results, batch_df, failed, batch_number, total_batches, period):
    buf = io.BytesIO()
    all_frames = []
    by_issuer = {}
    by_sector = {}

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for ticker, df in sorted(results.items()):
            issuer = safe_name(df["Issuer_Group"].iloc[0])
            sector = safe_name(df["Sector_Category"].iloc[0])

            z.writestr(
                f"By_Institution/{issuer}/{sector}/{ticker}.csv",
                df.to_csv(index=False)
            )
            all_frames.append(df)
            by_issuer.setdefault(issuer, []).append(df)
            by_sector.setdefault(sector, []).append(df)

        if all_frames:
            z.writestr(
                "BATCH_ALL_ETFS.csv",
                pd.concat(all_frames, ignore_index=True).to_csv(index=False)
            )

        for issuer, frames in by_issuer.items():
            z.writestr(
                f"By_Institution/{issuer}/ALL_{issuer}_ETFS_IN_THIS_BATCH.csv",
                pd.concat(frames, ignore_index=True).to_csv(index=False)
            )

        for sector, frames in by_sector.items():
            z.writestr(
                f"By_Sector/{sector}/ALL_{sector}_ETFS_IN_THIS_BATCH.csv",
                pd.concat(frames, ignore_index=True).to_csv(index=False)
            )

        z.writestr("BATCH_ETF_LIST.csv", batch_df.to_csv(index=False))

        if failed:
            z.writestr("FAILED_TICKERS.txt", "\n".join(sorted(set(failed))))

        z.writestr(
            "README.txt",
            (
                "ETF Batch Download\n"
                "==================\n\n"
                f"Batch: {batch_number} of {total_batches}\n"
                f"Created: {date.today().isoformat()}\n"
                f"Daily history: {period}\n"
                f"ETF symbols assigned to this batch: {len(batch_df)}\n"
                f"Successful downloads: {len(results)}\n"
                f"Failed downloads: {len(set(failed))}\n\n"
                "This ZIP is one piece of a larger ETF-universe download.\n"
                "Upload one or several batch ZIPs to ChatGPT for analysis.\n"
            )
        )

    buf.seek(0)
    return buf.getvalue()

try:
    universe = get_universe()
except Exception as e:
    st.error(f"Could not load ETF universe: {e}")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("ETF symbols", f"{len(universe):,}")
c2.metric("Institutions", f"{universe['Issuer_Group'].nunique():,}")
c3.metric("Sectors/categories", f"{universe['Sector_Category'].nunique():,}")

st.subheader("1. Choose institution and history")

institution_options = ["All Institutions"] + sorted(universe["Issuer_Group"].unique().tolist())
institution = st.selectbox(
    "Financial institution / ETF sponsor",
    institution_options,
    index=0,
)

period = st.selectbox(
    "Daily history",
    ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
    index=7,
)

batch_size = st.select_slider(
    "ETFs per ZIP batch",
    options=[100, 150, 200, 250, 300, 400, 500],
    value=200,
    help="For 10-year history, 150–200 ETFs per batch is recommended."
)

if institution == "All Institutions":
    institution_df = universe.copy()
    institution_label = "ALL_INSTITUTIONS"
else:
    institution_df = universe[universe["Issuer_Group"] == institution].copy()
    institution_label = safe_name(institution)

total_batches = max(1, math.ceil(len(institution_df) / batch_size))

st.info(
    f"{institution}: {len(institution_df):,} ETF symbols. "
    f"At {batch_size} ETFs per ZIP, this institution/group requires {total_batches} batch(es)."
)

st.subheader("2. Choose the institution batch")

batch_number = st.number_input(
    "Batch number",
    min_value=1,
    max_value=total_batches,
    value=1,
    step=1,
)

start_row = (batch_number - 1) * batch_size
end_row = min(start_row + batch_size, len(institution_df))
batch_df = institution_df.iloc[start_row:end_row].copy()

st.write(
    f"{institution} — Batch {batch_number} of {total_batches}: "
    f"{len(batch_df):,} ETF(s)."
)

with st.expander("Preview this institution batch"):
    st.dataframe(
        batch_df[["YahooTicker","Fund_Name","Issuer_Group","Sector_Category"]],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("3. Build the ZIP")

if st.button("Build institution batch ZIP", type="primary", use_container_width=True):
    if batch_df.empty:
        st.warning("This batch has no ETF symbols.")
    else:
        progress = st.progress(0)
        status = st.empty()

        request_chunk_size = 50
        request_chunks = [
            batch_df.iloc[i:i+request_chunk_size]
            for i in range(0, len(batch_df), request_chunk_size)
        ]

        all_results = {}
        all_failed = []

        for i, chunk in enumerate(request_chunks, 1):
            status.write(
                f"Downloading {institution} — request chunk {i} of {len(request_chunks)}..."
            )
            try:
                got, failed = download_chunk(chunk, period)
            except Exception:
                got, failed = {}, chunk["YahooTicker"].tolist()

            all_results.update(got)
            all_failed.extend(failed)
            progress.progress(i / len(request_chunks))

            if i < len(request_chunks):
                time.sleep(0.5)

        progress.empty()
        status.empty()

        if not all_results:
            st.error("No ETF data was downloaded for this institution batch.")
        else:
            bundle = build_batch_zip(
                all_results,
                batch_df,
                all_failed,
                batch_number,
                total_batches,
                period,
            )

            st.success(
                f"{institution} — Batch {batch_number} is ready: "
                f"{len(all_results):,} successful ETF downloads"
                + (f", {len(set(all_failed)):,} failed." if all_failed else ".")
            )

            stamp = date.today().isoformat()
            st.download_button(
                f"🗜️ Download {institution} — Batch {batch_number} of {total_batches}",
                data=bundle,
                file_name=(
                    f"{institution_label}_ETF_BATCH_{batch_number:02d}_OF_"
                    f"{total_batches:02d}_{stamp}_{period}.zip"
                ),
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )


st.divider()
st.header("🛡️ Short-Term Bond / Defensive Analyzer")
st.write(
    "Use this section for short holding periods from 1 day up to 3 weeks. "
    "It downloads several years of daily history so you can study many past short-term windows."
)

DEFENSIVE_BOND_ETFS = {
    "Treasury Bills / Ultra-Short": [
        "BIL", "SGOV", "SHV", "GBIL", "CLIP"
    ],
    "Short Treasury": [
        "SHY", "VGSH", "SCHO", "SPTS"
    ],
    "Floating / Ultra-Short Investment Grade": [
        "FLOT", "FLRN", "JPST", "ICSH", "MINT"
    ],
    "Short Corporate Investment Grade": [
        "VCSH", "SPSB", "IGSB", "SLQD"
    ],
    "TIPS / Inflation Protected": [
        "VTIP", "STIP", "SCHP"
    ],
}

st.subheader("Short-horizon bond ETF data")

bond_group = st.selectbox(
    "Bond / defensive group",
    ["All Short-Term Defensive Groups"] + list(DEFENSIVE_BOND_ETFS.keys()),
    key="bond_group"
)

bond_history = st.selectbox(
    "Historical data to download for analysis",
    ["1y", "2y", "5y", "10y", "max"],
    index=2,
    key="bond_history"
)

if bond_group == "All Short-Term Defensive Groups":
    bond_tickers = []
    for group_tickers in DEFENSIVE_BOND_ETFS.values():
        for ticker in group_tickers:
            if ticker not in bond_tickers:
                bond_tickers.append(ticker)
else:
    bond_tickers = DEFENSIVE_BOND_ETFS[bond_group]

st.caption("Selected bond ETFs: " + ", ".join(bond_tickers))

HOLD_WINDOWS = {
    "1 trading day": 1,
    "2 trading days": 2,
    "3 trading days": 3,
    "4 trading days": 4,
    "5 trading days / about 1 week": 5,
    "6 trading days": 6,
    "7 trading days": 7,
    "8 trading days": 8,
    "9 trading days": 9,
    "10 trading days / about 2 weeks": 10,
    "11 trading days": 11,
    "12 trading days": 12,
    "13 trading days": 13,
    "14 trading days": 14,
    "15 trading days / about 3 weeks": 15,
}

selected_windows = st.multiselect(
    "Short holding periods to calculate",
    options=list(HOLD_WINDOWS.keys()),
    default=[
        "1 trading day",
        "3 trading days",
        "5 trading days / about 1 week",
        "10 trading days / about 2 weeks",
        "15 trading days / about 3 weeks",
    ],
    key="bond_windows"
)

def download_bond_history(tickers, period):
    raw = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=False,
        actions=False,
        group_by="column",
        threads=True,
        progress=False,
        timeout=30,
    )
    out = {}
    for ticker in tickers:
        try:
            one = raw.copy()
            if isinstance(one.columns, pd.MultiIndex):
                ticker_level = None
                for level in range(one.columns.nlevels):
                    if ticker in set(map(str, one.columns.get_level_values(level))):
                        ticker_level = level
                        break
                if ticker_level is not None:
                    one = one.xs(ticker, axis=1, level=ticker_level, drop_level=True)

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
                out[ticker] = one
        except Exception:
            pass
    return out

def short_window_stats(df, ticker, selected_windows):
    if df.empty or "Close" not in df.columns:
        return pd.DataFrame()

    prices = df[["Date", "Close"]].copy().sort_values("Date")
    rows = []

    for label in selected_windows:
        days = HOLD_WINDOWS[label]
        future = prices["Close"].shift(-days)
        returns = (future / prices["Close"] - 1.0) * 100.0
        valid = returns.dropna()

        if valid.empty:
            continue

        rows.append({
            "Ticker": ticker,
            "Holding_Period": label,
            "Trading_Days": days,
            "Observations": int(valid.shape[0]),
            "Average_Return_%": float(valid.mean()),
            "Median_Return_%": float(valid.median()),
            "Best_Return_%": float(valid.max()),
            "Worst_Return_%": float(valid.min()),
            "Positive_Periods_%": float((valid > 0).mean() * 100.0),
        })

    return pd.DataFrame(rows)

def make_bond_zip(results, stats_df, group_name, history_period):
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        combined = []

        for ticker, df in sorted(results.items()):
            z.writestr(
                f"Bond_ETFs/{ticker}.csv",
                df.to_csv(index=False)
            )
            combined.append(df)

        if combined:
            z.writestr(
                "ALL_SHORT_TERM_BOND_ETFS.csv",
                pd.concat(combined, ignore_index=True).to_csv(index=False)
            )

        if stats_df is not None and not stats_df.empty:
            z.writestr(
                "SHORT_HOLDING_PERIOD_ANALYSIS.csv",
                stats_df.to_csv(index=False)
            )

        z.writestr(
            "README.txt",
            (
                "Short-Term Bond / Defensive ETF Export\n"
                "======================================\n\n"
                f"Created: {date.today().isoformat()}\n"
                f"Group: {group_name}\n"
                f"Historical lookback: {history_period}\n\n"
                "The historical data can span years, but the analysis windows are short:\n"
                "1 to 15 trading days, roughly 1 day through 3 weeks.\n\n"
                "This is designed for studying short holding periods, not for assuming "
                "that any bond ETF will necessarily rise during a market decline.\n"
            )
        )

    buf.seek(0)
    return buf.getvalue()

if st.button("Build short-term bond ZIP + analysis", type="primary", use_container_width=True, key="bond_build"):
    with st.spinner("Downloading bond ETF history and calculating short holding periods..."):
        bond_results = download_bond_history(bond_tickers, bond_history)

        stats_frames = []
        for ticker, df in bond_results.items():
            stats = short_window_stats(df, ticker, selected_windows)
            if not stats.empty:
                stats_frames.append(stats)

        stats_df = pd.concat(stats_frames, ignore_index=True) if stats_frames else pd.DataFrame()

        st.session_state["bond_results"] = bond_results
        st.session_state["bond_stats"] = stats_df
        st.session_state["bond_group_used"] = bond_group
        st.session_state["bond_history_used"] = bond_history

if "bond_results" in st.session_state:
    bond_results = st.session_state["bond_results"]
    stats_df = st.session_state["bond_stats"]
    bond_group_used = st.session_state["bond_group_used"]
    bond_history_used = st.session_state["bond_history_used"]

    if not bond_results:
        st.error("No bond ETF data was returned.")
    else:
        st.success(f"Loaded {len(bond_results)} short-term bond / defensive ETF(s).")

        if not stats_df.empty:
            st.subheader("Short holding-period comparison")
            display_stats = stats_df.copy()
            for col in [
                "Average_Return_%",
                "Median_Return_%",
                "Best_Return_%",
                "Worst_Return_%",
                "Positive_Periods_%"
            ]:
                display_stats[col] = display_stats[col].round(3)

            st.dataframe(
                display_stats.sort_values(
                    ["Trading_Days", "Average_Return_%"],
                    ascending=[True, False]
                ),
                use_container_width=True,
                hide_index=True
            )

        bond_zip = make_bond_zip(
            bond_results,
            stats_df,
            bond_group_used,
            bond_history_used
        )

        stamp = date.today().isoformat()
        safe_group = safe_name(bond_group_used)

        st.download_button(
            "🗜️ Download short-term bond ETF ZIP",
            data=bond_zip,
            file_name=f"SHORT_TERM_BOND_ETFS_{safe_group}_{stamp}_{bond_history_used}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
            key="bond_download"
        )

st.caption(
    "Short-horizon calculations use trading days, not calendar days. "
    "The 5-, 10-, and 15-trading-day windows are rough equivalents of about 1, 2, and 3 market weeks."
)


st.divider()
st.header("📊 Market Indicators")
st.write(
    "Download major U.S. stock indexes, volatility, Treasury-yield indicators, "
    "the U.S. dollar, gold, and crude oil. The app also calculates short-term "
    "changes from 1 through 15 trading days."
)

MARKET_INDICATORS = {
    "U.S. Stock Indexes": {
        "^GSPC": "S&P 500 Index",
        "^DJI": "Dow Jones Industrial Average",
        "^IXIC": "Nasdaq Composite",
        "^NDX": "Nasdaq-100 Index",
        "^RUT": "Russell 2000 Index",
    },
    "Volatility": {
        "^VIX": "CBOE Volatility Index (VIX)",
    },
    "Treasury Yield Indicators": {
        "^IRX": "13-Week Treasury Bill Yield",
        "^FVX": "5-Year Treasury Yield",
        "^TNX": "10-Year Treasury Yield",
        "^TYX": "30-Year Treasury Yield",
    },
    "Dollar / Commodities": {
        "DX-Y.NYB": "U.S. Dollar Index",
        "GC=F": "Gold Futures",
        "CL=F": "WTI Crude Oil Futures",
    },
    "Tradable Market Proxies": {
        "SPY": "SPDR S&P 500 ETF",
        "DIA": "SPDR Dow Jones Industrial Average ETF",
        "QQQ": "Invesco QQQ / Nasdaq-100 ETF",
        "IWM": "iShares Russell 2000 ETF",
    },
}

indicator_groups = st.multiselect(
    "Indicator groups",
    options=list(MARKET_INDICATORS.keys()),
    default=list(MARKET_INDICATORS.keys()),
    key="indicator_groups"
)

indicator_history = st.selectbox(
    "Historical data for market indicators",
    ["1y", "2y", "5y", "10y", "max"],
    index=2,
    key="indicator_history"
)

indicator_tickers = []
indicator_names = {}
for group in indicator_groups:
    for ticker, name in MARKET_INDICATORS[group].items():
        if ticker not in indicator_tickers:
            indicator_tickers.append(ticker)
            indicator_names[ticker] = name

st.caption(
    "Selected indicators: "
    + (", ".join(indicator_tickers) if indicator_tickers else "None")
)

indicator_windows = st.multiselect(
    "Short-term indicator windows",
    options=list(HOLD_WINDOWS.keys()),
    default=[
        "1 trading day",
        "3 trading days",
        "5 trading days / about 1 week",
        "10 trading days / about 2 weeks",
        "15 trading days / about 3 weeks",
    ],
    key="indicator_windows"
)

def download_indicator_history(tickers, period):
    if not tickers:
        return {}

    raw = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=False,
        actions=False,
        group_by="column",
        threads=True,
        progress=False,
        timeout=30,
    )

    results = {}

    for ticker in tickers:
        try:
            one = raw.copy()

            if isinstance(one.columns, pd.MultiIndex):
                ticker_level = None
                for level in range(one.columns.nlevels):
                    if ticker in set(map(str, one.columns.get_level_values(level))):
                        ticker_level = level
                        break

                if ticker_level is not None:
                    one = one.xs(
                        ticker,
                        axis=1,
                        level=ticker_level,
                        drop_level=True
                    )

            if one is None or one.empty:
                continue

            if getattr(one.index, "tz", None) is not None:
                one.index = one.index.tz_localize(None)

            one.index.name = "Date"
            one = one.reset_index()
            one.insert(1, "Ticker", ticker)
            one.insert(
                2,
                "Indicator_Name",
                indicator_names.get(ticker, ticker)
            )

            if "Close" in one.columns:
                one = one[one["Close"].notna()]

            if not one.empty:
                results[ticker] = one

        except Exception:
            pass

    return results

def indicator_short_window_stats(df, ticker, name, selected_windows):
    if df.empty or "Close" not in df.columns:
        return pd.DataFrame()

    values = df[["Date", "Close"]].copy().sort_values("Date")
    rows = []

    for label in selected_windows:
        days = HOLD_WINDOWS[label]
        future = values["Close"].shift(-days)
        changes = (future / values["Close"] - 1.0) * 100.0
        valid = changes.dropna()

        if valid.empty:
            continue

        rows.append({
            "Ticker": ticker,
            "Indicator_Name": name,
            "Holding_Period": label,
            "Trading_Days": days,
            "Observations": int(valid.shape[0]),
            "Average_Change_%": float(valid.mean()),
            "Median_Change_%": float(valid.median()),
            "Best_Change_%": float(valid.max()),
            "Worst_Change_%": float(valid.min()),
            "Positive_Periods_%": float((valid > 0).mean() * 100.0),
        })

    return pd.DataFrame(rows)

def make_indicator_zip(results, stats_df, history_period):
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        combined = []

        for ticker, df in sorted(results.items()):
            z.writestr(
                f"Market_Indicators/{safe_name(ticker)}.csv",
                df.to_csv(index=False)
            )
            combined.append(df)

        if combined:
            z.writestr(
                "ALL_MARKET_INDICATORS.csv",
                pd.concat(combined, ignore_index=True).to_csv(index=False)
            )

        if stats_df is not None and not stats_df.empty:
            z.writestr(
                "MARKET_INDICATOR_SHORT_WINDOW_ANALYSIS.csv",
                stats_df.to_csv(index=False)
            )

        mapping_rows = []
        for group, mapping in MARKET_INDICATORS.items():
            for ticker, name in mapping.items():
                if ticker in indicator_tickers:
                    mapping_rows.append({
                        "Group": group,
                        "Ticker": ticker,
                        "Indicator_Name": name,
                    })

        z.writestr(
            "MARKET_INDICATOR_LIST.csv",
            pd.DataFrame(mapping_rows).to_csv(index=False)
        )

        z.writestr(
            "README.txt",
            (
                "Market Indicator Export\n"
                "=======================\n\n"
                f"Created: {date.today().isoformat()}\n"
                f"Historical lookback: {history_period}\n\n"
                "Includes selected stock indexes, VIX, Treasury-yield indicators, "
                "the U.S. dollar, gold, crude oil, and tradable ETF market proxies.\n\n"
                "Short-window analysis uses trading-day changes from 1 through 15 trading days.\n"
                "For Treasury-yield symbols, percentage-change calculations describe changes "
                "in the quoted yield-index level, not total return from owning a Treasury security.\n"
            )
        )

    buf.seek(0)
    return buf.getvalue()

if st.button(
    "Build market indicator ZIP + analysis",
    type="primary",
    use_container_width=True,
    key="indicator_build"
):
    if not indicator_tickers:
        st.warning("Choose at least one indicator group.")
    else:
        with st.spinner(
            "Downloading market indicators and calculating short-term changes..."
        ):
            indicator_results = download_indicator_history(
                indicator_tickers,
                indicator_history
            )

            stats_frames = []
            for ticker, df in indicator_results.items():
                stats = indicator_short_window_stats(
                    df,
                    ticker,
                    indicator_names.get(ticker, ticker),
                    indicator_windows
                )
                if not stats.empty:
                    stats_frames.append(stats)

            indicator_stats = (
                pd.concat(stats_frames, ignore_index=True)
                if stats_frames else pd.DataFrame()
            )

            st.session_state["indicator_results"] = indicator_results
            st.session_state["indicator_stats"] = indicator_stats
            st.session_state["indicator_history_used"] = indicator_history

if "indicator_results" in st.session_state:
    indicator_results = st.session_state["indicator_results"]
    indicator_stats = st.session_state["indicator_stats"]
    indicator_history_used = st.session_state["indicator_history_used"]

    if not indicator_results:
        st.error("No market-indicator data was returned.")
    else:
        st.success(
            f"Loaded {len(indicator_results)} market indicators."
        )

        if not indicator_stats.empty:
            display_indicator_stats = indicator_stats.copy()

            for col in [
                "Average_Change_%",
                "Median_Change_%",
                "Best_Change_%",
                "Worst_Change_%",
                "Positive_Periods_%"
            ]:
                display_indicator_stats[col] = (
                    display_indicator_stats[col].round(3)
                )

            st.subheader("Short-term market indicator comparison")
            st.dataframe(
                display_indicator_stats.sort_values(
                    ["Trading_Days", "Average_Change_%"],
                    ascending=[True, False]
                ),
                use_container_width=True,
                hide_index=True
            )

        indicator_zip = make_indicator_zip(
            indicator_results,
            indicator_stats,
            indicator_history_used
        )

        stamp = date.today().isoformat()

        st.download_button(
            "🗜️ Download market indicators ZIP",
            data=indicator_zip,
            file_name=(
                f"MARKET_INDICATORS_{stamp}_{indicator_history_used}.zip"
            ),
            mime="application/zip",
            type="primary",
            use_container_width=True,
            key="indicator_download"
        )

st.caption(
    "The market-indicator ZIP is separate from the ETF institution batches "
    "and short-term bond ZIPs, so each dataset stays easy to identify."
)

st.divider()
st.markdown(
    """
### How the institution batches work

Choose an ETF provider such as **BlackRock/iShares, Vanguard, State Street/SPDR,
Invesco, Fidelity, or JPMorgan**. The app counts that institution's ETFs and
automatically tells you how many ZIP batches are needed.

For **10 years of daily data**, start with **200 ETFs per batch**.

A large provider can have multiple files such as:

`BlackRock_iShares_ETF_BATCH_01_OF_03_2026-08-15_10y.zip`

`BlackRock_iShares_ETF_BATCH_02_OF_03_2026-08-15_10y.zip`

A smaller provider may have only:

`Vanguard_ETF_BATCH_01_OF_01_2026-08-15_10y.zip`

Inside each ZIP, ETFs remain organized by **institution and sector/category**.

You can also choose **All Institutions** if you want numbered batches covering
the entire ETF universe.
"""
)
