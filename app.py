import io
import re
import time
import zipfile
from datetime import date

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="ETF Downloader by Institution & Sector", page_icon="🏦", layout="wide")

NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"

st.title("🏦 ETF Downloader — Institution + Sector")
st.write("Download U.S. ETF daily market data as one ZIP, organized by ETF sponsor and sector/category.")

ISSUER_PATTERNS = [
    ("BlackRock_iShares", [r"\\biShares\\b", r"\\bBlackRock\\b"]),
    ("Vanguard", [r"\\bVanguard\\b"]),
    ("State_Street_SPDR", [r"\\bSPDR\\b", r"\\bState Street\\b"]),
    ("Invesco", [r"\\bInvesco\\b", r"\\bPowerShares\\b"]),
    ("Charles_Schwab", [r"\\bSchwab\\b"]),
    ("Fidelity", [r"\\bFidelity\\b"]),
    ("JPMorgan", [r"\\bJPMorgan\\b", r"\\bJ\\.P\\. Morgan\\b", r"\\bJPM\\b"]),
    ("Goldman_Sachs", [r"\\bGoldman Sachs\\b"]),
    ("Franklin_Templeton", [r"\\bFranklin\\b", r"\\bTempleton\\b"]),
    ("PIMCO", [r"\\bPIMCO\\b"]),
    ("First_Trust", [r"\\bFirst Trust\\b"]),
    ("ProShares", [r"\\bProShares\\b"]),
    ("Direxion", [r"\\bDirexion\\b"]),
    ("Global_X", [r"\\bGlobal X\\b"]),
    ("VanEck", [r"\\bVanEck\\b"]),
    ("WisdomTree", [r"\\bWisdomTree\\b"]),
    ("ARK_Invest", [r"\\bARK\\b"]),
    ("Innovator", [r"\\bInnovator\\b"]),
    ("Amplify", [r"\\bAmplify\\b"]),
    ("Simplify", [r"\\bSimplify\\b"]),
    ("Roundhill", [r"\\bRoundhill\\b"]),
    ("Defiance", [r"\\bDefiance\\b"]),
    ("Janus_Henderson", [r"\\bJanus Henderson\\b"]),
    ("PGIM", [r"\\bPGIM\\b"]),
    ("YieldMax", [r"\\bYieldMax\\b"]),
]

SECTOR_PATTERNS = [
    ("Technology", [r"technology", r"\\btech\\b", r"semiconductor", r"software", r"cyber", r"cloud", r"artificial intelligence", r"robot"]),
    ("Financials", [r"financial", r"bank", r"insurance", r"capital markets", r"fintech"]),
    ("Energy", [r"\\benergy\\b", r"\\boil\\b", r"\\bgas\\b", r"midstream", r"pipeline", r"uranium"]),
    ("Healthcare", [r"health", r"biotech", r"pharma", r"medical", r"genomic"]),
    ("Industrials", [r"industrial", r"aerospace", r"defense", r"transport", r"construction", r"infrastructure", r"machinery"]),
    ("Consumer_Discretionary", [r"consumer discretionary", r"retail", r"e-commerce", r"travel", r"leisure", r"automotive"]),
    ("Consumer_Staples", [r"consumer staples", r"food", r"beverage"]),
    ("Utilities", [r"utilities", r"utility"]),
    ("Materials", [r"materials", r"metals", r"mining", r"steel", r"copper", r"lithium", r"chemicals", r"timber"]),
    ("Real_Estate", [r"real estate", r"\\bREIT"]),
    ("Communication_Services", [r"communication services", r"telecom", r"media", r"internet", r"social media"]),
    ("Fixed_Income", [r"bond", r"treasury", r"municipal", r"muni", r"credit", r"fixed income", r"debt", r"high yield", r"corporate", r"floating rate"]),
    ("Commodities", [r"gold", r"silver", r"commodity", r"commodities", r"precious metals", r"natural gas", r"crude oil"]),
    ("International", [r"international", r"emerging market", r"developed market", r"Europe", r"Asia", r"Japan", r"China", r"India", r"Brazil", r"Latin America"]),
    ("Broad_Market", [r"S&P 500", r"total stock", r"total market", r"Russell 1000", r"Russell 2000", r"Russell 3000", r"large[- ]cap", r"mid[- ]cap", r"small[- ]cap", r"dividend", r"\\bvalue\\b", r"\\bgrowth\\b", r"quality", r"momentum"]),
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
def universe():
    n = read_pipe(NASDAQ_LISTED)
    o = read_pipe(OTHER_LISTED)

    n = n[(n["ETF"] == "Y") & (n["Test Issue"] == "N")].copy()
    n = n.rename(columns={"Symbol":"Ticker", "Security Name":"Fund_Name"})
    n["Exchange"] = "Nasdaq"

    o = o[(o["ETF"] == "Y") & (o["Test Issue"] == "N")].copy()
    o = o.rename(columns={"ACT Symbol":"Ticker", "Security Name":"Fund_Name"})

    u = pd.concat([n[["Ticker","Fund_Name","Exchange"]], o[["Ticker","Fund_Name","Exchange"]]], ignore_index=True)
    u["YahooTicker"] = u["Ticker"].astype(str).str.replace(".", "-", regex=False)
    u["Issuer_Group"] = u["Fund_Name"].map(lambda x: classify(x, ISSUER_PATTERNS, "Other_or_Unknown"))
    u["Sector_Category"] = u["Fund_Name"].map(lambda x: classify(x, SECTOR_PATTERNS, "Unclassified"))
    u["Classification_Method"] = "Name-based"
    return u.drop_duplicates("YahooTicker").sort_values(["Issuer_Group","Sector_Category","YahooTicker"]).reset_index(drop=True)

def normalize(df, ticker, issuer, sector, fund_name):
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
    out.insert(2, "Issuer_Group", issuer)
    out.insert(3, "Sector_Category", sector)
    out.insert(4, "Fund_Name", fund_name)
    if "Close" in out.columns:
        out = out[out["Close"].notna()]
    return out

def download_selected(selected, period, batch_size=75):
    results, failed = {}, []
    batches = [selected.iloc[i:i+batch_size] for i in range(0, len(selected), batch_size)]
    progress = st.progress(0)
    status = st.empty()

    for idx, batch in enumerate(batches, 1):
        status.write(f"Downloading batch {idx} of {len(batches)}...")
        tickers = batch["YahooTicker"].tolist()
        try:
            raw = yf.download(tickers=tickers, period=period, interval="1d", auto_adjust=False,
                              actions=False, group_by="column", threads=True, progress=False, timeout=30)
        except Exception:
            raw = pd.DataFrame()

        for _, row in batch.iterrows():
            ticker = row["YahooTicker"]
            try:
                one = normalize(raw, ticker, row["Issuer_Group"], row["Sector_Category"], row["Fund_Name"])
                if one.empty:
                    retry = yf.download(ticker, period=period, interval="1d", auto_adjust=False,
                                        actions=False, progress=False, timeout=20)
                    one = normalize(retry, ticker, row["Issuer_Group"], row["Sector_Category"], row["Fund_Name"])
                if one.empty:
                    failed.append(ticker)
                else:
                    results[ticker] = one
            except Exception:
                failed.append(ticker)

        progress.progress(idx / len(batches))
        if idx < len(batches):
            time.sleep(0.2)

    progress.empty()
    status.empty()
    return results, sorted(set(failed))

def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(s)).strip("_") or "Unknown"

def make_zip(results, selected, failed, period):
    buf = io.BytesIO()
    by_issuer, by_sector, by_pair, all_frames = {}, {}, {}, []

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for ticker, df in sorted(results.items()):
            issuer = safe_name(df["Issuer_Group"].iloc[0])
            sector = safe_name(df["Sector_Category"].iloc[0])

            z.writestr(f"By_Institution/{issuer}/{sector}/{ticker}.csv", df.to_csv(index=False))
            all_frames.append(df)
            by_issuer.setdefault(issuer, []).append(df)
            by_sector.setdefault(sector, []).append(df)
            by_pair.setdefault((issuer, sector), []).append(df)

        if all_frames:
            z.writestr("ALL_ETFS.csv", pd.concat(all_frames, ignore_index=True).to_csv(index=False))

        for issuer, frames in by_issuer.items():
            z.writestr(f"By_Institution/{issuer}/ALL_{issuer}_ETFS.csv",
                       pd.concat(frames, ignore_index=True).to_csv(index=False))

        for (issuer, sector), frames in by_pair.items():
            z.writestr(f"By_Institution/{issuer}/{sector}/ALL_{issuer}_{sector}_ETFS.csv",
                       pd.concat(frames, ignore_index=True).to_csv(index=False))

        for sector, frames in by_sector.items():
            z.writestr(f"By_Sector/{sector}/ALL_{sector}_ETFS.csv",
                       pd.concat(frames, ignore_index=True).to_csv(index=False))

        z.writestr("ETF_UNIVERSE_WITH_ISSUER_AND_SECTOR.csv", selected.to_csv(index=False))

        summary = (selected.groupby(["Issuer_Group","Sector_Category"], dropna=False)
                   .agg(ETF_Count=("YahooTicker","nunique")).reset_index())
        z.writestr("ISSUER_SECTOR_SUMMARY.csv", summary.to_csv(index=False))

        sector_summary = (selected.groupby("Sector_Category", dropna=False)
                          .agg(ETF_Count=("YahooTicker","nunique")).reset_index()
                          .sort_values("ETF_Count", ascending=False))
        z.writestr("SECTOR_SUMMARY.csv", sector_summary.to_csv(index=False))

        if failed:
            z.writestr("FAILED_TICKERS.txt", "\n".join(failed))

        z.writestr("README.txt",
                   "ETF Downloader by Institution and Sector\n"
                   "=======================================\n\n"
                   f"Created: {date.today().isoformat()}\n"
                   f"Daily history period: {period}\n\n"
                   "Primary layout: By_Institution/<Institution>/<Sector>/<ETF>.csv\n"
                   "Broad-market, bond, commodity, international, and thematic ETFs use categories instead of being forced into an equity sector.\n"
                   "Issuer and sector/category classification is based on the published security name; uncertain funds remain unclassified.\n")
    buf.seek(0)
    return buf.getvalue()

try:
    u = universe()
except Exception as e:
    st.error(f"Could not load the ETF universe: {e}")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("ETF symbols", f"{len(u):,}")
c2.metric("Institution groups", f"{u['Issuer_Group'].nunique():,}")
c3.metric("Sector/categories", f"{u['Sector_Category'].nunique():,}")

with st.expander("Preview classifications"):
    st.dataframe(u[["YahooTicker","Fund_Name","Issuer_Group","Sector_Category","Exchange"]],
                 use_container_width=True, hide_index=True)

mode = st.radio("Download selection", [
    "All U.S. ETFs",
    "Choose institutions",
    "Choose sectors/categories",
    "Choose institution + sector",
    "Custom ETF tickers"
])

selected = u.copy()

if mode == "Choose institutions":
    choices = st.multiselect("Institutions", sorted(u["Issuer_Group"].unique()))
    selected = u[u["Issuer_Group"].isin(choices)].copy()

elif mode == "Choose sectors/categories":
    choices = st.multiselect("Sectors/categories", sorted(u["Sector_Category"].unique()))
    selected = u[u["Sector_Category"].isin(choices)].copy()

elif mode == "Choose institution + sector":
    institutions = st.multiselect("Institutions", sorted(u["Issuer_Group"].unique()))
    sectors = st.multiselect("Sectors/categories", sorted(u["Sector_Category"].unique()))
    if institutions:
        selected = selected[selected["Issuer_Group"].isin(institutions)]
    if sectors:
        selected = selected[selected["Sector_Category"].isin(sectors)]

elif mode == "Custom ETF tickers":
    typed = st.text_area("ETF tickers", value="SPY, QQQ, VOO, VTI, XLK, XLF, XLE")
    tickers = list(dict.fromkeys([
        t.strip().upper()
        for t in typed.replace(",", " ").replace("\n", " ").split()
        if t.strip()
    ]))
    selected = u[u["YahooTicker"].isin(tickers)].copy()

period = st.selectbox("Daily history", ["5d","1mo","3mo","6mo","1y","2y","5y","10y","max"], index=1)

st.info(f"Selected {len(selected):,} ETFs across "
        f"{selected['Issuer_Group'].nunique() if len(selected) else 0} institutions and "
        f"{selected['Sector_Category'].nunique() if len(selected) else 0} sectors/categories.")

if st.button("Build ZIP organized by institution and sector", type="primary", use_container_width=True):
    if selected.empty:
        st.warning("Select at least one ETF, institution, or sector.")
    else:
        results, failed = download_selected(selected, period)
        if results:
            st.session_state["results"] = results
            st.session_state["failed"] = failed
            st.session_state["selected"] = selected
            st.session_state["period"] = period
        else:
            st.error("No ETF market data was returned.")

if "results" in st.session_state:
    results = st.session_state["results"]
    failed = st.session_state["failed"]
    selected = st.session_state["selected"]
    period = st.session_state["period"]

    st.success(f"Finished: {len(results):,} ETFs downloaded" +
               (f"; {len(failed):,} failed." if failed else "."))

    bundle = make_zip(results, selected, failed, period)
    stamp = date.today().isoformat()

    st.download_button(
        "🗜️ Download ONE ZIP — institution + sector",
        data=bundle,
        file_name=f"US_ETFS_BY_INSTITUTION_AND_SECTOR_{stamp}_{period}.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True,
    )

st.caption("Market history comes from Yahoo Finance through yfinance. Institution and sector/category labels are name-based and included in the export for review.")
