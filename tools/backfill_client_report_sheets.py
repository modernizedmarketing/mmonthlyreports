#!/usr/bin/env python3
"""Backfill active client report sheets from the consolidated historical workbook."""
from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.control_sheet import (
    DEFAULT_CLIENTS_SHEET,
    ControlSheetClient,
    load_control_sheet_clients,
    select_control_sheet_clients,
)
from tools.google_sheet_report_data import (
    _execute_with_retry,
    _json_safe_cell,
    quote_sheet_name,
    read_sheet_values,
    values_to_dataframe,
)
from tools.google_workspace import build_workspace_services, extract_file_id

SOURCE_CAMPAIGN_TABS = ["Backup Campaigns", "Campaigns"]
SOURCE_AD_TABS = ["Backup Ads", "Ads"]
REPORT_HEADERS = [
    "Source",
    "Traffic Source",
    "Source Link",
    "Click",
    "Cost",
    "Revenue",
    "Recurring Revenue",
    "Sales",
    "Leads",
    "Total Revenue",
    "Impressions",
    "Average Order Value",
    "Client",
    "Month",
    "Year",
    "Funnel",
]
DEDUP_KEYS = ["Client", "Month", "Year", "Source", "Source Link", "Traffic Source", "Funnel"]
TOTAL_CHECK_COLUMNS = ["Click", "Cost", "Revenue", "Recurring Revenue", "Sales", "Leads", "Total Revenue", "Impressions", "Average Order Value"]
NUMERIC_OUTPUT_COLUMNS = TOTAL_CHECK_COLUMNS

MONTH_LOOKUP = {
    name.lower(): name
    for name in calendar.month_name
    if name
}
MONTH_LOOKUP.update(
    {
        abbr.lower(): calendar.month_name[index]
        for index, abbr in enumerate(calendar.month_abbr)
        if abbr
    }
)


@dataclass(frozen=True)
class PreparedClientData:
    client: ControlSheetClient
    campaigns: pd.DataFrame
    ads: pd.DataFrame
    campaign_duplicates_removed: int
    ad_duplicates_removed: int


@dataclass(frozen=True)
class BackfillSummary:
    client_key: str
    client_name: str
    spreadsheet_id: str
    campaign_source_rows: int
    ad_source_rows: int
    campaigns_rows: int
    ads_rows: int
    months: list[str]
    campaign_duplicates_removed: int
    ad_duplicates_removed: int
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill active client Campaigns/Ads sheets from the consolidated historical workbook."
    )
    parser.add_argument(
        "--source-sheet",
        default=os.environ.get("HISTORICAL_REPORTS_SOURCE_SHEET", ""),
        help="Monthly Reports Clients Google Sheet URL or ID.",
    )
    parser.add_argument(
        "--control-sheet",
        default=os.environ.get("MASTER_CONTROL_SHEET_ID", os.environ.get("CONTROL_SHEET_ID", "")),
        help="Monthly Report Master Control Sheet URL or ID.",
    )
    parser.add_argument("--clients-sheet", default=os.environ.get("CONTROL_SHEET_CLIENTS_SHEET", DEFAULT_CLIENTS_SHEET))
    parser.add_argument("--run-mode", choices=["all", "one"], default="all")
    parser.add_argument("--client-key", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.source_sheet:
        raise ValueError("--source-sheet is required or HISTORICAL_REPORTS_SOURCE_SHEET must be set.")
    if not args.control_sheet:
        raise ValueError("--control-sheet is required or MASTER_CONTROL_SHEET_ID/CONTROL_SHEET_ID must be set.")
    if args.run_mode == "one" and not args.client_key:
        raise ValueError("--client-key is required when --run-mode one is used.")


def _column_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _column_map(df: pd.DataFrame) -> dict[str, str]:
    return {_column_key(column): str(column) for column in df.columns}


def _find_column(df: pd.DataFrame, aliases: list[str], tab_name: str, output_name: str) -> str:
    columns = _column_map(df)
    for alias in aliases:
        key = _column_key(alias)
        if key in columns:
            return columns[key]
    raise ValueError(f"Source tab {tab_name!r} is missing required column for {output_name!r}.")


def parse_month_year(month_value: Any, year_value: Any = "") -> tuple[str, int]:
    month_text = str(month_value).strip()
    year_text = str(year_value).strip()
    if not month_text:
        raise ValueError("blank month")

    if year_text:
        month_key = month_text.lower()
        if month_key not in MONTH_LOOKUP:
            raise ValueError(f"invalid month {month_text!r}")
        return MONTH_LOOKUP[month_key], int(float(year_text))

    match = re.match(r"^([A-Za-z]+)\s+(\d{4})$", month_text)
    if not match:
        raise ValueError(f"invalid combined month/year {month_text!r}")
    month_key = match.group(1).lower()
    if month_key not in MONTH_LOOKUP:
        raise ValueError(f"invalid month {match.group(1)!r}")
    return MONTH_LOOKUP[month_key], int(match.group(2))


def _coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for column in NUMERIC_OUTPUT_COLUMNS:
        cleaned = df[column].astype(str).str.replace(r"[$€,]", "", regex=True).str.strip()
        df[column] = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)
    df["Year"] = pd.to_numeric(df["Year"], errors="raise").astype(int)
    return df


def normalize_source_sheet(df: pd.DataFrame, source_kind: str, tab_name: str) -> pd.DataFrame:
    """Normalize one consolidated source tab into the report-sheet shape."""
    if df.empty:
        return pd.DataFrame(columns=REPORT_HEADERS)
    if source_kind not in {"campaigns", "ads"}:
        raise ValueError(f"Unsupported source kind: {source_kind}")

    source_col = _find_column(df, ["Campaign"] if source_kind == "campaigns" else ["Ad Name"], tab_name, "Source")
    source_link_col = _find_column(
        df,
        ["SourceLink"] if source_kind == "campaigns" else ["Campaign"],
        tab_name,
        "Source Link",
    )
    traffic_col = _find_column(df, ["Traffic source", "Traffic Source"], tab_name, "Traffic Source")
    clicks_col = _find_column(df, ["Clicks", "Click"], tab_name, "Click")
    month_col = _find_column(df, ["Month"], tab_name, "Month")
    year_col = _column_map(df).get(_column_key("Year"), "")

    periods: list[tuple[str, int]] = []
    parse_errors: list[str] = []
    for index, row in df.iterrows():
        try:
            periods.append(parse_month_year(row.get(month_col, ""), row.get(year_col, "") if year_col else ""))
        except Exception as exc:
            parse_errors.append(f"row {index + 2}: {exc}")
            periods.append(("", 0))
    if parse_errors:
        sample = "; ".join(parse_errors[:5])
        raise ValueError(f"Source tab {tab_name!r} has invalid Month/Year values: {sample}")

    aliases = {
        "Cost": ["Cost"],
        "Revenue": ["Revenue"],
        "Recurring Revenue": ["Recurring revenue", "Recurring Revenue"],
        "Sales": ["Sales"],
        "Leads": ["Leads"],
        "Total Revenue": ["Total Revenue"],
        "Impressions": ["Impressions"],
        "Average Order Value": ["Average Order Value"],
        "Client": ["Client"],
        "Funnel": ["Funnel"],
    }
    source_columns = {name: _find_column(df, candidates, tab_name, name) for name, candidates in aliases.items()}

    normalized = pd.DataFrame(
        {
            "Source": df[source_col],
            "Traffic Source": df[traffic_col],
            "Source Link": df[source_link_col],
            "Click": df[clicks_col],
            "Cost": df[source_columns["Cost"]],
            "Revenue": df[source_columns["Revenue"]],
            "Recurring Revenue": df[source_columns["Recurring Revenue"]],
            "Sales": df[source_columns["Sales"]],
            "Leads": df[source_columns["Leads"]],
            "Total Revenue": df[source_columns["Total Revenue"]],
            "Impressions": df[source_columns["Impressions"]],
            "Average Order Value": df[source_columns["Average Order Value"]],
            "Client": df[source_columns["Client"]],
            "Month": [month for month, _year in periods],
            "Year": [year for _month, year in periods],
            "Funnel": df[source_columns["Funnel"]],
        }
    )
    for column in ["Source", "Traffic Source", "Source Link", "Client", "Month", "Funnel"]:
        normalized[column] = normalized[column].astype(str).str.strip()
    normalized = normalized[normalized["Client"] != ""].copy()
    normalized = _coerce_numeric_columns(normalized)
    return normalized[REPORT_HEADERS].reset_index(drop=True)


def load_normalized_source(sheets_service, source_spreadsheet_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    campaigns = []
    ads = []
    for tab_name in SOURCE_CAMPAIGN_TABS:
        values = read_sheet_values(sheets_service, source_spreadsheet_id, tab_name)
        campaigns.append(normalize_source_sheet(values_to_dataframe(values), "campaigns", tab_name))
    for tab_name in SOURCE_AD_TABS:
        values = read_sheet_values(sheets_service, source_spreadsheet_id, tab_name)
        ads.append(normalize_source_sheet(values_to_dataframe(values), "ads", tab_name))
    return (
        pd.concat(campaigns, ignore_index=True) if campaigns else pd.DataFrame(columns=REPORT_HEADERS),
        pd.concat(ads, ignore_index=True) if ads else pd.DataFrame(columns=REPORT_HEADERS),
    )


def _dedupe_client_rows(df: pd.DataFrame, client_name: str) -> tuple[pd.DataFrame, int]:
    client_rows = df[df["Client"].astype(str).str.strip() == client_name].copy()
    before = len(client_rows)
    client_rows = client_rows.drop_duplicates(subset=DEDUP_KEYS, keep="last")
    client_rows["_month_number"] = client_rows["Month"].astype(str).str.lower().map(
        {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
    )
    client_rows = client_rows.sort_values(
        ["Year", "_month_number", "Traffic Source", "Funnel", "Source"],
        kind="stable",
    ).drop(columns=["_month_number"])
    return client_rows[REPORT_HEADERS].reset_index(drop=True), before - len(client_rows)


def prepare_client_data(
    clients: list[ControlSheetClient],
    source_campaigns: pd.DataFrame,
    source_ads: pd.DataFrame,
) -> list[PreparedClientData]:
    prepared: list[PreparedClientData] = []
    missing: list[str] = []
    for client in clients:
        campaigns, campaign_dupes = _dedupe_client_rows(source_campaigns, client.client_name)
        ads, ad_dupes = _dedupe_client_rows(source_ads, client.client_name)
        if campaigns.empty or ads.empty:
            missing.append(
                f"{client.client_name} (campaigns={len(campaigns)}, ads={len(ads)})"
            )
            continue
        prepared.append(
            PreparedClientData(
                client=client,
                campaigns=campaigns,
                ads=ads,
                campaign_duplicates_removed=campaign_dupes,
                ad_duplicates_removed=ad_dupes,
            )
        )
    if missing:
        raise ValueError("Active clients missing source data: " + "; ".join(missing))
    return prepared


def _sheet_properties_by_title(sheets_service, spreadsheet_id: str) -> dict[str, dict[str, Any]]:
    metadata = _execute_with_retry(sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id))
    return {
        sheet["properties"]["title"]: sheet["properties"]
        for sheet in metadata.get("sheets", [])
        if "properties" in sheet
    }


def validate_destination_tabs(sheets_service, prepared: list[PreparedClientData]) -> None:
    missing: list[str] = []
    for item in prepared:
        properties = _sheet_properties_by_title(sheets_service, item.client.spreadsheet_id)
        for tab_name in [item.client.campaigns_tab, item.client.ads_tab]:
            if tab_name not in properties:
                missing.append(f"{item.client.client_name}: {tab_name}")
    if missing:
        raise ValueError("Destination client sheets are missing required tabs: " + "; ".join(missing))


def _backup_sheet(sheets_service, spreadsheet_id: str, sheet_name: str, timestamp: str) -> str:
    properties = _sheet_properties_by_title(sheets_service, spreadsheet_id)
    if sheet_name not in properties:
        raise ValueError(f"Destination sheet {spreadsheet_id} is missing tab {sheet_name!r}.")
    backup_name = f"{sheet_name} Backup {timestamp}"[:100]
    response = _execute_with_retry(
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "duplicateSheet": {
                            "sourceSheetId": properties[sheet_name]["sheetId"],
                            "newSheetName": backup_name,
                        }
                    }
                ]
            },
        )
    )
    backup_sheet_id = response["replies"][0]["duplicateSheet"]["properties"]["sheetId"]
    _execute_with_retry(
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {"sheetId": backup_sheet_id, "hidden": True},
                            "fields": "hidden",
                        }
                    }
                ]
            },
        )
    )
    return backup_name


def _ensure_grid_size(sheets_service, spreadsheet_id: str, sheet_name: str, row_count: int, column_count: int) -> None:
    properties = _sheet_properties_by_title(sheets_service, spreadsheet_id)
    if sheet_name not in properties:
        raise ValueError(f"Destination sheet {spreadsheet_id} is missing tab {sheet_name!r}.")
    sheet_properties = properties[sheet_name]
    grid_properties = sheet_properties.get("gridProperties", {})
    current_rows = int(grid_properties.get("rowCount", 0))
    current_columns = int(grid_properties.get("columnCount", 0))
    wanted_rows = max(current_rows, row_count)
    wanted_columns = max(current_columns, column_count)
    if wanted_rows == current_rows and wanted_columns == current_columns:
        return
    _execute_with_retry(
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": sheet_properties["sheetId"],
                                "gridProperties": {
                                    "rowCount": wanted_rows,
                                    "columnCount": wanted_columns,
                                },
                            },
                            "fields": "gridProperties(rowCount,columnCount)",
                        }
                    }
                ]
            },
        )
    )


def _dataframe_to_rows(df: pd.DataFrame) -> list[list[Any]]:
    rows = [REPORT_HEADERS]
    for row in df[REPORT_HEADERS].itertuples(index=False, name=None):
        rows.append([_json_safe_cell(value) for value in row])
    return rows


def _replace_values(sheets_service, spreadsheet_id: str, sheet_name: str, df: pd.DataFrame) -> None:
    rows = _dataframe_to_rows(df)
    _ensure_grid_size(sheets_service, spreadsheet_id, sheet_name, len(rows), len(REPORT_HEADERS))
    _execute_with_retry(
        sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"{quote_sheet_name(sheet_name)}!A:ZZ",
            body={},
        )
    )
    chunk_size = 5000
    for start in range(0, len(rows), chunk_size):
        chunk = rows[start : start + chunk_size]
        start_row = start + 1
        _execute_with_retry(
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{quote_sheet_name(sheet_name)}!A{start_row}",
                valueInputOption="USER_ENTERED",
                body={"values": chunk},
            )
        )


def _read_back_dataframe(sheets_service, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    values = read_sheet_values(sheets_service, spreadsheet_id, sheet_name, "A1:P")
    if not values or values[0] != REPORT_HEADERS:
        raise ValueError(f"Readback header mismatch in {spreadsheet_id}/{sheet_name}: {values[:1]}")
    return values_to_dataframe(values)


def _assert_totals_match(expected: pd.DataFrame, actual: pd.DataFrame, label: str) -> None:
    if set(actual["Client"].astype(str).str.strip()) != set(expected["Client"].astype(str).str.strip()):
        raise ValueError(f"{label} readback contains unexpected client values.")
    group_cols = ["Client", "Month", "Year"]
    expected_totals = expected.groupby(group_cols, dropna=False)[TOTAL_CHECK_COLUMNS].sum().sort_index()
    actual = _coerce_numeric_columns(actual[REPORT_HEADERS])
    actual_totals = actual.groupby(group_cols, dropna=False)[TOTAL_CHECK_COLUMNS].sum().sort_index()
    actual_totals = actual_totals.reindex(expected_totals.index, fill_value=0)
    unexpected = actual.groupby(group_cols, dropna=False).size().index.difference(expected_totals.index)
    if len(unexpected) > 0:
        raise ValueError(f"{label} readback contains unexpected periods: {list(unexpected)}")
    diff = (actual_totals[TOTAL_CHECK_COLUMNS] - expected_totals[TOTAL_CHECK_COLUMNS]).abs()
    if (diff > 0.000001).any().any():
        raise ValueError(f"{label} readback totals do not match source totals.")


def verify_client_write(sheets_service, item: PreparedClientData) -> None:
    campaigns = _read_back_dataframe(sheets_service, item.client.spreadsheet_id, item.client.campaigns_tab)
    ads = _read_back_dataframe(sheets_service, item.client.spreadsheet_id, item.client.ads_tab)
    _assert_totals_match(item.campaigns, campaigns, f"{item.client.client_name} Campaigns")
    _assert_totals_match(item.ads, ads, f"{item.client.client_name} Ads")


def summarize_prepared(item: PreparedClientData, status: str) -> BackfillSummary:
    periods = pd.concat([item.campaigns[["Month", "Year"]], item.ads[["Month", "Year"]]], ignore_index=True)
    periods = periods.drop_duplicates()
    periods["_month_number"] = periods["Month"].astype(str).str.lower().map(
        {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
    )
    periods = periods.sort_values(["Year", "_month_number"], kind="stable").drop(columns=["_month_number"])
    return BackfillSummary(
        client_key=item.client.client_key,
        client_name=item.client.client_name,
        spreadsheet_id=item.client.spreadsheet_id,
        campaign_source_rows=len(item.campaigns) + item.campaign_duplicates_removed,
        ad_source_rows=len(item.ads) + item.ad_duplicates_removed,
        campaigns_rows=len(item.campaigns),
        ads_rows=len(item.ads),
        months=[f"{row.Month} {int(row.Year)}" for row in periods.itertuples(index=False)],
        campaign_duplicates_removed=item.campaign_duplicates_removed,
        ad_duplicates_removed=item.ad_duplicates_removed,
        status=status,
    )


def backfill_client(sheets_service, item: PreparedClientData, timestamp: str) -> BackfillSummary:
    _backup_sheet(sheets_service, item.client.spreadsheet_id, item.client.campaigns_tab, timestamp)
    _backup_sheet(sheets_service, item.client.spreadsheet_id, item.client.ads_tab, timestamp)
    _replace_values(sheets_service, item.client.spreadsheet_id, item.client.campaigns_tab, item.campaigns)
    _replace_values(sheets_service, item.client.spreadsheet_id, item.client.ads_tab, item.ads)
    verify_client_write(sheets_service, item)
    return summarize_prepared(item, "written")


def run_backfill(args: argparse.Namespace, services: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_args(args)
    services = services or build_workspace_services()
    sheets_service = services["sheets"]
    source_spreadsheet_id = extract_file_id(args.source_sheet)
    control_spreadsheet_id = extract_file_id(args.control_sheet)
    clients = load_control_sheet_clients(
        sheets_service,
        control_spreadsheet_id,
        sheet_name=args.clients_sheet,
        active_only=True,
    )
    selected = select_control_sheet_clients(clients, args.run_mode, client_key=args.client_key)
    source_campaigns, source_ads = load_normalized_source(sheets_service, source_spreadsheet_id)
    prepared = prepare_client_data(selected, source_campaigns, source_ads)
    validate_destination_tabs(sheets_service, prepared)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summaries = []
    for item in prepared:
        if args.dry_run:
            summaries.append(summarize_prepared(item, "dry_run"))
        else:
            summaries.append(backfill_client(sheets_service, item, timestamp))
    return {
        "dry_run": bool(args.dry_run),
        "source_spreadsheet_id": source_spreadsheet_id,
        "control_spreadsheet_id": control_spreadsheet_id,
        "selected_clients": [item.client.client_key for item in prepared],
        "client_count": len(prepared),
        "summaries": [asdict(summary) for summary in summaries],
    }


def main() -> int:
    payload = run_backfill(parse_args())
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
