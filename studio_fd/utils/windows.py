"""Identificação do aplicativo na barra de tarefas do Windows."""

import ctypes
import logging
import sys


APP_USER_MODEL_ID = "StudioFDPerformance.Desktop"


def identify_windows_app() -> None:
    if sys.platform != "win32":
        return
    try:
        shell = ctypes.WinDLL("shell32", use_last_error=True)
        identify = shell.SetCurrentProcessExplicitAppUserModelID
        identify.argtypes = [ctypes.c_wchar_p]
        identify.restype = ctypes.c_long
        result = identify(APP_USER_MODEL_ID)
        if result < 0:
            raise OSError(f"AppUserModelID: HRESULT {result & 0xFFFFFFFF:08X}")
    except OSError:
        # Uma falha visual não deve impedir o acesso aos cadastros.
        logging.getLogger(__name__).warning("Não foi possível definir o ícone na barra de tarefas", exc_info=True)
