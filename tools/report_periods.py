"""Helpers for resolving monthly reporting windows."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
MONTH_LOOKUP = {month.lower(): index + 1 for index, month in enumerate(MONTH_NAMES)}


@dataclass(frozen=True)
class ReportingWindow:
    month: str
    year: int
    prev_month: str
    prev_year: int
    next_month: str
    next_year: int


def normalize_month_name(value: str) -> str:
    month_number = month_name_to_number(value)
    return MONTH_NAMES[month_number - 1]


def month_name_to_number(value: str) -> int:
    key = str(value).strip().lower()
    if key not in MONTH_LOOKUP:
        raise ValueError(f"Unsupported month value: {value!r}")
    return MONTH_LOOKUP[key]


def shift_month(month: str, year: int, delta: int) -> tuple[str, int]:
    month_number = month_name_to_number(month)
    absolute = (int(year) * 12) + (month_number - 1) + delta
    shifted_year, shifted_month_index = divmod(absolute, 12)
    return MONTH_NAMES[shifted_month_index], shifted_year


def default_reporting_window(today: date | None = None) -> ReportingWindow:
    today = today or date.today()
    current_month = MONTH_NAMES[today.month - 1]
    report_month, report_year = shift_month(current_month, today.year, -1)
    prev_month, prev_year = shift_month(report_month, report_year, -1)
    next_month, next_year = shift_month(report_month, report_year, 1)
    return ReportingWindow(
        month=report_month,
        year=report_year,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
    )


def resolve_reporting_window(
    month: str | None,
    year: int | None,
    prev_month: str | None = None,
    prev_year: int | None = None,
    next_month: str | None = None,
    next_year: int | None = None,
    today: date | None = None,
) -> ReportingWindow:
    if month is None or year is None:
        default_window = default_reporting_window(today=today)
        month = month or default_window.month
        year = int(year or default_window.year)

    normalized_month = normalize_month_name(month)
    resolved_prev_month, resolved_prev_year = shift_month(normalized_month, int(year), -1)
    resolved_next_month, resolved_next_year = shift_month(normalized_month, int(year), 1)

    return ReportingWindow(
        month=normalized_month,
        year=int(year),
        prev_month=normalize_month_name(prev_month) if prev_month else resolved_prev_month,
        prev_year=int(prev_year) if prev_year is not None else resolved_prev_year,
        next_month=normalize_month_name(next_month) if next_month else resolved_next_month,
        next_year=int(next_year) if next_year is not None else resolved_next_year,
    )
