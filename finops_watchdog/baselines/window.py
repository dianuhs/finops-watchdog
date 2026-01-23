from dataclasses import dataclass
from datetime import timedelta

import pandas as pd


@dataclass
class ServiceBaseline:
    """Baseline costs per service over a reference window."""

    reference_start: pd.Timestamp
    reference_end: pd.Timestamp
    daily_avg: pd.Series  # index: service, values: baseline daily cost


def build_service_baseline(services_df: pd.DataFrame, window_days: int = 14) -> ServiceBaseline:
    """
    Build a simple rolling baseline per service.

    Assumes services_df has at least:
      - 'date' (parseable to datetime)
      - 'service'
      - 'cost' (numeric)
    """
    df = services_df.copy()
    if "date" not in df.columns or "service" not in df.columns or "cost" not in df.columns:
        raise ValueError("services.csv must contain 'date', 'service', and 'cost' columns.")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    current_date = df["date"].max()
    window_start = current_date - timedelta(days=window_days)

    # reference window excludes the current day
    ref = df[(df["date"] > window_start) & (df["date"] < current_date)]
    if ref.empty:
        raise ValueError("Not enough history to build a baseline window.")

    # average daily cost per service over the window
    daily = (
        ref.groupby(["date", "service"])["cost"]
        .sum()
        .groupby("service")
        .mean()
    )

    return ServiceBaseline(
        reference_start=ref["date"].min(),
        reference_end=ref["date"].max(),
        daily_avg=daily,
    )
