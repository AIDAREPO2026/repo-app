import json
import logging

from app.core.log_setup import JsonFormatter, redact


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


def test_p1_acc_05_link_tokens_are_removed_from_logged_addresses() -> None:
    line = 'GET /reset-password/s3cretT0ken_-x HTTP/1.1 and "/set-password/An0ther" 200'

    logged = redact(line)

    assert "s3cret" not in logged and "An0ther" not in logged
    assert "/reset-password/[removed] HTTP/1.1" in logged
