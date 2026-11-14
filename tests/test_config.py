"""Tests of the .env loader in ``config``."""

import os

from earth_trail_detective.config import PROJECT_ROOT, load_env_file

KEYS = (
    "ETD_TEST_PLAIN",
    "ETD_TEST_QUOTED",
    "ETD_TEST_EXPORT",
    "ETD_TEST_COMMENT",
    "ETD_TEST_EMPTY",
    "ETD_TEST_SHELL",
)


def _clear(monkeypatch) -> None:
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)


def test_env_file_is_parsed(tmp_path, monkeypatch):
    _clear(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# a comment\n"
        "\n"
        "ETD_TEST_PLAIN=abc\n"
        'ETD_TEST_QUOTED="a b=c"\n'
        "export ETD_TEST_EXPORT='xyz'\n"
        "ETD_TEST_COMMENT=value # note\n"
        "ETD_TEST_EMPTY=\n"
        "not a variable\n",
        encoding="utf-8",
    )
    load_env_file(env_file)
    assert os.environ["ETD_TEST_PLAIN"] == "abc"
    assert os.environ["ETD_TEST_QUOTED"] == "a b=c"
    assert os.environ["ETD_TEST_EXPORT"] == "xyz"
    assert os.environ["ETD_TEST_COMMENT"] == "value"
    assert "ETD_TEST_EMPTY" not in os.environ
    for key in KEYS:  # leave the environment clean for other tests
        os.environ.pop(key, None)


def test_shell_variable_wins(tmp_path, monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("ETD_TEST_SHELL", "from-shell")
    env_file = tmp_path / ".env"
    env_file.write_text("ETD_TEST_SHELL=from-file\n", encoding="utf-8")
    load_env_file(env_file)
    assert os.environ["ETD_TEST_SHELL"] == "from-shell"


def test_missing_file_is_ignored(tmp_path):
    load_env_file(tmp_path / "does-not-exist")


def test_example_file_sets_nothing(monkeypatch):
    """The committed template has an empty token and only commented options."""
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    load_env_file(PROJECT_ROOT / ".env.example")
    assert "EARTHDATA_TOKEN" not in os.environ
