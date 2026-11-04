"""Gera o ícone tipográfico provisório FD; não substitui a logo original."""

import os
from pathlib import Path
import struct

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication


def main() -> None:
    app = QApplication.instance() or QApplication([])
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "georgia.ttf"
    QFontDatabase.addApplicationFont(str(font_path))
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = []
    for size in sizes:
        canvas = QImage(size, size, QImage.Format.Format_ARGB32)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setBrush(QColor("#111214"))
        painter.setPen(QPen(QColor("#a68d5d"), max(1, size / 64)))
        painter.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), size / 6, size / 6)
        font = QFont("Georgia")
        font.setPixelSize(round(size * 0.52))
        painter.setFont(font)
        painter.setPen(QColor("#d6b776"))
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "FD")
        painter.end()
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        canvas.save(buffer, "PNG")
        images.append(bytes(buffer.data()))
    header = struct.pack("<HHH", 0, 1, len(sizes))
    entries = bytearray()
    offset = 6 + 16 * len(sizes)
    for size, png in zip(sizes, images):
        entries.extend(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset))
        offset += len(png)
    target = Path(__file__).resolve().parents[1] / "assets" / "app.ico"
    target.write_bytes(header + entries + b"".join(images))
    print(target)


if __name__ == "__main__":
    main()
