import pandas as pd

from tools.google_sheet_report_data import (
    _json_safe_cell,
    filter_report_dataframe,
    flatten_kpis,
    quote_sheet_name,
    values_to_dataframe,
)


def test_values_to_dataframe_normalizes_numeric_columns():
    values = [
        ["Client", "Month", "Cost", "Total Revenue", "Sales"],
        ["One Funded", "March 2026", "1,234.50", "2500", "3"],
    ]

    df = values_to_dataframe(values)

    assert df.loc[0, "Client"] == "One Funded"
    assert df.loc[0, "Cost"] == 1234.50
    assert df.loc[0, "Total Revenue"] == 2500
    assert df.loc[0, "Sales"] == 3


def test_filter_report_dataframe_accepts_month_year_values():
    df = pd.DataFrame(
        [
            {"Client": "One Funded", "Month": "March 2026", "Cost": 1},
            {"Client": "One Funded", "Month": "February 2026", "Cost": 2},
            {"Client": "Other", "Month": "March 2026", "Cost": 3},
        ]
    )

    filtered = filter_report_dataframe(df, client="One Funded", month="March", year=2026)

    assert len(filtered) == 1
    assert filtered.iloc[0]["Cost"] == 1


def test_quote_sheet_name_escapes_single_quotes():
    assert quote_sheet_name("Owner's Data") == "'Owner''s Data'"


def test_flatten_kpis_uses_dot_paths():
    flat = flatten_kpis({"totals": {"roas": 2.1}, "google_top_ads": [{"source": "Ad A"}]})

    assert flat["totals.roas"] == 2.1
    assert flat["google_top_ads"].startswith("[")


def test_json_safe_cell_converts_numpy_scalars():
    value = pd.Series([3]).sum()

    assert _json_safe_cell(value) == 3
    assert isinstance(_json_safe_cell(value), int)
