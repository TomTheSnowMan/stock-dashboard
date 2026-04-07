from __future__ import annotations

import numpy as np
import pandas as pd

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
	"""
	Add moving average, daily returns, cumulative return, rolling max, and drawdown.
	"""
	out = df.copy()

	out["Daily Return"] = out["Close"].pct_change()
	out["MA20"] = out["Close"].rolling(20).mean()
	out["MA50"] = out["Close"].rolling(50).mean()

	out["Cumulative Return"] = (1 + out["Daily Return"].fillna(0.0)).cumprod()
	out["Rolling Max"] = out["Close"].cummax()
	out["Drawdown"] = out["Close"] / out["Rolling Max"] - 1

	return out

def calculate_summary_stats(df: pd.DataFrame) -> dict[str, float | int]:
	"""
	Calculate headline analytics for the dashboard.
	"""
	if df.empty:
		raise ValueError("Cannot calculate stats on empty data.")

	daily_returns = df["Daily Return"].dropna()

	total_return = df["Close"].iloc[-1] / df["Close"].iloc[0] - 1

	if len(daily_returns) > 1:
		annualized_volatility = daily_returns.std(ddof=1) * np.sqrt(252)
		mean_daily_return = daily_returns.mean()
		best_day = daily_returns.max()
		worst_day = daily_returns.min()
	else:
		annualized_volatility = 0.0
		mean_daily_return = 0.0
		best_day = 0.0
		worst_day = 0.0

	max_drawdown = df["Drawdown"].min() if "Drawdown" in df.columns else 0.0

	return {
		"latest_close": float(df["Close"].iloc[-1]),
		"total_return": float(total_return),
		"annualized_volatility": float(annualized_volatility),
		"max_drawdown": float(max_drawdown),
		"mean_daily_return": float(mean_daily_return),
		"best_day": float(best_day),
		"worst_day": float(worst_day),
		"num_days": int(len(df)),
	}

def format_pct(value: float) -> str:
	return f"{value:.2%}"

def format_price(value: float) -> str:
	return f"${value:,.2f}"