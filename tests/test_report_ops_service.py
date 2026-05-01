import io
import json

from tools.report_ops_service import build_app, render_dashboard_html


def _call_app(app, method="GET", path="/", body=b"", content_type="application/x-www-form-urlencoded", accept="text/html"):
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
        "HTTP_ACCEPT": accept,
    }
    response = b"".join(app(environ, start_response)).decode("utf-8")
    return captured["status"], dict(captured["headers"]), response


def test_render_dashboard_html_lists_clients():
    html = render_dashboard_html([{"client_key": "one-funded", "client_name": "One Funded"}])

    assert "One Funded" in html
    assert "Launch run" in html


def test_build_app_post_runs_returns_json():
    class Launcher:
        def launch(self, payload):
            assert payload["RUN_MODE"] == "one"
            assert payload["CLIENT_KEY"] == "one-funded"
            return {"name": "operations/123"}

    app = build_app(lambda: [{"client_key": "one-funded", "client_name": "One Funded"}], Launcher())
    body = json.dumps(
        {
            "run_mode": "one",
            "client_key": "one-funded",
            "month": "March",
            "year": "2026",
            "insights_provider": "deterministic",
        }
    ).encode("utf-8")

    status, headers, response = _call_app(
        app,
        method="POST",
        path="/runs",
        body=body,
        content_type="application/json",
        accept="application/json",
    )

    payload = json.loads(response)
    assert status == "202 Accepted"
    assert headers["Content-Type"] == "application/json"
    assert payload["status"] == "queued"
    assert payload["operation"] == "operations/123"
