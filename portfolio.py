from __future__ import annotations

import pandas as pd

from data import get_price_data, get_dividend_data

def parse_portfolio_input(text: str) -> list[dict[str, float | str]]:
    """
    Parse multiline portfolio input in the form:
    TICKER, SHARES

    Example:
    AAPL, 10
    MSFT, 5
    KO, 20
    """
    if text is None:
        return []

    text = text.strip()

    if not text:
        return []

    holdings: list[dict[str, float | str]] = []
    lines = text.splitlines()

    for line in lines:
        line = line.strip()

        if not line:
            continue

        parts = [part.strip() for part in line.split(",")]

        if len(parts) != 2:
            continue

        ticker = parts[0].upper()

        try:
            shares = float(parts[1])
        except ValueError:
            continue

        holdings.append({
            "Ticker": ticker,
            "Shares": shares,
        })

    return holdings

def build_portfolio_table(holdings: list[dict[str, float | str]]) -> pd.DataFrame:
    """
    Build a portfolio table with price, market value, annual income,
    monthly income, allocation %, and income %.
    """
    if holdings is None or len(holdings) == 0:
        return pd.DataFrame()

    rows: list[dict[str, float | str]] = []

    for holding in holdings:
        ticker = str(holding["Ticker"])
        shares = float(holding["Shares"])

        try:
            end_for_download = pd.Timestamp.today() + pd.Timedelta(days=1)

            price_df = get_price_data(
                ticker,
                "2025-01-01",
                str(end_for_download.date())
            )

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
                "Error": "",
            })

        except Exception as exc:
            rows.append({
                "Ticker": ticker,
                "Shares": shares,
                "Price": 0.0,
                "Market Value": 0.0,
                "Annual Dividend/Share": 0.0,
                "Annual Income": 0.0,
                "Monthly Income": 0.0,
                "Error": str(exc),
            })

    portfolio_df = pd.DataFrame(rows)

    if not portfolio_df.empty:
        total_value = portfolio_df["Market Value"].sum()
        total_income = portfolio_df["Annual Income"].sum()

        if total_value > 0:
            portfolio_df["Allocation %"] = portfolio_df["Market Value"] / total_value
        else:
            portfolio_df["Allocation %"] = 0.0

        if total_income > 0:
            portfolio_df["Income %"] = portfolio_df["Annual Income"] / total_income
        else:
            portfolio_df["Income %"] = 0.0

    return portfolio_df
