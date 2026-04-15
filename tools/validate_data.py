import pandas as pd
from pathlib import Path
from typing import Union

REQUIRED_COLUMNS = [
    "Traffic Source", "Funnel", "Cost", "Total Revenue", "Sales",
    "Leads", "Click", "Impressions", "Average Order Value"
]

def load_sheet(path: Union[str, Path], sheet_name: str, client: str) -> pd.DataFrame:
    """
    Load a sheet from the Hyros xlsx export and filter by Client column.
    sheet_name is "Campaigns" or "Ads".
    """
    path = Path(path)
    df = pd.read_excel(path, sheet_name=sheet_name)
    # Normalize column names: strip whitespace
    df.columns = df.columns.str.strip()
    # Filter to the target client
    if "Client" in df.columns:
        df = df[df["Client"] == client].copy()
    for col in ["Cost", "Total Revenue", "Sales", "Leads", "Impressions", "Click", "Average Order Value"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df.reset_index(drop=True)


def run_checkpoints(df: pd.DataFrame) -> dict:
    """
    Run the 4 mandatory verification checkpoints.
    Returns dict with checkpoint_N_passed keys and computed totals.
    """
    tol = 0.01  # $0.01 tolerance for floating point

    google = df[df["Traffic Source"].str.lower() == "google"]
    meta   = df[df["Traffic Source"].str.lower() == "meta"]

    google_cost  = google["Cost"].sum()
    meta_cost    = meta["Cost"].sum()
    total_cost   = df["Cost"].sum()

    google_sales = google["Sales"].sum()
    meta_sales   = meta["Sales"].sum()
    total_sales  = df["Sales"].sum()

    google_tof_sales = google[google["Funnel"].str.upper() == "TOF"]["Sales"].sum()
    google_mof_sales = google[google["Funnel"].str.upper() == "MOF"]["Sales"].sum()
    google_bof_sales = google[google["Funnel"].str.upper() == "BOF"]["Sales"].sum()

    meta_tof_sales = meta[meta["Funnel"].str.upper() == "TOF"]["Sales"].sum()
    meta_mof_sales = meta[meta["Funnel"].str.upper() == "MOF"]["Sales"].sum()
    meta_bof_sales = meta[meta["Funnel"].str.upper() == "BOF"]["Sales"].sum()

    cp1 = bool(abs((google_cost + meta_cost) - total_cost) < tol)
    cp2 = bool(abs((google_sales + meta_sales) - total_sales) < tol)
    cp3 = bool(abs((google_tof_sales + google_mof_sales + google_bof_sales) - google_sales) < tol)
    cp4 = bool(abs((meta_tof_sales + meta_mof_sales + meta_bof_sales) - meta_sales) < tol)

    return {
        "checkpoint_1_passed": cp1,
        "checkpoint_2_passed": cp2,
        "checkpoint_3_passed": cp3,
        "checkpoint_4_passed": cp4,
        "google_cost": google_cost, "meta_cost": meta_cost, "total_cost": total_cost,
        "google_sales": google_sales, "meta_sales": meta_sales, "total_sales": total_sales,
    }


def validate_or_raise(df: pd.DataFrame) -> dict:
    """Run checkpoints and raise ValueError if any fail."""
    results = run_checkpoints(df)
    failures = [k for k, v in results.items() if k.startswith("checkpoint") and not v]
    if failures:
        raise ValueError(f"Data validation FAILED: {failures}\nTotals: {results}")
    return results
