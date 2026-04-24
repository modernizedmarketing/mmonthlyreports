"""Google Sheets data layer for monthly marketing reports."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from googleapiclient.errors import HttpError

NUMERIC_COLUMNS = [
    "Cost",
    "Total Revenue",
    "Sales",
    "Leads",
    "Impressions",
    "Click",
    "Average Order Value",
]


def _execute_with_retry(request, attempts: int = 3, delay_seconds: float = 1.0):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return request.execute()
        except TimeoutError as exc:
            last_error = exc
            if attempt == attempts:
                raise
            time.sleep(delay_seconds * attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Request execution failed without raising an exception.")


def _json_safe_cell(value: Any) -> Any:
    """Convert pandas/numpy scalar values into JSON-safe Sheet cell values."""
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


def quote_sheet_name(sheet_name: str) -> str:
    escaped = sheet_name.replace("'", "''")
    return f"'{escaped}'"


def values_to_dataframe(values: list[list[Any]]) -> pd.DataFrame:
    """Convert a Sheets values payload into a normalized DataFrame."""
    if not values:
        return pd.DataFrame()

    header = [str(col).strip() for col in values[0]]
    width = len(header)
    rows = []
    for row in values[1:]:
        padded = list(row[:width]) + [""] * max(0, width - len(row))
        rows.append(padded)

    df = pd.DataFrame(rows, columns=header)
    df = df.dropna(how="all")
    if not df.empty:
        df = df.loc[:, [col for col in df.columns if str(col).strip()]]
    return normalize_report_dataframe(df)


def normalize_report_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Match the local xlsx loader's column cleanup and numeric coercion."""
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            cleaned = (
                df[col]
                .astype(str)
                .str.replace(r"[$€,]", "", regex=True)
                .str.strip()
            )
            df[col] = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)
    return df.reset_index(drop=True)


def filter_report_dataframe(
    df: pd.DataFrame,
    client: str | None = None,
    month: str | None = None,
    year: int | None = None,
) -> pd.DataFrame:
    """Filter by client and period when those columns are present."""
    filtered = df.copy()
    if client and "Client" in filtered.columns:
        filtered = filtered[filtered["Client"].astype(str).str.strip() == client].copy()
    if month and "Month" in filtered.columns:
        wanted = month.strip().lower()
        month_values = filtered["Month"].astype(str).str.strip().str.lower()
        allowed = {wanted}
        if year:
            allowed.add(f"{wanted} {int(year)}")
        filtered = filtered[month_values.isin(allowed)].copy()
    if year and "Year" in filtered.columns:
        years = pd.to_numeric(filtered["Year"], errors="coerce")
        filtered = filtered[years == int(year)].copy()
    return filtered.reset_index(drop=True)


def read_sheet_values(
    sheets_service,
    spreadsheet_id: str,
    sheet_name: str,
    cell_range: str = "A1:ZZ",
) -> list[list[Any]]:
    a1_range = f"{quote_sheet_name(sheet_name)}!{cell_range}"
    result = (
        sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=a1_range)
    )
    result = _execute_with_retry(result)
    return result.get("values", [])


def load_report_sheet(
    sheets_service,
    spreadsheet_id: str,
    sheet_name: str,
    client: str,
    month: str | None = None,
    year: int | None = None,
    cell_range: str = "A1:ZZ",
) -> pd.DataFrame:
    values = read_sheet_values(sheets_service, spreadsheet_id, sheet_name, cell_range)
    df = values_to_dataframe(values)
    return filter_report_dataframe(df, client=client, month=month, year=year)


def _normalize_key(value: str) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _parse_scalar(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text:
        return ""
    cleaned = text.replace("$", "").replace("€", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return text


def read_manual_inputs(
    sheets_service,
    spreadsheet_id: str,
    sheet_name: str,
    client: str,
    month: str,
    year: int,
) -> dict[str, Any]:
    """Read manual inputs from either a row table or key/value sheet.

    Supported shapes:
    - Columns like Client, Month, Year, company_revenue, ad_revenue, ad_cost.
    - Columns key/value, optionally with Client/Month/Year filters.
    """
    try:
        df = values_to_dataframe(read_sheet_values(sheets_service, spreadsheet_id, sheet_name))
    except HttpError as exc:
        if exc.resp.status in {400, 404}:
            return {}
        raise
    if df.empty:
        return {}

    normalized_columns = {_normalize_key(col): col for col in df.columns}
    has_key_value = "key" in normalized_columns and "value" in normalized_columns

    if has_key_value:
        scoped = filter_report_dataframe(df, client=client, month=month, year=year)
        if scoped.empty:
            scoped = df
        key_col = normalized_columns["key"]
        value_col = normalized_columns["value"]
        return {
            _normalize_key(row[key_col]): _parse_scalar(row[value_col])
            for _, row in scoped.iterrows()
            if str(row.get(key_col, "")).strip()
        }

    scoped = filter_report_dataframe(df, client=client, month=month, year=year)
    if scoped.empty:
        return {}

    row = scoped.iloc[0].to_dict()
    return {
        _normalize_key(key): _parse_scalar(value)
        for key, value in row.items()
        if _normalize_key(key) not in {"client", "month", "year"}
    }


def ensure_sheet_exists(sheets_service, spreadsheet_id: str, sheet_name: str) -> None:
    metadata = _execute_with_retry(
        sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id)
    )
    existing = {
        sheet["properties"]["title"]
        for sheet in metadata.get("sheets", [])
        if "properties" in sheet
    }
    if sheet_name in existing:
        return
    _execute_with_retry(
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
        )
    )


def write_table(
    sheets_service,
    spreadsheet_id: str,
    sheet_name: str,
    rows: list[list[Any]],
    start_cell: str = "A1",
    clear_first: bool = True,
) -> None:
    ensure_sheet_exists(sheets_service, spreadsheet_id, sheet_name)
    safe_rows = [[_json_safe_cell(value) for value in row] for row in rows]
    target = f"{quote_sheet_name(sheet_name)}!{start_cell}"
    if clear_first:
        _execute_with_retry(
            sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"{quote_sheet_name(sheet_name)}!A:ZZ",
                body={},
            )
        )
    _execute_with_retry(
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=target,
            valueInputOption="USER_ENTERED",
            body={"values": safe_rows},
        )
    )


def ensure_sheet_headers(
    sheets_service,
    spreadsheet_id: str,
    sheet_name: str,
    headers: list[str],
) -> None:
    ensure_sheet_exists(sheets_service, spreadsheet_id, sheet_name)
    existing = read_sheet_values(sheets_service, spreadsheet_id, sheet_name, "A1:Z1")
    if existing:
        return
    _execute_with_retry(
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{quote_sheet_name(sheet_name)}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [headers]},
        )
    )


def flatten_kpis(kpis: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested KPI dicts into stable dot-path keys for Sheets output."""
    flat: dict[str, Any] = {}

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(f"{prefix}.{key}" if prefix else str(key), child)
        elif isinstance(value, list):
            flat[prefix] = json.dumps(value, default=str)
        else:
            flat[prefix] = value

    walk("", kpis)
    return flat


def write_kpi_output(
    sheets_service,
    spreadsheet_id: str,
    kpis: dict[str, Any],
    sheet_name: str = "KPI Output",
) -> None:
    rows = [["metric_key", "value"]]
    rows.extend([[key, value] for key, value in sorted(flatten_kpis(kpis).items())])
    write_table(sheets_service, spreadsheet_id, sheet_name, rows)


def append_run_log(
    sheets_service,
    spreadsheet_id: str,
    row: dict[str, Any],
    sheet_name: str = "Run Log",
) -> None:
    ensure_sheet_exists(sheets_service, spreadsheet_id, sheet_name)
    headers = [
        "timestamp_utc",
        "client",
        "period",
        "status",
        "presentation_url",
        "pdf_path",
        "pptx_path",
        "remaining_placeholders",
        "validation_json",
    ]
    ensure_sheet_headers(sheets_service, spreadsheet_id, sheet_name, headers)
    values = [[row.get(header, "") for header in headers]]
    sheets_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{quote_sheet_name(sheet_name)}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def make_run_log_row(
    client: str,
    month: str,
    year: int,
    status: str,
    presentation_url: str = "",
    pdf_path: str = "",
    pptx_path: str = "",
    remaining_placeholders: list[str] | None = None,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "client": client,
        "period": f"{month} {year}",
        "status": status,
        "presentation_url": presentation_url,
        "pdf_path": pdf_path,
        "pptx_path": pptx_path,
        "remaining_placeholders": len(remaining_placeholders or []),
        "validation_json": json.dumps(validation or {}, default=str),
    }
