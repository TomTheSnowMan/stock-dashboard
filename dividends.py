from __future__ import annotations

import pandas as pd

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