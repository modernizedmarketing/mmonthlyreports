import argparse

import pandas as pd
import pytest

from tools.backfill_client_report_sheets import (
    REPORT_HEADERS,
    PreparedClientData,
    _assert_totals_match,
    backfill_client,
    normalize_source_sheet,
    parse_month_year,
    prepare_client_data,
    run_backfill,
)
from tools.control_sheet import ControlSheetClient


def _client(name="One Funded", key="one-funded", spreadsheet_id="sheet-1"):
    return ControlSheetClient(
        active=True,
        client_name=name,
        client_key=key,
        spreadsheet_id=spreadsheet_id,
        template_presentation_id="deck-1",
        output_folder_id="folder-1",
    )


def _campaign_source_rows():
    return pd.DataFrame(
        [
            {
                "Campaign": "TOF Campaign",
                "Traffic source": "google",
                "SourceLink": "TOF Link",
                "Clicks": "12",
                "Cost": "$34.50",
                "Revenue": "100",
                "Recurring revenue": "5",
                "Sales": "2",
                "Leads": "8",
                "Total Revenue": "105",
                "Impressions": "900",
                "Average Order Value": "52.5",
                "Client": "One Funded",
                "Month": "February 2026",
                "Funnel": "TOF",
            }
        ]
    )


def _ad_source_rows():
    return pd.DataFrame(
        [
            {
                "Ad Name": "Ad A",
                "Traffic source": "meta",
                "Campaign": "Source Campaign",
                "Clicks": "7",
                "Cost": "11",
                "Revenue": "42",
                "Recurring revenue": "0",
                "Sales": "1",
                "Leads": "3",
                "Total Revenue": "42",
                "Impressions": "100",
                "Average Order Value": "42",
                "Client": "One Funded",
                "Month": "March 2026",
                "Funnel": "BOF",
            }
        ]
    )


def test_parse_month_year_splits_combined_value():
    assert parse_month_year("February 2026") == ("February", 2026)
    assert parse_month_year("Mar", "2026") == ("March", 2026)


def test_normalize_campaign_source_sheet_matches_report_headers():
    df = normalize_source_sheet(_campaign_source_rows(), "campaigns", "Campaigns")

    assert list(df.columns) == REPORT_HEADERS
    assert df.loc[0, "Source"] == "TOF Campaign"
    assert df.loc[0, "Source Link"] == "TOF Link"
    assert df.loc[0, "Click"] == 12
    assert df.loc[0, "Month"] == "February"
    assert df.loc[0, "Year"] == 2026


def test_normalize_ad_source_sheet_uses_campaign_as_source_link():
    df = normalize_source_sheet(_ad_source_rows(), "ads", "Ads")

    assert df.loc[0, "Source"] == "Ad A"
    assert df.loc[0, "Source Link"] == "Source Campaign"
    assert df.loc[0, "Traffic Source"] == "meta"


def test_prepare_client_data_filters_active_clients_and_dedupes():
    duplicate_campaigns = pd.concat(
        [
            normalize_source_sheet(_campaign_source_rows(), "campaigns", "Backup Campaigns"),
            normalize_source_sheet(_campaign_source_rows(), "campaigns", "Campaigns"),
        ],
        ignore_index=True,
    )
    ads = normalize_source_sheet(_ad_source_rows(), "ads", "Ads")

    prepared = prepare_client_data([_client()], duplicate_campaigns, ads)

    assert len(prepared) == 1
    assert len(prepared[0].campaigns) == 1
    assert prepared[0].campaign_duplicates_removed == 1


def test_prepare_client_data_fails_when_active_client_has_no_rows():
    campaigns = normalize_source_sheet(_campaign_source_rows(), "campaigns", "Campaigns")
    ads = normalize_source_sheet(_ad_source_rows(), "ads", "Ads")

    with pytest.raises(ValueError, match="Active clients missing source data"):
        prepare_client_data([_client(name="Missing Client", key="missing")], campaigns, ads)


class FakeRequest:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


class FakeValues:
    def __init__(self, api):
        self.api = api

    def clear(self, spreadsheetId, range, body):
        def run():
            sheet_name = range.split("!", 1)[0].strip("'").replace("''", "'")
            self.api.cleared.append((spreadsheetId, sheet_name))
            self.api.data[(spreadsheetId, sheet_name)] = []
            return {}

        return FakeRequest(run)

    def update(self, spreadsheetId, range, valueInputOption, body):
        def run():
            sheet_name = range.split("!", 1)[0].strip("'").replace("''", "'")
            self.api.updated.append((spreadsheetId, sheet_name, body["values"]))
            self.api.data[(spreadsheetId, sheet_name)] = body["values"]
            return {}

        return FakeRequest(run)

    def get(self, spreadsheetId, range):
        def run():
            sheet_name = range.split("!", 1)[0].strip("'").replace("''", "'")
            return {"values": self.api.data.get((spreadsheetId, sheet_name), [])}

        return FakeRequest(run)


class FakeSpreadsheets:
    def __init__(self, api):
        self.api = api

    def get(self, spreadsheetId):
        def run():
            return {
                "sheets": [
                    {"properties": dict(properties)}
                    for properties in self.api.metadata[spreadsheetId].values()
                ]
            }

        return FakeRequest(run)

    def batchUpdate(self, spreadsheetId, body):
        def run():
            self.api.batch_requests.extend(body["requests"])
            request = body["requests"][0]
            if "duplicateSheet" in request:
                source = request["duplicateSheet"]
                new_id = self.api.next_sheet_id
                self.api.next_sheet_id += 1
                title = source["newSheetName"]
                self.api.metadata[spreadsheetId][title] = {"title": title, "sheetId": new_id}
                return {"replies": [{"duplicateSheet": {"properties": {"sheetId": new_id, "title": title}}}]}
            if "updateSheetProperties" in request:
                update_properties = request["updateSheetProperties"]["properties"]
                sheet_id = update_properties["sheetId"]
                for properties in self.api.metadata[spreadsheetId].values():
                    if properties["sheetId"] == sheet_id:
                        if "hidden" in update_properties:
                            properties["hidden"] = update_properties["hidden"]
                        if "gridProperties" in update_properties:
                            properties["gridProperties"] = update_properties["gridProperties"]
                return {"replies": [{}]}
            return {"replies": [{}]}

        return FakeRequest(run)

    def values(self):
        return FakeValues(self.api)


class FakeSheets:
    def __init__(self):
        self.metadata = {
            "sheet-1": {
                "Campaigns": {"title": "Campaigns", "sheetId": 1, "gridProperties": {"rowCount": 1000, "columnCount": 23}},
                "Ads": {"title": "Ads", "sheetId": 2, "gridProperties": {"rowCount": 1000, "columnCount": 23}},
            }
        }
        self.data = {}
        self.cleared = []
        self.updated = []
        self.batch_requests = []
        self.next_sheet_id = 100

    def spreadsheets(self):
        return FakeSpreadsheets(self)


def test_backfill_client_creates_hidden_backups_and_replaces_tabs():
    sheets = FakeSheets()
    campaigns = normalize_source_sheet(_campaign_source_rows(), "campaigns", "Campaigns")
    ads = normalize_source_sheet(_ad_source_rows(), "ads", "Ads")
    item = PreparedClientData(_client(), campaigns, ads, 0, 0)

    summary = backfill_client(sheets, item, "20260428T010203Z")

    assert summary.status == "written"
    assert ("sheet-1", "Campaigns") in sheets.cleared
    assert ("sheet-1", "Ads") in sheets.cleared
    assert sheets.data[("sheet-1", "Campaigns")][0] == REPORT_HEADERS
    assert sheets.metadata["sheet-1"]["Campaigns Backup 20260428T010203Z"]["hidden"] is True
    assert sheets.metadata["sheet-1"]["Ads Backup 20260428T010203Z"]["hidden"] is True


def test_backfill_client_expands_grid_before_large_write():
    sheets = FakeSheets()
    campaigns = normalize_source_sheet(_campaign_source_rows(), "campaigns", "Campaigns")
    ads = pd.concat([normalize_source_sheet(_ad_source_rows(), "ads", "Ads")] * 1001, ignore_index=True)
    item = PreparedClientData(_client(), campaigns, ads, 0, 1000)

    backfill_client(sheets, item, "20260428T010203Z")

    assert sheets.metadata["sheet-1"]["Ads"]["gridProperties"]["rowCount"] == 1002


def test_assert_totals_match_accepts_equivalent_numeric_dtypes():
    expected = normalize_source_sheet(_campaign_source_rows(), "campaigns", "Campaigns")
    actual = expected.copy()
    actual["Click"] = actual["Click"].astype(int)
    actual["Year"] = actual["Year"].astype(float)

    _assert_totals_match(expected, actual, "One Funded Campaigns")


def test_run_backfill_dry_run_does_not_write(monkeypatch):
    sheets = FakeSheets()
    client = _client()
    campaigns = normalize_source_sheet(_campaign_source_rows(), "campaigns", "Campaigns")
    ads = normalize_source_sheet(_ad_source_rows(), "ads", "Ads")

    monkeypatch.setattr("tools.backfill_client_report_sheets.extract_file_id", lambda value: value)
    monkeypatch.setattr("tools.backfill_client_report_sheets.load_control_sheet_clients", lambda *args, **kwargs: [client])
    monkeypatch.setattr("tools.backfill_client_report_sheets.load_normalized_source", lambda *args, **kwargs: (campaigns, ads))

    payload = run_backfill(
        argparse.Namespace(
            source_sheet="source",
            control_sheet="control",
            clients_sheet="Clients",
            run_mode="all",
            client_key="",
            dry_run=True,
        ),
        services={"sheets": sheets},
    )

    assert payload["dry_run"] is True
    assert payload["client_count"] == 1
    assert sheets.cleared == []
    assert sheets.updated == []
