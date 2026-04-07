from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data import get_price_data, merge_with_benchmark, get_dividend_data
from indicators import (
	add_indicators,
	calculate_summary_stats,
	format_pct,
	format_price
)

def parse_portfolio_input(text):
	if text is None:
		return []

	text = text.strip()

	if not text:
		return []

	holdings = []
	lines = text.splitlines()

	for line in lines:
		line = line.strip()

		if not line:
			continue

		parts = [part.strip() for part in line.split(",")]

		if len(parts) != 2:
			continue

		ticker = parts[0].strip().upper()

		try:
			shares = float(parts[1])
		except ValueError:
			continue

		holdings.append({"Ticker": ticker, "Shares": shares})

	return holdings

def build_portfolio_table(holdings):
	if holdings is None:
		return pd.DataFrame()

	if len(holdings) == 0:
		return pd.DataFrame()

	rows = []

	for holding in holdings:
		ticker = holding["Ticker"]
		shares = holding["Shares"]

		try:
			end_for_download = pd.Timestamp.today() + pd.Timedelta(days=1)

			price_df = get_price_data(ticker, "2025-01-01", str(end_for_download.date()))

			if price_df.empty:
				raise ValueError(f"No price data returned for {ticker}")

			latest_price = float(price_df["Close"].iloc[-1])

			dividend_data = get_dividend_data(ticker)
			annual_dividend_per_share = dividend_data["annual_dividend_per_share"]

			market_value = shares * latest_price
			annual_income = shares * annual_dividend_per_share
			monthly_income = annual_income / 12

			rows.append({
				"Ticker": ticker,
				"Shares": shares,
				"Price": latest_price,
				"Market Value": market_value,
				"Annual Dividend/Share": annual_dividend_per_share,
				"Annual Income": annual_income,
				"Monthly Income": monthly_income,
				"Error": ""
			})

		except Exception:
			rows.append({
				"Ticker": ticker,
				"Shares": shares,
				"Price": 0.0,
				"Market Value": 0.0,
				"Annual Dividend/Share": 0.0,
				"Annual Income": 0.0,
				"Monthly Income": 0.0,
				"Error": str(exc)
			})

	portfolio_df = pd.DataFrame(rows)

	if not portfolio_df.empty:
		total_value = portfolio_df["Market Value"].sum()
		if total_value > 0:
			portfolio_df["Allocation %"] = portfolio_df["Market Value"] / total_value
		else:
			portfolio_df["Allocation %"] = 0.0

	return portfolio_df

st.set_page_config(
	page_title="Stock Market Analytics Dashboard",
	layout="wide",
)

st.title("Stock Market Analytics Dashboard")
st.caption("V1: price, trend, risk, benchmark comparison")

with st.sidebar:
	st.header("Inputs")
	ticker = st.text_input("Ticker", value="AAPL").upper().strip()
	benchmark = st.text_input("Benchmark", value="SPY").upper().strip()

	default_start = pd.to_datetime("2025-01-01").date()
	default_end = pd.Timestamp.today().date()

	start_date = st.date_input("Start Date", value=default_start)
	end_date = st.date_input("End Date", value=default_end)

	chart_type = st.selectbox("Chart type", ["Line", "Candlestick"])
	shares_owned = st.number_input("Shares owned", min_value=0.0, value=100.0, step=1.0)

	st.markdown("---")
	st.markdown(
		"Tip: Start with large liquid tickers like 'AAPL', 'MSFT, 'NVDA', 'SPY'."
	)

	st.markdown("---")
	st.subheader("Portfolio Mode")

	portfolio_text = st.text_area(
		"Enter holdings: TICKER, SHARES (one per line)",
		value="AAPL,10\nMSFT,5\nKO,20\nO,30",
		height=150,
	)

if not ticker:
	st.warning("Enter a ticker to begin.")
	st.stop()

if start_date >= end_date:
	st.error("Start date must be earlier than end date.")
	st.stop()

try:
	#make end date inclusive
	end_for_download = pd.to_datetime(end_date) + pd.Timedelta(days=1)

	stock_df = get_price_data(ticker, str(start_date), str(end_for_download.date()))
	benchmark_df = get_price_data(benchmark, str(start_date), str(end_for_download.date()))
	dividend_data = get_dividend_data(ticker)

	#handle empty data here
	if stock_df.empty:
		st.warning("No trading data found for that ticker and date range. Try widening the dates.")
		st.stop()

	if benchmark_df.empty:
		st.warning("No benchmark data found. Try widening the dates.")
		st.stop()

	#only run calculations after data is confirmed valid
	stock_df = add_indicators(stock_df)
	benchmark_df = add_indicators((benchmark_df))

	comparison_df = merge_with_benchmark(stock_df, benchmark_df, ticker, benchmark)
	stats = calculate_summary_stats(stock_df)

	annual_dividend_per_share = dividend_data["annual_dividend_per_share"]
	dividend_yield = dividend_data["dividend_yield"]
	dividend_history = dividend_data["dividend_history"]

	estimated_annual_income = shares_owned * annual_dividend_per_share
	estimated_monthly_income = estimated_annual_income / 12
	position_value = shares_owned * stats["latest_close"]

except Exception as exc:
	st.error(f"Could not load data: {exc}")
	st.stop()

portfolio_holdings = parse_portfolio_input(portfolio_text)
st.write("Parsed holdings:", portfolio_holdings)
portfolio_df = build_portfolio_table(portfolio_holdings)

#Top Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Latest Close", format_price(stats["latest_close"]))
m2.metric("Total Return", format_pct(stats["total_return"]))
m3.metric("Annualized Volatility", format_pct(stats["annualized_volatility"]))
m4.metric("Max Drawdown", format_pct(stats["max_drawdown"]))

st.subheader("Dividend Income")

d1, d2, d3, d4 = st.columns(4)
d1.metric("Dividend Yield", format_pct(dividend_yield))
d2.metric("Annual Dividend / Share", format_price(annual_dividend_per_share))
d3.metric("Estimated Annual Income", format_price(estimated_annual_income))
d4.metric("Estimated Monthly Income", format_price(estimated_monthly_income))

#Price Chart
st.subheader(f"{ticker} Price")

if chart_type == "Line":
	fig_price = go.Figure()
	fig_price.add_trace(
		go.Scatter(
			x=stock_df["Date"],
			y=stock_df["Close"],
			mode="lines",
			name="Close",
		)
	)
	fig_price.add_trace(
		go.Scatter(
			x=stock_df["Date"],
			y=stock_df["MA20"],
			mode="lines",
			name="MA20",
		)
	)
	fig_price.add_trace(
		go.Scatter(
			x=stock_df["Date"],
			y=stock_df["MA50"],
			mode="lines",
			name="MA50",
		)
	)
else:
	fig_price = go.Figure()
	fig_price.add_trace(
		go.Candlestick(
			x=stock_df["Date"],
			open=stock_df["Open"],
			high=stock_df["High"],
			low=stock_df["Low"],
			close=stock_df["Close"],
			name="Price",
		)
	)
	fig_price.add_trace(
		go.Scatter(
			x=stock_df["Date"],
			y=stock_df["MA20"],
			mode="lines",
			name="MA20",
		)
	)
	fig_price.add_trace(
		go.Scatter(
			x=stock_df["Date"],
			y=stock_df["MA50"],
			mode="lines",
			name="MA50",
		)
	)

fig_price.update_layout(
	xaxis_title="Date",
	yaxis_title="Price",
	legend_title="Series",
	height=500,
)
st.plotly_chart(
	fig_price,
	config={"responsive": True}
)

# Benchmark Comparison
st.subheader(f"{ticker} vs {benchmark}")

fig_compare = go.Figure()
fig_compare.add_trace(
	go.Scatter(
		x=comparison_df["Date"],
		y=comparison_df[f"{ticker}_GrowthOf10k"],
		mode="lines",
		name=f"{ticker} Growth of $10,000",
	)
)
fig_compare.add_trace(
	go.Scatter(
		x=comparison_df["Date"],
		y=comparison_df[f"{benchmark}_GrowthOf10k"],
		mode="lines",
		name=f"{benchmark} Growth of $10,000",
	)
)
fig_compare.update_layout(
	xaxis_title="Date",
	yaxis_title="Portfolio Value ($)",
	height=450,
)
st.plotly_chart(
	fig_compare,
	config={"responsive": True}
)

left, right = st.columns(2)

with left:
	st.subheader("Daily Returns Distribution")
	fig_hist = px.histogram(
		stock_df.dropna(subset=["Daily Return"]),
		x="Daily Return",
		nbins=50
	)
	fig_hist.update_layout(
		xaxis_title="Daily Return",
		yaxis_title="Frequency",
		height=400,
	)
	st.plotly_chart(
		fig_hist,
		config={"responsive": True}
	)

with right:
	st.subheader("Drawdown")
	fig_drawdown = go.Figure()
	fig_drawdown.add_trace(
		go.Scatter(
			x=stock_df["Date"],
			y=stock_df["Drawdown"],
			mode="lines",
			name="Drawdown",
		)
	)
	fig_drawdown.update_layout(
		xaxis_title="Date",
		yaxis_title="Drawdown",
		height=400,
	)
	st.plotly_chart(
		fig_drawdown,
		config={"responsive": True}
	)

#Recent data and summary
st.subheader("Summary")

summary_col1, summary_col2 = st.columns(2)
with summary_col1:
	st.write(f"**Ticker:** {ticker}")
	st.write(f"**Benchmark:** {benchmark}")
	st.write(f"**Start:** {start_date}")
	st.write(f"**End:** {end_date}")

with summary_col2:
	st.write(f"**Mean Daily Return:** {format_pct(stats['mean_daily_return'])}")
	st.write(f"**Best Day:** {format_pct(stats['best_day'])}")
	st.write(f"**Worst Day:** {format_pct(stats['worst_day'])}")
	st.write(f"**Trading Days:** {stats['num_days']}")

st.subheader("Recent Data")
display_cols = [
	"Date",
	"Open",
	"High",
	"Low",
	"Close",
	"Volume",
	"MA20",
	"MA50",
	"Daily Return",
	"Drawdown",
]
st.dataframe(stock_df[display_cols].tail(20), width='stretch')

st.subheader("Dividend History")

if dividend_history.empty:
	st.info("No dividend history available for this ticker.")
else:
	dividend_display = dividend_history.copy().head(12)
	dividend_display["Date"] = pd.to_datetime(dividend_display["Date"]).dt.date
	dividend_display["Dividend"] = dividend_display["Dividend"].round(4)
	st.dataframe(dividend_display, width='stretch')

st.markdown("---")
st.header("Portfolio Mode")

if portfolio_df.empty:
	st.info("No portfolio holdings entered.")
else:
	total_portfolio_value = portfolio_df["Market Value"].sum()
	total_annual_income = portfolio_df["Annual Income"].sum()
	total_monthly_income = portfolio_df["Monthly Income"].sum()

	p1,p2,p3 = st.columns(3)
	p1.metric("Total Portfolio Value", format_price(total_portfolio_value))
	p2.metric("Total Annual Income", format_price(total_annual_income))
	p3.metric("Total Monthly Dividend Income", format_price(total_monthly_income))

st.subheader("Portfolio Breakdown")

portfolio_display = portfolio_df.copy()

if not portfolio_display.empty:
	for col in ["Price", "Market Value", "Annual Dividend/Share", "Annual Income", "Monthly Income"]:
		portfolio_display[col] = portfolio_display[col].round(2)

	portfolio_display["Allocation %"] = (portfolio_display["Allocation %"] * 100).round(2)

	st.dataframe(portfolio_display, width='stretch')

if not portfolio_df.empty and portfolio_df["Market Value"].sum() > 0:
	st.subheader("Portfolio Allocation")

	portfolio_chart_df = portfolio_df.copy()

	# keep only rows with actual market value
	portfolio_chart_df = portfolio_chart_df[portfolio_chart_df["Market Value"] > 0]

	if portfolio_chart_df.empty:
		st.info("No valid portfolio values to chart yet.")
	else:
		fig_portfolio = px.pie(
			portfolio_chart_df,
			names="Ticker",
			values="Market Value",
			title="Portfolio Allocation by Market Value"
		)
	st.plotly_chart(
		fig_portfolio,
		config={"responsive": True, "displaylogo": False}
	)