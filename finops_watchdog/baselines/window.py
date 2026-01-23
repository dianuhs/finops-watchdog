from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

import pandas as pd


@dataclass
class ServiceBaseline:
    """Baseline view of per-service costs over a reference window."""

    reference_start: pd.Timestamp
    reference_end: pd.Timestamp
    daily_avg: pd.Series
    mode: Literal["window", "weekday"]


def build_service_baseline(
    df: pd.DataFrame,
    window_days: int = 14,
    prefer_weekday: bool = True,
    min_weekday_points: int = 3,
) -> ServiceBaseline:
    """Build a simple per-service baseline from FinOps Lite services data.

    Strategy:

      1. Take a rolling window of history (default 14 days) ending before
         the most recent day in the dataset.
      2. If prefer_weekday is True, and there are enough prior days that
         share the same weekday as the latest day (min_weekday_points),
         build the baseline from those weekday-matching days only.
      3. Otherwise, fall back to the full rolling window.

    The result is a per-service average daily cost over the chosen window.
    """
    if "date" not in df.columns or "service" not in df.columns or "cost" not in df.columns:
        raise ValueError("services dataframe must contain 'date', 'service', and 'cost' columns.")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date")

    if df.empty:
        raise ValueError("services dataframe is empty after parsing dates.")

    current_date = df["date"].max()
    window_start = current_date - timedelta(days=window_days)

    # Base rolling window: all days in the lookback (excluding current)
    window_df = df[(df["date"] > window_start) & (df["date"] < current_date)]
    if window_df.empty:
        raise ValueError("Not enough history to build a baseline window.")

    mode: Literal["window", "weekday"] = "window"
    ref_df = window_df

    if prefer_weekday:
        current_weekday = current_date.weekday()
        weekday_df = window_df[window_df["date"].dt.weekday == current_weekday]

        # Count distinct prior days for this weekday
        distinct_days = weekday_df["date"].dt.normalize().nunique()

        if distinct_days >= min_weekday_points:
            ref_df = weekday_df
            mode = "weekday"

    # Average daily cost per service over the reference window
    daily = (
        ref_df.groupby(["date", "service"])["cost"]
        .sum()
        .groupby("service")
        .mean()
    )

    return ServiceBaseline(
        reference_start=ref_df["date"].min(),
        reference_end=ref_df["date"].max(),
        daily_avg=daily,
        mode=mode,
    )
