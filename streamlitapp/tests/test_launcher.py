"""Tests for the PyInstaller launcher entry point at the repo root."""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from unittest.mock import MagicMock

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import launcher  # noqa: E402


def _socket_mock(bind_raises: bool = False, ephemeral_port: int = 54321) -> MagicMock:
    sock = MagicMock()
    sock.__enter__.return_value = sock
    sock.__exit__.return_value = False
    if bind_raises:
        sock.bind.side_effect = OSError("address in use")
    sock.getsockname.return_value = ("localhost", ephemeral_port)
    return sock


# ---------------------------------------------------------------------------
# port selection
# ---------------------------------------------------------------------------


def test_find_free_port_uses_8501_when_free(monkeypatch):
    monkeypatch.setattr(launcher.socket, "socket", lambda *a, **k: _socket_mock())

    assert launcher._find_free_port() == 8501


def test_find_free_port_falls_back_when_8501_occupied(monkeypatch):
    calls = [_socket_mock(bind_raises=True), _socket_mock(ephemeral_port=54321)]
    monkeypatch.setattr(launcher.socket, "socket", lambda *a, **k: calls.pop(0))

    assert launcher._find_free_port() == 54321


# ---------------------------------------------------------------------------
# command construction
# ---------------------------------------------------------------------------


def test_streamlit_command_dev_mode(monkeypatch):
    monkeypatch.setattr(launcher.sys, "frozen", False, raising=False)

    command = launcher._build_streamlit_command(8501, Path("/repo/streamlitapp/app/Home.py"))

    assert command[0] == sys.executable
    assert command[1:4] == ["-m", "streamlit", "run"]
    assert str(Path("/repo/streamlitapp/app/Home.py")) in command
    assert "--server.port" in command and "8501" in command
    assert "--server.headless" in command and "true" in command


def test_streamlit_command_frozen_mode(monkeypatch):
    monkeypatch.setattr(launcher.sys, "frozen", True, raising=False)

    command = launcher._build_streamlit_command(8501, Path("/dist/streamlitapp/app/Home.py"))

    assert command[0] == sys.executable
    assert launcher._RUN_STREAMLIT_FLAG in command
    assert "run" in command


# ---------------------------------------------------------------------------
# main(): subprocess + browser scheduling
# ---------------------------------------------------------------------------


def test_main_spawns_subprocess_and_schedules_browser(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher.path_utils, "get_logs_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(launcher.path_utils, "get_base_dir", lambda: tmp_path)
    monkeypatch.setattr(launcher, "_find_free_port", lambda: 8501)
    monkeypatch.setattr(launcher.sys, "frozen", False, raising=False)

    popen_mock = MagicMock()
    popen_mock.return_value.wait.return_value = 0
    monkeypatch.setattr(launcher.subprocess, "Popen", popen_mock)

    timer_mock = MagicMock()
    monkeypatch.setattr(launcher.threading, "Timer", timer_mock)

    browser_open_mock = MagicMock()
    monkeypatch.setattr(launcher.webbrowser, "open", browser_open_mock)

    exit_code = launcher.main()

    assert exit_code == 0
    popen_mock.assert_called_once()
    called_command = popen_mock.call_args[0][0]
    assert "8501" in called_command
    assert popen_mock.call_args.kwargs["cwd"] == str(tmp_path)

    timer_mock.assert_called_once_with(launcher._BROWSER_OPEN_DELAY_SECONDS, browser_open_mock, args=("http://localhost:8501",))
    timer_mock.return_value.start.assert_called_once()
    browser_open_mock.assert_not_called()


def test_main_creates_logs_dir_and_writes_log(monkeypatch, tmp_path):
    logs_dir = tmp_path / "logs"
    monkeypatch.setattr(launcher.path_utils, "get_logs_dir", lambda: logs_dir)
    monkeypatch.setattr(launcher.path_utils, "get_base_dir", lambda: tmp_path)
    monkeypatch.setattr(launcher, "_find_free_port", lambda: 8501)
    monkeypatch.setattr(launcher.sys, "frozen", False, raising=False)
    popen_mock = MagicMock()
    popen_mock.return_value.wait.return_value = 0
    monkeypatch.setattr(launcher.subprocess, "Popen", popen_mock)
    monkeypatch.setattr(launcher.threading, "Timer", MagicMock())
    monkeypatch.setattr(launcher.webbrowser, "open", MagicMock())

    launcher.main()

    assert logs_dir.exists()
    assert (logs_dir / "launcher.log").exists()


# ---------------------------------------------------------------------------
# port-finding integration sanity check (real sockets, no mocking)
# ---------------------------------------------------------------------------


def test_find_free_port_real_socket_returns_bindable_port():
    port = launcher._find_free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", port))
