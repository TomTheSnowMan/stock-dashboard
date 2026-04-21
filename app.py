from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data import get_price_data, merge_with_benchmark, get_dividend_data
from indicators import add_indicators, calculate_summary_stats, format_pct, format_price
from portfolio import parse_portfolio_input, build_portfolio_table
from dividends import build_monthly_dividend_breakdown, build_portfolio_dividend_calendar
from utils import dataframe_to_csv


st.set_page_config(
	page_title="Stock Market Analytics Dashboard",
	layout="wide",
)

st.title("Stock Market Analytics Dashboard")
st.caption("Price, Trend, Risk, Dividend Income, Portfolio Analytics, and Downloadable Data.")

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
		"Tip: Start with large liquid tickers like 'AAPL', 'MSFT', 'NVDA', 'SPY'."
	)

	st.markdown("---")
	st.subheader("Portfolio Mode")

	portfolio_text = st.text_area(
		"Enter holdings: TICKER, SHARES (one per line)",
		value="AAPL,10\nMSFT,5\nKO,20\nO,30",
		height=150,
	)

	st.markdown("---")
	st.subheader("Premium Access")
	premium_password = st.text_input("Enter Premium Password", type="password")

premium_enabled = premium_password == "dividendpro"

if not ticker:
	st.warning("Enter a ticker to begin.")
	st.stop()

if start_date >= end_date:
	st.error("Start date must be earlier than end date.")
	st.stop()

try:
	# Make end date inclusive
	end_for_download = pd.to_datetime(end_date) + pd.Timedelta(days=1)

	stock_df = get_price_data(ticker, str(start_date), str(end_for_download.date()))
	benchmark_df = get_price_data(benchmark, str(start_date), str(end_for_download.date()))
	dividend_data = get_dividend_data(ticker)

	# Handle empty data here
	if stock_df.empty:
		st.warning("No trading data found for that ticker and date range. Try widening the dates.")
		st.stop()

	if benchmark_df.empty:
		st.warning("No benchmark data found. Try widening the dates.")
		st.stop()

	# Only run calculations after data is confirmed valid
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

	monthly_dividend_df = build_monthly_dividend_breakdown(dividend_history, shares_owned)

except Exception as exc:
	st.error(f"Could not load data: {exc}")
	st.stop()

portfolio_holdings = parse_portfolio_input(portfolio_text)
portfolio_df = build_portfolio_table(portfolio_holdings)
portfolio_calendar_df = build_portfolio_dividend_calendar(portfolio_df)

# Top Metrics
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

# Price Chart
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
	config={"responsive": True, "displaylogo": False},
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
	config={"responsive": True, "displaylogo": False},
)

left, right = st.columns(2)

with left:
	st.subheader("Daily Returns Distribution")
	fig_hist = px.histogram(
		stock_df.dropna(subset=["Daily Return"]),
		x="Daily Return",
		nbins=50,
	)
	fig_hist.update_layout(
		xaxis_title="Daily Return",
		yaxis_title="Frequency",
		height=400,
	)
	st.plotly_chart(
		fig_hist,
		config={"responsive": True, "displaylogo": False},
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
		config={"responsive": True, "displaylogo": False},
	)

# Recent data and summary
st.subheader("Summary")

summary_col1, summary_col2 = st.columns(2)
with summary_col1:
	st.write(f"**Ticker:** {ticker}")
	st.write(f"**Benchmark:** {benchmark}")
	st.write(f"**Start:** {start_date}")
	st.write(f"**End:** {end_date}")
	st.write(f"**Position Value:** {format_price(position_value)}")

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

display_df = stock_df[display_cols].tail(20).copy()
numeric_cols = display_df.select_dtypes(include="number").columns
display_df[numeric_cols] = display_df[numeric_cols].round(4)

st.dataframe(display_df, width='stretch')

st.download_button(
	label="Download Recent Stock Data CSV",
	data=dataframe_to_csv(display_df),
	file_name=f"{ticker.lower()}_recent_data.csv",
	mime="text/csv",
)

st.subheader("Dividend History")

if dividend_history.empty:
	st.info("No dividend history available for this ticker.")
else:
	dividend_display = dividend_history.copy().head(12)
	dividend_display["Date"] = pd.to_datetime(dividend_display["Date"]).dt.date
	dividend_display["Dividend"] = dividend_display["Dividend"].round(4)
	st.dataframe(dividend_display, width='stretch')

	st.download_button(
		label="Download Dividend History CSV",
		data=dataframe_to_csv(dividend_display),
		file_name=f"{ticker.lower()}_dividend_history.csv",
		mime="text/csv",
	)

st.subheader("Monthly Dividend Breakdown")

if monthly_dividend_df.empty:
	st.info("No monthly dividend data available for this ticker.")
else:
	monthly_display =  monthly_dividend_df.copy()
	monthly_display["Dividend_Per_Share"] = monthly_display["Dividend_Per_Share"].round(4)
	monthly_display["Estimated_Income"] = monthly_display["Estimated_Income"].round(2)

	fig_monthly_dividends = px.bar(
		monthly_display,
		x="Year-Month",
		y="Estimated_Income",
		title="Estimated Monthly Dividend Income",
	)
	fig_monthly_dividends.update_layout(
		xaxis_title="Month",
		yaxis_title="Estimated Income ($)",
		height=450,
	)
	st.plotly_chart(
		fig_monthly_dividends,
		config={"responsive": True, "displaylogo": False},
	)

	st.dataframe(monthly_display, use_container_width=True)

	st.download_button(
		label="Download Monthly Dividend Breakdown CSV",
		data=dataframe_to_csv(monthly_display),
		file_name=f"{ticker.lower()}_monthly_dividend_breakdown.csv",
		mime="text/csv",
	)

st.markdown("---")
st.header("Portfolio Mode")

if portfolio_df.empty:
	st.info("No portfolio holdings entered.")
else:
	total_portfolio_value = portfolio_df["Market Value"].sum()
	total_annual_income = portfolio_df["Annual Income"].sum()
	total_monthly_income = portfolio_df["Monthly Income"].sum()

	income_positive_df = portfolio_df[portfolio_df["Annual Income"] > 0].copy()

	if income_positive_df.empty:
		top_income_ticker = "N/A"
		top_income_pct = 0.0
	else:
		top_row = income_positive_df.sort_values("Annual Income", ascending=False).iloc[0]
		top_income_ticker = top_row["Ticker"]
		top_income_pct = top_row["Income %"]

	p1, p2, p3, p4, p5 = st.columns(5)
	p1.metric("Total Portfolio Value", format_price(total_portfolio_value))
	p2.metric("Total Annual Income", format_price(total_annual_income))
	p3.metric("Total Monthly Dividend Income", format_price(total_monthly_income))
	p4.metric("Top Income Contributor", top_income_ticker)
	p5.metric("Top Contributor %", format_pct(top_income_pct))


	st.subheader("Portfolio Breakdown")

	portfolio_display = portfolio_df.copy()
	portfolio_display = portfolio_display.sort_values("Annual Income", ascending=False)


	for col in ["Price", "Market Value", "Annual Dividend/Share", "Annual Income", "Monthly Income"]:
		portfolio_display[col] = portfolio_display[col].round(2)

	portfolio_display["Allocation %"] = (portfolio_display["Allocation %"] * 100).round(2)

	if "Income %" in portfolio_display.columns:
		portfolio_display["Income %"] = (portfolio_display["Income %"] * 100).round(2)

	st.dataframe(portfolio_display, width='stretch')

	st.download_button(
		label="Download Portfolio Breakdown CSV",
		data=dataframe_to_csv(portfolio_display),
		file_name="portfolio_breakdown.csv",
		mime="text/csv",
	)

	st.subheader("Portfolio Dividend Income by Stock")

	portfolio_income_df = portfolio_df.copy()
	portfolio_income_df = portfolio_income_df[portfolio_income_df["Annual Income"] > 0]

	if portfolio_income_df.empty:
		st.info("No dividend paying holdings found in portfolio.")
	else:
		portfolio_income_df = portfolio_income_df.sort_values("Annual Income", ascending=False)

		fig_income_by_stock = px.bar(
			portfolio_income_df,
			x="Ticker",
			y="Annual Income",
			title="Annual Dividend Income by Stock",
			text="Annual Income",
		)
		fig_income_by_stock.update_traces(
			texttemplate="$%{text:.2f}",
			textposition="outside",
		)
		fig_income_by_stock.update_layout(
			xaxis_title="Ticker",
			yaxis_title="Annual Dividend Income ($)",
			height=450,
		)
		st.plotly_chart(
			fig_income_by_stock,
			config={"responsive": True, "displaylogo": False}
		)

	st.subheader("Portfolio Monthly Dividend by Stock")

	portfolio_monthly_df = portfolio_df.copy()
	portfolio_monthly_df = portfolio_monthly_df[portfolio_monthly_df["Monthly Income"] > 0]

	if portfolio_monthly_df.empty:
		st.info("No monthly dividend income available for this portfolio.")
	else:
		portfolio_monthly_df = portfolio_monthly_df.sort_values("Monthly Income", ascending=False)

		fig_monthly_income_by_stock = px.bar(
			portfolio_monthly_df,
			x="Ticker",
			y="Monthly Income",
			title="Average Monthly Dividend Income by Stock",
			text="Monthly Income",
		)
		fig_monthly_income_by_stock.update_traces(
			texttemplate="$%{text:.2f}",
			textposition="outside",
		)
		fig_monthly_income_by_stock.update_layout(
			xaxis_title="Ticker",
			yaxis_title="Monthly Dividend Income ($)",
			height=450,
		)
		st.plotly_chart(
			fig_monthly_income_by_stock,
			config={"responsive": True, "displaylogo": False},
		)

	st.subheader("Portfolio Dividend Income Concentration")

	income_concentration_df = portfolio_df.copy()
	income_concentration_df = income_concentration_df[income_concentration_df["Annual Income"] > 0]

	if income_concentration_df.empty:
		st.info("No dividend income data availability for concentration analysis.")
	else:
		income_concentration_df = income_concentration_df.sort_values("Annual Income", ascending=False)

		fig_income_concentration = px.pie(
			income_concentration_df,
			names="Ticker",
			values="Annual Income",
			title="Dividend Income Concentration by Stock",
		)
		st.plotly_chart(
			fig_income_concentration,
			config={"responsive": True, "displaylogo": False}
		)

	st.subheader("Portfolio Allocation")

	portfolio_chart_df = portfolio_df.copy()
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

st.markdown("---")
st.header("Premium: Portfolio Dividend Calendar")

if not premium_enabled:
	st.info("Premium feature locked. Enter the premium password in the sidebar to view the dividend calendar.")
else:
	calendar_display = portfolio_calendar_df.copy()
	calendar_display["Estimated Income"] = calendar_display["Estimated Income"].round(2)
	calendar_display["Total Income"] = calendar_display["Total Income"].round(2)

	st.subheader("Dividend Payments by Stock and Month")
	st.dataframe(calendar_display, use_container_width=True)

	st.subheader("Monthly Income Calendar")

	calendar_pivot = (
		calendar_display.pivot_table(
			index="Ticker",
			columns="Month",
			values="Estimated Income",
			aggfunc="sum",
			fill_values=0.0,
		)
	)

	month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

	existing_months = [m for m in month_order if m in calendar_pivot.columns]
	calendar_pivot = calendar_pivot.reindex(columns=existing_months, fill_value=0.0)

	totals_row = calendar_pivot.sum(axis=0).to_frame().T
	totals_row.index = ["Total Portfolio Income"]

	calendar_full = pd.concat([calendar_pivot, totals_row], axis=0)
	calendar_full = calendar_full.round(2)

	st.dataframe(calendar_full, use_container_width=True)

	st.download_button(
		label="Download Dividend Calendar CSV",
		data=dataframe_to_csv(calendar_display),
		file_name="portfolio_dividend_calendar.csv",
		mime="text/csv",
	)

st.markdown("---")
st.caption(
	"Built by TomTheSnowMan | Data: Yahoo Finance (yfinance) | For educational use only"
)