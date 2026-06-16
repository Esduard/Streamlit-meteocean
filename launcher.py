"""
PyInstaller entry point for MeteoceanForecast.

Spawns `streamlit run` as a subprocess (rather than calling Streamlit's
programmatic API in-process) so a crash or version mismatch inside Streamlit
cannot take down the launcher itself, then opens the default browser once
the server has had time to start.

When frozen, there is no separate `streamlit` executable on PATH inside the
bundle, so the launcher re-invokes its own executable with a sentinel CLI
flag; the child process detects the flag and runs the bundled Streamlit CLI
in-process instead of restarting the launcher loop.
"""

from __future__ import annotations

import logging
import socket
import subprocess
import sys
import threading
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "streamlitapp" / "src"))

from meteocean_forecast import path_utils  # noqa: E402

# Home.py and the page scripts are loaded dynamically by Streamlit at runtime, which
# PyInstaller's static import analysis can't see. Importing their dependencies here
# (from the one script PyInstaller does analyze) ensures the frozen bundle includes
# `meteocean_forecast` and plotly rather than failing at runtime with ModuleNotFoundError.
import plotly.graph_objects  # noqa: E402,F401
from meteocean_forecast.domain import forecast_request  # noqa: E402,F401
from meteocean_forecast.features import raw_xlsx_reader  # noqa: E402,F401
from meteocean_forecast.inference import forecasting_service  # noqa: E402,F401

_DEFAULT_PORT = 8501
_BROWSER_OPEN_DELAY_SECONDS = 2.0
_RUN_STREAMLIT_FLAG = "--run-streamlit-worker"

logger = logging.getLogger("launcher")


def _configure_logging() -> Path:
    """Rotate logs/launcher.log so the last 3 runs are retained, then attach it."""
    logs_dir = path_utils.get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "launcher.log"

    handler = RotatingFileHandler(log_path, backupCount=3)
    if log_path.exists() and log_path.stat().st_size > 0:
        handler.doRollover()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    return log_path


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("localhost", port))
        except OSError:
            return False
        return True


def _find_free_port() -> int:
    if _port_is_free(_DEFAULT_PORT):
        return _DEFAULT_PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        return sock.getsockname()[1]


def _internal_root() -> Path:
    """Root that bundled (non-replaceable) app source lives under."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def _home_script_path() -> Path:
    return _internal_root() / "streamlitapp" / "app" / "Home.py"


def _build_streamlit_command(port: int, home_script: Path) -> list[str]:
    """Build the `streamlit run` argv.

    There is no `--global.configDir` CLI flag in installed Streamlit versions
    (checked against 1.57.0): config files are discovered via `${cwd}/.streamlit/`.
    `main()` spawns this command with `cwd` set to `path_utils.get_base_dir()` so
    Streamlit picks up the bundled `.streamlit/config.toml` automatically.
    """
    streamlit_args = [
        "run",
        str(home_script),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    if getattr(sys, "frozen", False):
        # Streamlit infers global.developmentMode from whether its own __file__
        # contains "site-packages" — true for a PyInstaller bundle's extracted
        # path — and refuses to honor --server.port while that's set.
        streamlit_args += ["--global.developmentMode", "false"]
        return [sys.executable, _RUN_STREAMLIT_FLAG, *streamlit_args]
    return [sys.executable, "-m", "streamlit", *streamlit_args]


def _run_streamlit_worker_if_requested() -> bool:
    """If invoked as the re-exec'd streamlit worker, run Streamlit's CLI and exit."""
    if _RUN_STREAMLIT_FLAG not in sys.argv:
        return False

    from streamlit.web import cli as st_cli

    sys.argv = ["streamlit", *[arg for arg in sys.argv[1:] if arg != _RUN_STREAMLIT_FLAG]]
    sys.exit(st_cli.main())


def _schedule_browser_open(port: int) -> threading.Timer:
    timer = threading.Timer(_BROWSER_OPEN_DELAY_SECONDS, webbrowser.open, args=(f"http://localhost:{port}",))
    timer.start()
    return timer


def main() -> int:
    _run_streamlit_worker_if_requested()

    _configure_logging()
    logger.info("Starting MeteoceanForecast launcher")

    port = _find_free_port()
    logger.info("Selected port %d", port)

    command = _build_streamlit_command(port, _home_script_path())
    base_dir = path_utils.get_base_dir()
    logger.info("Spawning Streamlit: %s (cwd=%s)", command, base_dir)
    process = subprocess.Popen(command, cwd=str(base_dir))

    _schedule_browser_open(port)

    exit_code = process.wait()
    logger.info("Streamlit process exited with code %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
