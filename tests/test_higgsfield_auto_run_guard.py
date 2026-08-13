import os
import sys
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.enable_higgsfield_once import main


def test_main_creates_flag_file(tmp_path, monkeypatch):
    flag_path = str(tmp_path / ".higgsfield_auto_once")
    monkeypatch.setattr("scripts.enable_higgsfield_once.HIGGSFIELD_ONESHOT_FLAG_PATH", flag_path)

    main()

    assert os.path.exists(flag_path)


def test_main_overwrites_existing_flag_file(tmp_path, monkeypatch):
    flag_path = str(tmp_path / ".higgsfield_auto_once")
    with open(flag_path, "w", encoding="utf-8") as f:
        f.write("stale")
    monkeypatch.setattr("scripts.enable_higgsfield_once.HIGGSFIELD_ONESHOT_FLAG_PATH", flag_path)

    main()

    with open(flag_path, encoding="utf-8") as f:
        assert f.read() == ""
