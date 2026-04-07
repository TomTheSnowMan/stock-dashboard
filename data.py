import pandas as pd
import streamlit as st
import yfinance as yf

@st.cache_data(ttl=3600)
def get_price_data(ticker: str, start: str, end: str) ->pd.DataFrame:
	"""
	Download OHLCV(Open, High, Low, Close, Volume)price data for a single ticker.
	Cached for 1 hour to reduce repeated downloads.
	"""
	df = yf.download(
		ticker,
		start=start,
		end=end,
		auto_adjust=True,
		progress=False,
	)

	# Flatten MultiIndex columns if returned by yfinance
	if isinstance(df.columns, pd.MultiIndex):
		df.columns = df.columns.get_level_values(0)
	if df.empty:
		return pd.DataFrame

	df = df.reset_index()
	df["Date"] = pd.to_datetime(df["Date"])

	return df

def merge_with_benchmark(stock_df, benchmark_df, stock_ticker, benchmark_ticker):
	stock = stock_df[["Date", "Close"]].copy()
	bench = benchmark_df[["Date", "Close"]].copy()

	stock["Stock Return"] = stock["Close"].pct_change().fillna(0.0)
	bench["Benchmark Return"] = bench["Close"].pct_change().fillna(0.0)

	stock[f"{stock_ticker}_GrowthOf10k"] = 10000 * (1 + stock["Stock Return"]).cumprod()
	bench[f"{benchmark_ticker}_GrowthOf10k"] = 10000 * (1 + bench["Benchmark Return"]).cumprod()

	merged = pd.merge(
		stock[["Date", f"{stock_ticker}_GrowthOf10k"]],
		bench[["Date", f"{benchmark_ticker}_GrowthOf10k"]],
		on="Date",
		how="inner",
	)

	if merged.empty:
		raise ValueError("No overlapping dates found between ticker and benchmark.")

	return merged

def get_dividend_data(ticker):
	stock = yf.Ticker(ticker)
	dividends = stock.dividends

	if dividends is None or dividends.empty:
		return {
			"annual_dividend_per_share": 0.0,
			"dividend_yield": 0.0,
			"dividend_history": pd.DataFrame()
		}

	dividends = dividends.reset_index()
	dividends.columns = ["Date", "Dividend"]
	dividends["Date"] = pd.to_datetime(dividends["Date"])

	#Make Comparison timezone-compatible
	if dividends["Date"].dt.tz is not None:
		one_year_ago = pd.Timestamp.now(tz=dividends["Date"].dt.tz) - pd.Timedelta(days=365)
	else:
		one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)

	recent_dividends = dividends[dividends["Date"] >= one_year_ago]
	annual_dividend_per_share = recent_dividends["Dividend"].sum()

	current_price = 0.0
	try:
		hist = stock.history(period="5d")
		if not hist.empty:
			current_price = float(hist["Close"].iloc[-1])
	except Exception:
		current_price = 0.0

	dividend_yield = 0.0 if current_price == 0 else annual_dividend_per_share / current_price

	return {
		"annual_dividend_per_share": float(annual_dividend_per_share),
		"dividend_yield": float(dividend_yield),
		"dividend_history": dividends.sort_values("Date", ascending=False)
	}