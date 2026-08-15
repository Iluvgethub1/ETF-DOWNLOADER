# ETF Downloader — Institution + Sector

This version organizes ETF CSV files by both the financial institution / ETF sponsor and the ETF's sector or investment category.

Main ZIP structure:

By_Institution/
- BlackRock_iShares/
  - Technology/
  - Financials/
  - Healthcare/
- Vanguard/
  - Broad_Market/
  - Technology/
- State_Street_SPDR/
  - Energy/
  - Financials/

It also creates a By_Sector folder and combined CSVs.

Sector/category labels include Technology, Financials, Energy, Healthcare, Industrials, Consumer Discretionary, Consumer Staples, Utilities, Materials, Real Estate, Communication Services, Fixed Income, Commodities, International, Broad Market, Thematic/Other, and Unclassified.

Broad-market, bond, commodity, and international ETFs are not forced into a stock-market sector.

Run locally:

pip install -r requirements.txt
streamlit run app.py
