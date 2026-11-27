import json
import logging

from app.core.log_setup import JsonFormatter


def format_record(message: str, **extra: object) -> dict[str, object]:
    record = logging.makeLogRecord({"msg": message, "levelname": "INFO", "name": "test", **extra})
    return json.loads(JsonFormatter().format(record))  # type: ignore[no-any-return]


def test_p0_set_02_logs_remove_auth_headers() -> None:
    entry = format_record(
        "request Cookie: session=abc; other=def",
        headers={"Authorization": "Bearer secret-token", "Set-Cookie": "session=abc", "Accept": "text/html"},
    )

    assert "abc" not in json.dumps(entry)
    assert "secret-token" not in json.dumps(entry)
    assert entry["headers"] == {
        "Authorization": "[removed]",
        "Set-Cookie": "[removed]",
        "Accept": "text/html",
    }


def test_p0_set_02_logs_are_json_lines() -> None:
    entry = format_record("hello", item_id=7)

    assert entry["message"] == "hello"
    assert entry["level"] == "INFO"
    assert entry["item_id"] == 7
