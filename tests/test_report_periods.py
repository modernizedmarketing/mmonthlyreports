from datetime import date

from tools.report_periods import default_reporting_window, resolve_reporting_window, shift_month


def test_shift_month_handles_year_boundaries():
    assert shift_month("January", 2026, -1) == ("December", 2025)
    assert shift_month("December", 2026, 1) == ("January", 2027)


def test_default_reporting_window_uses_previous_calendar_month():
    window = default_reporting_window(today=date(2026, 4, 21))

    assert window.month == "March"
    assert window.year == 2026
    assert window.prev_month == "February"
    assert window.next_month == "April"


def test_resolve_reporting_window_derives_prev_and_next_years():
    window = resolve_reporting_window("January", 2026)

    assert window.prev_month == "December"
    assert window.prev_year == 2025
    assert window.next_month == "February"
    assert window.next_year == 2026
