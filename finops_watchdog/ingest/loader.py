from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

DEFAULT_OVERVIEW = "overview.csv"
DEFAULT_SERVICES = "services.csv"
DEFAULT_FOCUS = "focus-lite.csv"

SERVICE_COST_CANDIDATES: Sequence[str] = ("cost", "unblended_cost", "amount")


@dataclass
class LiteInputs:
    """Container for FinOps Lite outputs used by Watchdog."""

    root: Path
    overview: pd.DataFrame
    services: pd.DataFrame
    focus: Optional[pd.DataFrame] = None


def _normalize_services_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure services DataFrame has date, service, cost columns.

    Tries to map common FinOps Lite-style cost columns into a unified 'cost'.
    """
    df = df.copy()

    if "service" not in df.columns:
        raise ValueError("services.csv must contain a 'service' column.")

    if "date" not in df.columns:
        raise ValueError("services.csv must contain a 'date' column.")

    # Find a cost-like column and normalize to 'cost'
    cost_col = None
    for candidate in SERVICE_COST_CANDIDATES:
        if candidate in df.columns:
            cost_col = candidate
            break

    if cost_col is None:
        raise ValueError(
            f"services.csv must contain one of the cost columns: {', '.join(SERVICE_COST_CANDIDATES)}"
        )

    if cost_col != "cost":
        df = df.rename(columns={cost_col: "cost"})

    # Ensure numeric
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce").fillna(0.0)

    return df


def load_lite_outputs(root: str | Path) -> LiteInputs:
    """Load FinOps Lite CSV outputs from a directory.

    Expected files (by default):
      - overview.csv
      - services.csv
      - focus-lite.csv (optional)

    This is intentionally strict for overview/services and lenient for focus.
    """
    root_path = Path(root)

    overview_path = root_path / DEFAULT_OVERVIEW
    services_path = root_path / DEFAULT_SERVICES
    focus_path = root_path / DEFAULT_FOCUS

    if not overview_path.exists():
        raise FileNotFoundError(f"Missing overview CSV at {overview_path}")

    if not services_path.exists():
        raise FileNotFoundError(f"Missing services CSV at {services_path}")

    overview_df = pd.read_csv(overview_path)
    services_df = pd.read_csv(services_path)
    services_df = _normalize_services_df(services_df)

    focus_df = None
    if focus_path.exists():
        focus_df = pd.read_csv(focus_path)

    return LiteInputs(
        root=root_path,
        overview=overview_df,
        services=services_df,
        focus=focus_df,
    )
