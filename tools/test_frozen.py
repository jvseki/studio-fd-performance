"""Teste real do .exe Windows com dados isolados, abertura e fechamento normal."""

import ctypes
from ctypes import wintypes
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import time


user32 = ctypes.WinDLL("user32", use_last_error=True)
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


def app_window(pid: int):
    windows = []

    @callback_type
    def visit(hwnd, _):
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value == pid:
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, len(title))
            if title.value == "Studio FD Performance":
                windows.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    return windows[0] if windows else None


def launch_and_close(executable: Path, data: Path) -> None:
    env = os.environ.copy()
    env["STUDIO_FD_DATA_DIR"] = str(data)
    env["QT_QPA_PLATFORM"] = "windows"
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen([str(executable)], cwd=str(data.parent), env=env, startupinfo=startup)
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            hwnd = app_window(process.pid)
            if hwnd:
                user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                if process.wait(timeout=10) != 0:
                    raise RuntimeError("O executável retornou erro ao fechar.")
                return
            if process.poll() is not None:
                raise RuntimeError(f"O executável encerrou antes de abrir a janela: {process.returncode}")
            time.sleep(0.1)
        raise RuntimeError("A janela principal não abriu em 30 segundos.")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


def main() -> None:
    executable = Path(sys.argv[1]).resolve(strict=True)
    with TemporaryDirectory(prefix="studio-fd-exe-") as directory:
        data = Path(directory) / "data"
        launch_and_close(executable, data)
        database = data / "studio_fd.db"
        with closing(sqlite3.connect(database)) as connection, connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0002"
            connection.execute("INSERT INTO students (full_name, phone, registered_on, active) VALUES ('Teste isolado', '', '2026-11-03', 1)")
        launch_and_close(executable, data)
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("SELECT count(*) FROM students").fetchone()[0] == 1
        log = (data / "logs" / "studio_fd.log").read_text(encoding="utf-8")
        assert "ERROR" not in log and "Traceback" not in log, log
        print("OK: executavel abriu e fechou duas vezes; migracao, integridade e persistencia verificadas.")


if __name__ == "__main__":
    main()
