from __future__ import annotations

import pandas as pd

from data import get_dividend_data

def build_monthly_dividend_breakdown(
        dividend_history: pd.DataFrame,
        shares_owned: float,
) -> pd.DataFrame:
    """
    Build a monthly dividend breakdown from dividend history.
    Returns a DataFrame with:
    - Year
    - Month Number
    - Month
    - Year-Month
    - Dividend_Per_Share
    - Estimated_Income
    """
    if dividend_history is None or dividend_history.empty:
        return pd.DataFrame()

    df = dividend_history.copy()

    df["Date"] = pd.to_datetime(df["Date"])
    df["Year"] = df["Date"].dt.year
    df["Month Number"] = df["Date"].dt.month
    df["Month"] = df["Date"].dt.strftime("%b")
    df["Year-Month"] = df["Date"].dt.strftime("%Y-%m")

    df["Dividend Income"] = df["Dividend"] * shares_owned

    monthly_df = (
        df.groupby(["Year", "Month Number", "Month", "Year-Month"], as_index=False)
        .agg(
            Dividend_Per_Share=("Dividend", "sum"),
            Estimated_Income=("Dividend Income", "sum")
        )
        .sort_values(["Year", "Month Number"])
    )

    return monthly_df

def build_portfolio_dividend_calendar(portfolio_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a simple monthly dividend calendar for the portfolio.

    Uses each holing's average monthly dividend income and maps it to
    the months in which the ticker has historically paid dividends.
    """
    if portfolio_df is None or portfolio_df.empty:
        return pd.DataFrame()

    calendar_rows = []

    month_names = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }

    for _, row in portfolio_df.iterrows():
        ticker = row["Ticker"]
        monthly_income = float(row["Monthly Income"])

        if monthly_income <= 0:
            continue

        try:
            dividend_data = get_dividend_data(ticker)
            dividend_history = dividend_data["dividend_history"]

            if dividend_history is None or dividend_history.empty:
                continue

            dividend_history = dividend_history.copy()
            dividend_history["Date"] = pd.to_datetime(dividend_history["Date"])
            paid_months = sorted(dividend_history["Date"].dt.month.unique())

            if len(paid_months) == 0:
                continue

            for month_num in paid_months:
                calendar_rows.append({
                    "Ticker": ticker,
                    "Month Number": month_num,
                    "Month": month_names[month_num],
                    "Estimated Income": monthly_income,
                })

        except Exception:
            continue

    calendar_df = pd.DataFrame(calendar_rows)

    if calendar_df.empty:
        return pd.DataFrame()

    calendar_summary = (
        calendar_df.groupby(["Month Number", "Month"], as_index=False)
        .agg(Total_Income=("Estimated Income", "sum"))
        .sort_values("Month Number")
    )

    return calendar_df.merge(calendar_summary, on=["Month Number", "Month"], how="left")
