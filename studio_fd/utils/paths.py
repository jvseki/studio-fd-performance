"""Recursos distribuídos e dados persistentes têm raízes diferentes."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def resource_root() -> Path:
    # _MEIPASS será usado somente para recursos, nunca para dados do cliente.
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


@dataclass(frozen=True)
class AppPaths:
    root: Path

    @classmethod
    def default(cls) -> "AppPaths":
        override = os.environ.get("STUDIO_FD_DATA_DIR")
        if override:
            root = Path(override).expanduser()
            if not root.is_absolute():
                raise ValueError("STUDIO_FD_DATA_DIR deve ser um caminho absoluto.")
            return cls(root)
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / ".local" / "share"
        return cls(base / "StudioFDPerformance" / "data")

    @property
    def database(self) -> Path:
        return self.root / "studio_fd.db"

    @property
    def contracts(self) -> Path:
        return self.root / "contratos"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def settings(self) -> Path:
        return self.root / "configuracoes"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    def ensure_directories(self) -> None:
        for directory in (self.root, self.contracts, self.backups, self.settings, self.logs):
            directory.mkdir(parents=True, exist_ok=True)
