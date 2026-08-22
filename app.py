import io
import ftplib
import math
import re
import time
import zipfile
from datetime import date

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from dateutil.relativedelta import relativedelta

st.set_page_config(
    page_title="ETF + Mutual Fund Downloader",
    page_icon="📦",
    layout="wide",
)

NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
NASDAQ_FTP_HOST = "ftp.nasdaqtrader.com"
NASDAQ_FTP_MUTUAL_FUNDS_PATH = "/symboldirectory/mfundslist.txt"

st.title("📦 ETF + Mutual Fund Downloader")
st.write(
    "Download ETFs and mutual funds with the same batch, institution, date-range, "
    "year-block, CSV, and ZIP workflow."
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
    ("T_Rowe_Price", [r"\bT\.?\s*Rowe Price\b"]),
    ("Franklin_Templeton", [r"\bFranklin\b", r"\bTempleton\b"]),
    ("PIMCO", [r"\bPIMCO\b"]),
    ("Dimensional", [r"\bDimensional\b"]),
    ("American_Funds_Capital_Group", [r"\bAmerican Funds\b", r"\bCapital Group\b"]),
    ("Dodge_and_Cox", [r"\bDodge\s*&?\s*Cox\b"]),
    ("Putnam", [r"\bPutnam\b"]),
    ("MFS", [r"\bMFS\b", r"\bMassachusetts Financial\b"]),
    ("Janus_Henderson", [r"\bJanus Henderson\b", r"\bJanus\b"]),
    ("PGIM", [r"\bPGIM\b"]),
    ("Nuveen", [r"\bNuveen\b"]),
    ("Principal", [r"\bPrincipal\b"]),
    ("Victory_Capital", [r"\bVictory\b"]),
    ("Virtus", [r"\bVirtus\b"]),
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
    ("YieldMax", [r"\bYieldMax\b"]),
]

SECTOR_PATTERNS = [
    ("Technology", [r"technology", r"\btech\b", r"semiconductor", r"software", r"cyber", r"cloud", r"artificial intelligence", r"\bAI\b", r"robot", r"quantum"]),
    ("Financials", [r"financial", r"\bbank", r"insurance", r"capital markets", r"fintech", r"broker"]),
    ("Energy", [r"\benergy\b", r"\boil\b", r"\bgas\b", r"midstream", r"pipeline", r"uranium", r"exploration", r"MLP"]),
    ("Healthcare", [r"health", r"biotech", r"pharma", r"medical", r"genomic", r"life science"]),
    ("Industrials", [r"industrial", r"aerospace", r"defense", r"transport", r"construction", r"infrastructure", r"machinery"]),
    ("Consumer_Discretionary", [r"consumer discretionary", r"retail", r"e-commerce", r"travel", r"leisure", r"automotive", r"restaurant"]),
    ("Consumer_Staples", [r"consumer staples", r"food", r"beverage", r"grocery", r"agriculture"]),
    ("Utilities", [r"utilities", r"\butility\b", r"electric power"]),
    ("Materials", [r"materials", r"metals", r"mining", r"steel", r"copper", r"lithium", r"chemicals", r"timber", r"rare earth"]),
    ("Real_Estate", [r"real estate", r"\bREIT", r"property"]),
    ("Communication_Services", [r"communication services", r"telecom", r"media", r"internet", r"social media", r"streaming"]),
    ("Treasury_Government_Bonds", [r"treasury", r"government bond", r"government securities", r"\bTIPS\b", r"inflation.protected"]),
    ("Municipal_Bonds", [r"municipal", r"\bmuni\b", r"tax.exempt bond"]),
    ("Corporate_Bonds", [r"corporate bond", r"investment grade", r"credit opportunities"]),
    ("High_Yield_Bonds", [r"high yield", r"junk bond"]),
    ("Short_Term_Bonds", [r"ultra.?short", r"short.?term bond", r"short duration", r"1.?3 year", r"0.?3 month"]),
    ("Intermediate_Bonds", [r"intermediate.?term", r"intermediate bond", r"3.?10 year"]),
    ("Long_Term_Bonds", [r"long.?term bond", r"long duration", r"10.?year", r"20.?year", r"30.?year"]),
    ("Floating_Rate_Bank_Loans", [r"floating rate", r"bank loan", r"senior loan"]),
    ("Mortgage_Asset_Backed", [r"mortgage", r"mortgage.backed", r"asset.backed", r"\bMBS\b"]),
    ("International_Bonds", [r"international bond", r"global bond", r"emerging market bond", r"foreign bond"]),
    ("Fixed_Income_General", [r"\bbond\b", r"fixed income", r"\bdebt\b", r"\bcredit\b"]),
    ("Money_Market_Cash", [r"money market", r"government money", r"cash reserves", r"liquidity fund", r"treasury money"]),
    ("Emerging_Markets", [r"emerging market", r"frontier market"]),
    ("International_Developed", [r"developed market", r"international", r"foreign", r"Europe", r"Asia", r"Japan", r"China", r"India", r"Brazil", r"Latin America", r"Pacific", r"EAFE"]),
    ("US_Large_Cap", [r"large[- ]cap", r"S&P 500", r"Russell 1000"]),
    ("US_Mid_Cap", [r"mid[- ]cap", r"S&P MidCap", r"Russell Midcap"]),
    ("US_Small_Cap", [r"small[- ]cap", r"Russell 2000", r"micro[- ]cap"]),
    ("Total_Broad_Market", [r"total stock", r"total market", r"Russell 3000", r"broad market", r"composite index"]),
    ("Growth", [r"\bgrowth\b"]),
    ("Value", [r"\bvalue\b"]),
    ("Dividend_Income", [r"dividend", r"equity income", r"income fund"]),
    ("Quality_Factor", [r"\bquality\b"]),
    ("Momentum_Factor", [r"\bmomentum\b"]),
    ("Low_Volatility_Defensive", [r"low volatility", r"minimum volatility", r"defensive"]),
    ("Balanced_Allocation", [r"balanced", r"allocation", r"target risk", r"multi.?asset", r"asset allocation"]),
    ("Target_Date_Retirement", [r"target date", r"target retirement", r"retirement \d{4}", r"lifecycle"]),
    ("Commodities", [r"commodity", r"commodities", r"gold", r"silver", r"precious metals", r"natural gas", r"crude oil"]),
    ("Currency_Crypto", [r"currency", r"bitcoin", r"ethereum", r"crypto", r"blockchain"]),
    ("Options_Derivatives", [r"covered call", r"option income", r"buffer", r"defined outcome", r"derivative"]),
    ("Leveraged_Inverse", [r"leveraged", r"\b2x\b", r"\b3x\b", r"ultra", r"inverse", r"\bshort\b", r"\bbear\b"]),
    ("Thematic", [r"clean energy", r"solar", r"wind", r"water", r"space", r"cannabis", r"metaverse", r"gaming", r"innovation", r"disruptive"]),
]

def classify(text, patterns, default):
    text = str(text or "")
    for label, pats in patterns:
        if any(re.search(p, text, flags=re.IGNORECASE) for p in pats):
            return label
    return default

def classify_fund_category(name, fund_type="ETF", nasdaq_category=""):
    name = str(name or "")
    cat = str(nasdaq_category or "").upper().strip()
    if cat == "D":
        return "Fixed_Income_General"
    result = classify(name, SECTOR_PATTERNS, "")
    if result:
        return result
    if str(fund_type).lower().startswith("mutual"):
        return "Diversified_Other_Mutual_Fund"
    return "Diversified_Other_ETF"

def safe_name(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("_") or "Unknown"

@st.cache_data(ttl=3600)
def read_pipe(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), sep="|")
    first = df.columns[0]
    return df[~df[first].astype(str).str.startswith("File Creation Time", na=False)]

@st.cache_data(ttl=3600)
def get_etf_universe():
    n = read_pipe(NASDAQ_LISTED)
    o = read_pipe(OTHER_LISTED)

    n = n[(n["ETF"] == "Y") & (n["Test Issue"] == "N")].copy()
    n = n.rename(columns={"Symbol": "Ticker", "Security Name": "Fund_Name"})
    n["Exchange"] = "Nasdaq"

    o = o[(o["ETF"] == "Y") & (o["Test Issue"] == "N")].copy()
    o = o.rename(columns={"ACT Symbol": "Ticker", "Security Name": "Fund_Name"})

    u = pd.concat(
        [n[["Ticker", "Fund_Name", "Exchange"]], o[["Ticker", "Fund_Name", "Exchange"]]],
        ignore_index=True,
    )
    u["YahooTicker"] = u["Ticker"].astype(str).str.replace(".", "-", regex=False)
    u["Fund_Type"] = "ETF"
    u["Issuer_Group"] = u["Fund_Name"].map(lambda x: classify(x, ISSUER_PATTERNS, "Other_or_Unknown"))
    u["Sector_Category"] = u["Fund_Name"].map(lambda x: classify_fund_category(x, "ETF"))
    return u.drop_duplicates("YahooTicker").sort_values(["Issuer_Group", "YahooTicker"]).reset_index(drop=True)

def fetch_nasdaq_mutual_fund_text():
    """
    Nasdaq's current symbol-directory page documents mfundslist.txt as an FTP file.
    Fetch it directly from the Nasdaq Trader FTP server instead of the old HTTP URL.
    """
    buffer = io.BytesIO()

    ftp = ftplib.FTP(NASDAQ_FTP_HOST, timeout=30)
    try:
        ftp.login()
        ftp.retrbinary(
            f"RETR {NASDAQ_FTP_MUTUAL_FUNDS_PATH}",
            buffer.write,
        )
    finally:
        try:
            ftp.quit()
        except Exception:
            pass

    raw = buffer.getvalue()

    # Nasdaq's symbol-directory files are ASCII/Windows text. utf-8-sig handles
    # a BOM if one is present; latin-1 fallback avoids parser crashes on odd bytes.
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def parse_mutual_fund_directory(raw_text):
    """
    Parse the pipe-delimited mfundslist.txt defensively.
    Expected fields:
    Fund Symbol | Fund Name | Fund Family Name | Type | Category | Pricing Agent

    We intentionally parse line-by-line instead of using pandas.read_csv so an
    odd footer or malformed line cannot break the whole mutual-fund tab.
    """
    records = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("File Creation Time"):
            continue

        parts = [p.strip() for p in line.split("|")]

        # Header line.
        if parts and parts[0].lower() == "fund symbol":
            continue

        # We need at least symbol, name and family.
        if len(parts) < 3:
            continue

        # If a line contains extra delimiters, preserve the first six documented
        # fields and ignore anything after them.
        parts = parts[:6] + [""] * max(0, 6 - len(parts))

        symbol, fund_name, family, fund_type, category, pricing_agent = parts[:6]

        symbol = symbol.strip().upper()
        fund_name = fund_name.strip()
        family = family.strip()
        fund_type = fund_type.strip().upper()
        category = category.strip().upper()

        if not symbol or not fund_name:
            continue

        # Keep actual mutual funds / supplemental mutual funds. Money-market
        # funds can be added later as a separate product if desired.
        if fund_type not in {"MF", "MS"}:
            continue

        records.append(
            {
                "Ticker": symbol,
                "Fund_Name": fund_name,
                "Fund_Family_Name": family or "Other_or_Unknown",
                "Nasdaq_Fund_Type": fund_type,
                "Nasdaq_Category": category,
                "Pricing_Agent": pricing_agent,
            }
        )

    if not records:
        raise ValueError(
            "Nasdaq mutual-fund directory was reached, but no mutual-fund records could be parsed."
        )

    return pd.DataFrame(records)


@st.cache_data(ttl=3600)
def get_mutual_fund_universe():
    raw_text = fetch_nasdaq_mutual_fund_text()
    u = parse_mutual_fund_directory(raw_text)

    u["YahooTicker"] = (
        u["Ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(".", "-", regex=False)
    )
    u["Exchange"] = "Mutual Fund"
    u["Fund_Type"] = "Mutual Fund"

    # Nasdaq supplies the actual Fund Family Name, so use it directly rather than
    # guessing the institution from the fund name.
    u["Issuer_Group"] = (
        u["Fund_Family_Name"]
        .fillna("Other_or_Unknown")
        .astype(str)
        .str.strip()
        .replace("", "Other_or_Unknown")
    )

    # Use Nasdaq's fixed-income category where available, then fall back to our
    # name-based categories for the rest.
    u["Sector_Category"] = u.apply(
        lambda row: classify_fund_category(
            row["Fund_Name"], "Mutual Fund", row.get("Nasdaq_Category", "")
        ),
        axis=1,
    )

    return (
        u.drop_duplicates("YahooTicker")
        .sort_values(["Issuer_Group", "YahooTicker"])
        .reset_index(drop=True)
    )

def time_selector(prefix, fund_type):
    if fund_type == "ETF":
        interval_choice = st.selectbox(
            "Data interval",
            ["Daily (1d)", "Hourly (1h)", "30 minute (30m)", "15 minute (15m)"],
            index=0,
            key=f"{prefix}_interval",
        )
        interval_map = {
            "Daily (1d)": "1d",
            "Hourly (1h)": "1h",
            "30 minute (30m)": "30m",
            "15 minute (15m)": "15m",
        }
        interval = interval_map[interval_choice]
    else:
        interval_choice = "Daily (1d)"
        interval = "1d"
        st.info(
            "Mutual funds are generally priced once per trading day, so the mutual-fund "
            "downloader uses Daily (1d) data."
        )

    date_mode = st.radio(
        "Date selection",
        ["Recent period", "Year block", "Custom date range"],
        horizontal=True,
        key=f"{prefix}_date_mode",
    )

    if date_mode == "Recent period":
        options = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]
        period = st.selectbox("History to include", options, index=6, key=f"{prefix}_period")
        return interval_choice, interval, {"period": period}, period

    if date_mode == "Year block":
        block_years = st.selectbox(
            "Years per block",
            [1, 2, 3, 5, 10],
            index=4,
            key=f"{prefix}_block_years",
        )
        block_number = st.number_input(
            "Historical block",
            min_value=1,
            max_value=30,
            value=1,
            step=1,
            key=f"{prefix}_block_number",
        )
        today = date.today()
        end_date = today - relativedelta(years=block_years * (int(block_number) - 1))
        start_date = end_date - relativedelta(years=block_years)
        st.info(
            f"Block {int(block_number)}: {start_date.isoformat()} through {end_date.isoformat()}"
        )
        return (
            interval_choice,
            interval,
            {"start": str(start_date), "end": str(end_date)},
            f"{start_date}_to_{end_date}",
        )

    today = date.today()
    start_date = st.date_input(
        "Start date",
        value=today - relativedelta(years=2),
        key=f"{prefix}_start",
    )
    end_date = st.date_input("End date", value=today, key=f"{prefix}_end")
    return (
        interval_choice,
        interval,
        {"start": str(start_date), "end": str(end_date)},
        f"{start_date}_to_{end_date}",
    )

def normalize_download(raw, ticker, row):
    if raw is None or raw.empty:
        return pd.DataFrame()

    out = raw.copy()
    if isinstance(out.columns, pd.MultiIndex):
        ticker_level = None
        for level in range(out.columns.nlevels):
            if ticker in set(map(str, out.columns.get_level_values(level))):
                ticker_level = level
                break
        if ticker_level is not None:
            out = out.xs(ticker, axis=1, level=ticker_level, drop_level=True)

    if out is None or out.empty:
        return pd.DataFrame()

    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_localize(None)

    out.index.name = "Date"
    out = out.reset_index()
    out.insert(1, "Ticker", ticker)
    out.insert(2, "Fund_Type", row["Fund_Type"])
    out.insert(3, "Issuer_Group", row["Issuer_Group"])
    out.insert(4, "Sector_Category", row["Sector_Category"])
    out.insert(5, "Fund_Name", row["Fund_Name"])

    if "Close" in out.columns:
        out = out[out["Close"].notna()]

    return out

def download_batch(batch_df, interval, time_kwargs, internal_size=20):
    results = {}
    failed = []
    tickers = batch_df["YahooTicker"].tolist()
    meta = batch_df.set_index("YahooTicker")

    internal_groups = [
        tickers[i:i + internal_size]
        for i in range(0, len(tickers), internal_size)
    ]

    for gi, group in enumerate(internal_groups, 1):
        try:
            raw = yf.download(
                tickers=group,
                interval=interval,
                auto_adjust=False,
                actions=False,
                group_by="column",
                threads=True,
                progress=False,
                timeout=30,
                **time_kwargs,
            )
        except Exception:
            raw = pd.DataFrame()

        for ticker in group:
            row = meta.loc[ticker]
            one = pd.DataFrame()
            try:
                one = normalize_download(raw, ticker, row)
            except Exception:
                pass

            if one.empty:
                try:
                    retry = yf.download(
                        ticker,
                        interval=interval,
                        auto_adjust=False,
                        actions=False,
                        progress=False,
                        timeout=20,
                        **time_kwargs,
                    )
                    one = normalize_download(retry, ticker, row)
                except Exception:
                    one = pd.DataFrame()

            if one.empty:
                failed.append(ticker)
            else:
                results[ticker] = one

        if gi < len(internal_groups):
            time.sleep(0.4)

    return results, sorted(set(failed))

def build_zip(results, batch_df, failed, product_label, institution, batch_number, total_batches, range_label, interval_label):
    buf = io.BytesIO()
    combined = []
    by_sector = {}

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for ticker, df in sorted(results.items()):
            sector = safe_name(df["Sector_Category"].iloc[0])
            z.writestr(
                f"By_Sector/{sector}/{ticker}.csv",
                df.to_csv(index=False),
            )
            combined.append(df)
            by_sector.setdefault(sector, []).append(df)

        if combined:
            all_data = pd.concat(combined, ignore_index=True)
            z.writestr("BATCH_ALL_FUNDS.csv", all_data.to_csv(index=False))

        for sector, frames in by_sector.items():
            z.writestr(
                f"By_Sector/{sector}/ALL_{sector}_FUNDS_IN_BATCH.csv",
                pd.concat(frames, ignore_index=True).to_csv(index=False),
            )

        z.writestr("BATCH_FUND_LIST.csv", batch_df.to_csv(index=False))

        if failed:
            z.writestr("FAILED_TICKERS.txt", "\n".join(failed))

        z.writestr(
            "README.txt",
            (
                f"{product_label} Download\n"
                f"{'=' * (len(product_label) + 9)}\n\n"
                f"Institution: {institution}\n"
                f"Batch: {batch_number} of {total_batches}\n"
                f"Date range/period: {range_label}\n"
                f"Interval: {interval_label}\n"
                f"Successful downloads: {len(results)}\n"
                f"Failed downloads: {len(failed)}\n"
            ),
        )

    buf.seek(0)
    return buf.getvalue()

tab_etf, tab_mf = st.tabs(["📈 ETFs", "🏛️ Mutual Funds"])

def render_downloader(product_name, universe_df, prefix):
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{product_name} symbols", f"{len(universe_df):,}")
    c2.metric("Institution groups", f"{universe_df['Issuer_Group'].nunique():,}")
    c3.metric("Sector/categories", f"{universe_df['Sector_Category'].nunique():,}")

    st.subheader("1. Choose institution and dates")

    institutions = ["All Institutions"] + sorted(universe_df["Issuer_Group"].unique())
    institution = st.selectbox(
        "Financial institution / fund family",
        institutions,
        key=f"{prefix}_institution",
    )

    if institution == "All Institutions":
        selected_universe = universe_df.copy()
        institution_label = "ALL_INSTITUTIONS"
    else:
        selected_universe = universe_df[universe_df["Issuer_Group"] == institution].copy()
        institution_label = safe_name(institution)

    interval_choice, interval, time_kwargs, range_label = time_selector(
        prefix,
        product_name,
    )

    if product_name == "ETF":
        default_batch = 100
        batch_options = [50, 100, 150, 200, 250]
    else:
        default_batch = 50
        batch_options = [25, 50, 75, 100, 150]

    batch_size = st.select_slider(
        "Funds per ZIP batch",
        options=batch_options,
        value=default_batch,
        key=f"{prefix}_batch_size",
    )

    total_batches = max(1, math.ceil(len(selected_universe) / batch_size))

    st.info(
        f"{institution}: {len(selected_universe):,} {product_name.lower()} symbol(s). "
        f"At {batch_size} per ZIP, this requires {total_batches} batch(es)."
    )

    st.subheader("2. Choose the batch")

    batch_number = st.number_input(
        "Batch number",
        min_value=1,
        max_value=total_batches,
        value=1,
        step=1,
        key=f"{prefix}_batch_number",
    )

    start = (int(batch_number) - 1) * batch_size
    end = min(start + batch_size, len(selected_universe))
    batch_df = selected_universe.iloc[start:end].copy()

    st.write(
        f"{institution} — Batch {int(batch_number)} of {total_batches}: "
        f"{len(batch_df):,} {product_name.lower()}(s)."
    )

    with st.expander("Preview this batch"):
        st.dataframe(
            batch_df[
                ["YahooTicker", "Fund_Name", "Issuer_Group", "Sector_Category"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("3. Build the ZIP")

    if st.button(
        f"Build {product_name} institution batch ZIP",
        type="primary",
        use_container_width=True,
        key=f"{prefix}_build",
    ):
        if batch_df.empty:
            st.warning("This batch has no symbols.")
        else:
            progress = st.progress(0)
            status = st.empty()

            request_chunks = [
                batch_df.iloc[i:i + 20]
                for i in range(0, len(batch_df), 20)
            ]

            all_results = {}
            all_failed = []

            for i, chunk in enumerate(request_chunks, 1):
                status.write(
                    f"Downloading {institution} — chunk {i} of {len(request_chunks)}..."
                )
                got, failed = download_batch(
                    chunk,
                    interval,
                    time_kwargs,
                    internal_size=20,
                )
                all_results.update(got)
                all_failed.extend(failed)
                progress.progress(i / len(request_chunks))

            progress.empty()
            status.empty()

            if not all_results:
                st.error(
                    f"No {product_name.lower()} data was downloaded for this institution batch."
                )
            else:
                bundle = build_zip(
                    all_results,
                    batch_df,
                    sorted(set(all_failed)),
                    product_name,
                    institution,
                    int(batch_number),
                    total_batches,
                    range_label,
                    interval_choice,
                )

                st.success(
                    f"{institution} — Batch {int(batch_number)} is ready: "
                    f"{len(all_results)} successful {product_name.lower()} downloads."
                )

                stamp = date.today().isoformat()
                file_name = (
                    f"{institution_label}_{safe_name(product_name)}_BATCH_"
                    f"{int(batch_number):02d}_OF_{total_batches:02d}_"
                    f"{stamp}_{safe_name(range_label)}_{safe_name(interval_choice)}.zip"
                )

                st.download_button(
                    f"🗜️ Download {institution} — Batch {int(batch_number)} of {total_batches}",
                    data=bundle,
                    file_name=file_name,
                    mime="application/zip",
                    type="primary",
                    use_container_width=True,
                    key=f"{prefix}_download",
                )

with tab_etf:
    try:
        etf_universe = get_etf_universe()
        render_downloader("ETF", etf_universe, "etf")
    except Exception as e:
        st.error(f"Could not load ETF universe: {e}")

with tab_mf:
    try:
        mf_universe = get_mutual_fund_universe()
        render_downloader("Mutual Fund", mf_universe, "mf")
    except Exception as e:
        st.error(f"Could not load mutual-fund universe: {e}")
        st.info(
            "The mutual-fund list is loaded from Nasdaq Trader's official symbol-directory FTP file. "
            "If this appears again, the FTP service may be temporarily unavailable."
        )

st.divider()
st.markdown(
    """
### How the two downloaders work together

The ETF and Mutual Fund tabs use the same basic workflow:

**Institution → interval/date selection → year blocks/custom dates → batch number → ZIP download.**

ETFs can use Daily or intraday intervals where Yahoo Finance provides them.

Mutual funds normally publish one NAV per trading day, so the Mutual Fund tab uses Daily data.

Both export clear filenames, sector/category folders, a combined batch CSV, a batch symbol list,
and a failed-ticker list when needed.
"""
)
