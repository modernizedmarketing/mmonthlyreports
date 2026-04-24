from tools.google_sheet_report_data import make_run_log_row


def test_make_run_log_row_handles_empty_optional_values():
    row = make_run_log_row("One Funded", "March", 2026, "ok")

    assert row["remaining_placeholders"] == 0
    assert row["validation_json"] == "{}"
