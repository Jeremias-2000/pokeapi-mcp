import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.mcp.infra.logging import LOGGING_CONF, load_logging_config
from app.mcp.infra.logging.json_formatter import JsonFormatter


def test_load_logging_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_logging_config(tmp_path / "missing.conf")


def test_logging_conf_exists() -> None:
    assert LOGGING_CONF.is_file()


def test_json_formatter_includes_request_id_when_present() -> None:
    record = logging.getLogger("tests.test_logging").makeRecord(
        name="tests.test_logging",
        level=logging.INFO,
        fn=__file__,
        lno=0,
        msg="with request",
        args=(),
        exc_info=None,
        extra={"request_id": "42"},
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == "42"
    assert payload["message"] == "with request"


def test_json_formatter_includes_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.getLogger("tests.test_logging").makeRecord(
            "tests.test_logging", logging.ERROR, __file__, 0, "failed", (), sys.exc_info()
        )
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]
