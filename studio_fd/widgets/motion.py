"""Movimento da interface: rolagem suave, transição de telas e avisos.

Tudo aqui é opcional para a lógica do programa: se uma animação for
interrompida, o estado final é aplicado na hora.
"""

from PySide6.QtCore import (
    QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QParallelAnimationGroup,
    QRectF, Qt, QTimer, QVariantAnimation,
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractScrollArea, QAbstractSpinBox, QApplication, QComboBox, QGraphicsOpacityEffect,
    QStackedWidget, QWidget,
)

from studio_fd.views import theme
from studio_fd.widgets.icons import pixmap


class SmoothScroller(QObject):
    """Transforma cada 'clique' da roda do mouse em um deslize animado.

    Touchpads (que já mandam pixels) continuam com a rolagem nativa. Quando a
    área chega ao fim, o evento segue para a área de fora, como no navegador.
    """

    STEP = 110
    DURATION = 340

    def __init__(self, area: QAbstractScrollArea):
        super().__init__(area)
        self.area = area
        self.target = None
        self.animation = QPropertyAnimation(area.verticalScrollBar(), b"value", self)
        self.animation.setDuration(self.DURATION)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self._done)
        area.viewport().installEventFilter(self)

    def _done(self) -> None:
        self.target = None

    def eventFilter(self, watched, event) -> bool:
        if event.type() != QEvent.Type.Wheel or event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return False
        if not event.pixelDelta().isNull() or event.angleDelta().y() == 0:
            return False
        bar = self.area.verticalScrollBar()
        steps = -event.angleDelta().y() / 120
        start = self.target if self.target is not None else bar.value()
        if (steps < 0 and start <= bar.minimum()) or (steps > 0 and start >= bar.maximum()):
            return False  # deixa a área externa rolar
        self.target = max(bar.minimum(), min(bar.maximum(), int(start + steps * self.STEP)))
        self.animation.stop()
        self.animation.setStartValue(bar.value())
        self.animation.setEndValue(self.target)
        self.animation.start()
        return True


def smooth(area: QAbstractScrollArea) -> QAbstractScrollArea:
    if getattr(area, "_smooth", None) is None:
        area._smooth = SmoothScroller(area)
    return area


class WheelGuard(QObject):
    """Evita mudar valores sem querer: campos numéricos e listas só reagem à
    roda do mouse quando estão com o foco (o usuário clicou neles)."""

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Wheel and isinstance(watched, (QAbstractSpinBox, QComboBox)) and not watched.hasFocus():
            event.ignore()
            return True
        return False


_GUARD = None


def install_wheel_guard(app: QApplication) -> None:
    global _GUARD
    if not isinstance(app, QObject):
        return  # testes que simulam o QApplication
    _GUARD = _GUARD or WheelGuard()
    app.installEventFilter(_GUARD)


class FadeStack(QStackedWidget):
    """QStackedWidget que entra com a nova tela em fade + leve subida."""

    DURATION = 260

    def __init__(self):
        super().__init__()
        self._group = None

    def setCurrentIndex(self, index: int) -> None:
        if index == self.currentIndex() or not self.isVisible():
            super().setCurrentIndex(index)
            return
        if self._group is not None:
            self._group.stop()
            self._finish()
        super().setCurrentIndex(index)
        page = self.currentWidget()
        effect = QGraphicsOpacityEffect(page)
        effect.setOpacity(0)
        page.setGraphicsEffect(effect)
        fade = QPropertyAnimation(effect, b"opacity", self)
        fade.setDuration(self.DURATION)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide = QPropertyAnimation(page, b"pos", self)
        slide.setDuration(self.DURATION + 60)
        slide.setStartValue(QPoint(0, 14))
        slide.setEndValue(QPoint(0, 0))
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.finished.connect(self._finish)
        self._group = group
        group.start()

    def _finish(self) -> None:
        page = self.currentWidget()
        if page is not None:
            page.setGraphicsEffect(None)  # sem efeito permanente: desenho mais leve
            page.move(0, 0)
        self._group = None


class HoverMixin:
    """Progresso de hover animado (0 → 1) para widgets pintados à mão."""

    def _setup_hover(self, duration: int = 160) -> None:
        self._hover = 0.0
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(duration)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_animation.valueChanged.connect(self._set_hover)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def _set_hover(self, value) -> None:
        self._hover = float(value)
        self.update()

    def _animate_hover(self, target: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover)
        self._hover_animation.setEndValue(target)
        self._hover_animation.start()

    def enterEvent(self, event) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)


def mix(first: str, second: str, amount: float) -> QColor:
    a, b = QColor(first), QColor(second)
    amount = max(0.0, min(1.0, amount))
    return QColor(round(a.red() + (b.red() - a.red()) * amount), round(a.green() + (b.green() - a.green()) * amount),
                  round(a.blue() + (b.blue() - a.blue()) * amount), round(a.alpha() + (b.alpha() - a.alpha()) * amount))


TOASTS = {"success": (theme.SUCCESS, "check"), "info": (theme.GOLD, "info"), "error": (theme.DANGER, "info")}


class Toast(QWidget):
    """Aviso discreto no canto inferior direito, que some sozinho."""

    def __init__(self, host: QWidget, text: str, tone: str = "success"):
        super().__init__(host)
        self.text = text
        self.color, self.icon_name = TOASTS.get(tone, TOASTS["info"])
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        font = QFont("Segoe UI")
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.DemiBold)
        self.font_ = font
        width = min(480, QFontMetrics(font).horizontalAdvance(text) + 80)
        self.resize(int(width), 52)
        self.effect = QGraphicsOpacityEffect(self)
        self.effect.setOpacity(0)
        self.setGraphicsEffect(self.effect)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.fillPath(path, QColor(theme.RAISED))
        painter.setPen(QPen(QColor(theme.BORDER_STRONG), 1))
        painter.drawPath(path)
        bar = QPainterPath()
        bar.addRoundedRect(QRectF(10, 14, 3, rect.height() - 28), 1.5, 1.5)
        painter.fillPath(bar, QColor(self.color))
        painter.drawPixmap(24, int(rect.height() / 2 - 9), pixmap(self.icon_name, self.color, 18))
        painter.setFont(self.font_)
        painter.setPen(QColor(theme.TEXT))
        painter.drawText(QRectF(52, 0, rect.width() - 64, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine, self.text)

    def popup(self, stack_index: int = 0) -> None:
        host = self.parentWidget()
        end = QPoint(host.width() - self.width() - 24, host.height() - self.height() - 24 - stack_index * 60)
        self.move(end + QPoint(0, 16))
        self.show()
        self.raise_()
        group = QParallelAnimationGroup(self)
        fade = QPropertyAnimation(self.effect, b"opacity", self)
        fade.setDuration(220)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        slide = QPropertyAnimation(self, b"pos", self)
        slide.setDuration(320)
        slide.setStartValue(self.pos())
        slide.setEndValue(end)
        slide.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.start()
        QTimer.singleShot(3200, self.dismiss)

    def dismiss(self) -> None:
        fade = QPropertyAnimation(self.effect, b"opacity", self)
        fade.setDuration(260)
        fade.setStartValue(self.effect.opacity())
        fade.setEndValue(0.0)
        fade.finished.connect(self.deleteLater)
        fade.start()


def toast(widget: QWidget | None, text: str, tone: str = "success") -> None:
    """Mostra um aviso na janela principal, de qualquer tela ou diálogo."""
    host = None
    for candidate in [widget.window() if widget is not None else None, *QApplication.topLevelWidgets()]:
        if candidate is not None and getattr(candidate, "toast_host", None) is not None and candidate.isVisible():
            host = candidate.toast_host
            break
    if host is None:
        return
    alive = [child for child in host.findChildren(Toast) if child.isVisible()]
    item = Toast(host, text, tone)
    item.popup(len(alive))
