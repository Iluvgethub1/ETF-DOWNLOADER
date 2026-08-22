from __future__ import annotations

import io
import math
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="Batched Mutual Fund Downloader",
    page_icon="📥",
    layout="wide",
)

DB_FILENAME = "mutual_funds.csv"
MAX_WORKERS = 6


def clean_text(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def normalize_database(df: pd.DataFrame) -> pd.DataFrame:
    """Accept common database column names and normalize them."""
    if df is None or df.empty:
        raise ValueError("The mutual-fund database is empty.")

    cols = {str(c).strip().lower(): c for c in df.columns}

    def find_col(names):
        for n in names:
            if n in cols:
                return cols[n]
        return None

    symbol_col = find_col(["symbol", "ticker", "fund_symbol", "fund ticker", "fund_ticker"])
    name_col = find_col(["fund_name", "name", "security_name", "fund name", "description"])
    institution_col = find_col([
        "institution", "fund_family", "family", "sponsor",
        "fund company", "fund_company", "issuer"
    ])
    category_col = find_col(["category", "fund_category", "asset_class", "type"])

    if symbol_col is None:
        raise ValueError(
            "The database needs a Symbol or Ticker column. "
            "Example columns: symbol, fund_name, institution, category."
        )

    out = pd.DataFrame()
    out["symbol"] = df[symbol_col].map(clean_text).str.upper()
    out["fund_name"] = df[name_col].map(clean_text) if name_col else ""
    out["institution"] = (
        df[institution_col].map(clean_text) if institution_col else "Unassigned"
    )
    out["category"] = df[category_col].map(clean_text) if category_col else ""

    out["institution"] = out["institution"].replace("", "Unassigned")
    out = out[out["symbol"].str.match(r"^[A-Z0-9.\-]+$", na=False)]
    out = out.drop_duplicates(subset=["symbol"], keep="first")
    out = out.sort_values(["institution", "symbol"], kind="stable").reset_index(drop=True)

    if out.empty:
        raise ValueError("No valid mutual-fund ticker symbols were found.")

    return out


@st.cache_data(show_spinner=False)
def load_repo_database(path_str: str) -> pd.DataFrame:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"{DB_FILENAME} was not found beside app.py."
        )
    return normalize_database(pd.read_csv(path))


def safe_filename(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.\-]+", "_", str(text).strip())
    return text.strip("_") or "fund"


def build_history_args(mode: str, interval: str):
    """Return kwargs for yfinance.Ticker.history."""
    if mode == "Recent period":
        period = st.session_state.get("recent_period", "10y")
        return {"period": period, "interval": interval}

    if mode == "Year block":
        start_year = int(st.session_state["start_year"])
        end_year = int(st.session_state["end_year"])
        if end_year < start_year:
            start_year, end_year = end_year, start_year
        start = date(start_year, 1, 1)
        end = date(end_year, 12, 31) + timedelta(days=1)
        return {"start": str(start), "end": str(end), "interval": interval}

    start_date = st.session_state["custom_start"]
    end_date = st.session_state["custom_end"]
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    return {
        "start": str(start_date),
        "end": str(end_date + timedelta(days=1)),
        "interval": interval,
    }


def download_one(row: dict, history_kwargs: dict):
    symbol = row["symbol"]
    try:
        hist = yf.Ticker(symbol).history(
            auto_adjust=False,
            actions=True,
            **history_kwargs,
        )

        if hist is None or hist.empty:
            return symbol, None, "No price history returned."

        hist = hist.copy()
        hist.index.name = "Date"
        hist = hist.reset_index()

        # Make the date column friendly for CSV output.
        if "Date" in hist.columns:
            try:
                hist["Date"] = pd.to_datetime(hist["Date"]).dt.strftime("%Y-%m-%d")
            except Exception:
                pass

        # Add fund metadata to every record.
        hist.insert(0, "Institution", row.get("institution", ""))
        hist.insert(0, "Fund_Name", row.get("fund_name", ""))
        hist.insert(0, "Symbol", symbol)

        return symbol, hist, ""

    except Exception as exc:
        return symbol, None, str(exc)


def make_zip(batch_df: pd.DataFrame, history_kwargs: dict):
    rows = batch_df.to_dict("records")
    successes = []
    errors = []

    progress = st.progress(0.0)
    status = st.empty()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(download_one, row, history_kwargs): row
            for row in rows
        }

        completed = 0
        for fut in as_completed(futures):
            row = futures[fut]
            completed += 1
            symbol, hist, err = fut.result()

            status.write(
                f"Downloading mutual funds… {completed:,} / {len(rows):,} "
                f"• {symbol}"
            )
            progress.progress(completed / max(1, len(rows)))

            if hist is None:
                errors.append({
                    "symbol": symbol,
                    "fund_name": row.get("fund_name", ""),
                    "institution": row.get("institution", ""),
                    "error": err,
                })
            else:
                successes.append((row, hist))

    status.write(
        f"Finished • {len(successes):,} downloaded • {len(errors):,} error(s)"
    )

    memory = io.BytesIO()
    combined_frames = []

    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest_rows = []

        for row, hist in successes:
            symbol = row["symbol"]
            fund_name = row.get("fund_name", "")
            institution = row.get("institution", "")

            filename = f"{safe_filename(symbol)}.csv"
            zf.writestr(filename, hist.to_csv(index=False))

            combined_frames.append(hist)

            manifest_rows.append({
                "symbol": symbol,
                "fund_name": fund_name,
                "institution": institution,
                "rows_downloaded": len(hist),
                "file": filename,
                "status": "OK",
            })

        for e in errors:
            manifest_rows.append({
                "symbol": e["symbol"],
                "fund_name": e["fund_name"],
                "institution": e["institution"],
                "rows_downloaded": 0,
                "file": "",
                "status": f"ERROR: {e['error']}",
            })

        manifest = pd.DataFrame(manifest_rows)
        zf.writestr("MANIFEST.csv", manifest.to_csv(index=False))

        if errors:
            zf.writestr("ERRORS.csv", pd.DataFrame(errors).to_csv(index=False))

        if combined_frames:
            combined = pd.concat(combined_frames, ignore_index=True)
            zf.writestr("ALL_MUTUAL_FUNDS_COMBINED.csv", combined.to_csv(index=False))

        readme = (
            "Batched Mutual Fund Downloader\n\n"
            "Each successfully downloaded mutual fund has its own CSV file.\n"
            "ALL_MUTUAL_FUNDS_COMBINED.csv contains all successful downloads "
            "in one long-format file.\n"
            "MANIFEST.csv lists every requested symbol and its result.\n"
            "ERRORS.csv appears only when one or more tickers failed.\n"
        )
        zf.writestr("README.txt", readme)

    memory.seek(0)
    return memory.getvalue(), len(successes), errors


# -------------------------------------------------------------------
# Page
# -------------------------------------------------------------------

st.title("📥 Batched Mutual Fund Downloader")
st.caption("GitHub / Streamlit version • downloads mutual-fund price history in ZIP batches")

with st.expander("Mutual-fund database", expanded=False):
    st.write(
        "The deployed GitHub app reads **mutual_funds.csv** from the same "
        "repository as **app.py**. You can also upload a CSV here temporarily "
        "to test a new database before committing it to GitHub."
    )
    uploaded_db = st.file_uploader(
        "Optional temporary mutual-fund CSV",
        type=["csv"],
        help="Required column: symbol or ticker. Optional: fund_name, institution/fund_family, category.",
    )

try:
    if uploaded_db is not None:
        database = normalize_database(pd.read_csv(uploaded_db))
        db_source = "Temporary uploaded CSV"
    else:
        database = load_repo_database(str(Path(__file__).with_name(DB_FILENAME)))
        db_source = DB_FILENAME
except Exception as exc:
    st.error(str(exc))
    st.stop()

st.success(
    f"Database ready: **{len(database):,} mutual-fund symbols** • Source: **{db_source}**"
)

st.header("1. Choose institution and history")

institutions = sorted(database["institution"].dropna().unique().tolist())
institution = st.selectbox(
    "Financial institution / fund family",
    ["All Institutions"] + institutions,
)

if institution == "All Institutions":
    filtered = database.copy()
else:
    filtered = database[database["institution"] == institution].copy()

interval_label = st.selectbox(
    "Data interval",
    ["Daily (1d)", "Weekly (1wk)", "Monthly (1mo)"],
)
interval = {
    "Daily (1d)": "1d",
    "Weekly (1wk)": "1wk",
    "Monthly (1mo)": "1mo",
}[interval_label]

st.write("Date selection")
mode = st.radio(
    "Date selection",
    ["Recent period", "Year block", "Custom date range"],
    horizontal=True,
    label_visibility="collapsed",
)

current_year = date.today().year

if mode == "Recent period":
    st.selectbox(
        "History to include",
        ["1y", "2y", "5y", "10y", "max"],
        index=3,
        key="recent_period",
    )

elif mode == "Year block":
    c1, c2 = st.columns(2)
    years = list(range(1980, current_year + 1))
    with c1:
        st.selectbox(
            "Start year",
            years,
            index=max(0, len(years) - 11),
            key="start_year",
        )
    with c2:
        st.selectbox(
            "End year",
            years,
            index=len(years) - 1,
            key="end_year",
        )

else:
    c1, c2 = st.columns(2)
    with c1:
        st.date_input(
            "Start date",
            value=date.today() - timedelta(days=3650),
            key="custom_start",
        )
    with c2:
        st.date_input(
            "End date",
            value=date.today(),
            key="custom_end",
        )

batch_size = st.slider(
    "Mutual funds per ZIP batch",
    min_value=25,
    max_value=500,
    value=200,
    step=25,
)

batch_count = max(1, math.ceil(len(filtered) / batch_size))

st.info(
    f"{institution}: **{len(filtered):,} mutual-fund symbols**. "
    f"At **{batch_size} funds per ZIP**, this group requires "
    f"**{batch_count} batch(es)**."
)

st.header("2. Choose the institution batch")

batch_number = st.number_input(
    "Batch number",
    min_value=1,
    max_value=batch_count,
    value=1,
    step=1,
)

start = (int(batch_number) - 1) * batch_size
end = min(start + batch_size, len(filtered))
batch_df = filtered.iloc[start:end].copy()

st.write(
    f"**{institution} — Batch {int(batch_number)} of {batch_count}: "
    f"{len(batch_df):,} mutual fund(s).**"
)

with st.expander("Preview this institution batch", expanded=False):
    st.dataframe(
        batch_df[["symbol", "fund_name", "institution", "category"]],
        use_container_width=True,
        hide_index=True,
    )

history_kwargs = build_history_args(mode, interval)

if st.button(
    "📦 BUILD THIS MUTUAL-FUND ZIP BATCH",
    type="primary",
    use_container_width=True,
):
    with st.spinner("Building ZIP batch…"):
        zip_bytes, ok_count, errors = make_zip(batch_df, history_kwargs)

    tag = safe_filename(institution)
    filename = (
        f"MUTUAL_FUNDS_{tag}_BATCH_{int(batch_number):02d}_OF_{batch_count:02d}.zip"
    )

    st.session_state["last_zip_bytes"] = zip_bytes
    st.session_state["last_zip_name"] = filename
    st.session_state["last_zip_ok"] = ok_count
    st.session_state["last_zip_errors"] = len(errors)

if "last_zip_bytes" in st.session_state:
    st.success(
        f"ZIP is ready • {st.session_state['last_zip_ok']:,} successful "
        f"• {st.session_state['last_zip_errors']:,} error(s)"
    )
    st.download_button(
        "⬇️ DOWNLOAD MUTUAL-FUND ZIP",
        data=st.session_state["last_zip_bytes"],
        file_name=st.session_state["last_zip_name"],
        mime="application/zip",
        use_container_width=True,
    )

st.divider()
st.caption(
    "Historical prices are requested from Yahoo Finance through yfinance. "
    "Some mutual-fund symbols may be unavailable, renamed, merged, or delisted; "
    "those symbols are listed in ERRORS.csv inside the ZIP."
)
