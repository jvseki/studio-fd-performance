"""Monta o vídeo da versão web (celular) a partir de tools/gravar.mjs.

Legendas, celular desenhado, marcas de toque, trilha original e sons de toque
e de confirmação gerados aqui mesmo (nada de áudio de terceiros).

Uso (Python do projeto desktop, que já tem PySide6, numpy e ffmpeg):
  ..\\..\\.venv\\Scripts\\python.exe tools\\montar_video.py [--preview]
"""

import json
import math
import os
from pathlib import Path
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[2]  # versão-web
DESKTOP = ROOT.parent
sys.path.insert(0, str(DESKTOP / "build/video-tools"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import numpy as np  # noqa: E402
from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

W, H, FPS = 1920, 1080, 30
GOLD = QColor("#C9A96B")
BG = QColor("#0B0B0C")
OUT = ROOT / "video"
log = json.loads((OUT / "roteiro.json").read_text(encoding="utf-8"))

CAPTIONS = {
    "inicio": ("1 · Início", "O dia do Studio na palma da mão.", "Alunos ativos, agenda de hoje, recebidos e atrasos."),
    "agenda": ("2 · Agenda", "Douglas e Fran lado a lado.", "Toque numa vaga livre para agendar."),
    "agendado": ("2 · Agenda", "Horário fixo em um toque.", "O aluno já fica marcado nas próximas semanas."),
    "alunos": ("3 · Alunos", "Ache qualquer aluno na hora.", "Digite parte do nome e pronto."),
    "ficha": ("3 · Alunos", "A ficha completa do aluno.", "Plano, mensalidades e anamnese em PDF."),
    "mensalidades": ("4 · Mensalidades", "Quem pagou e quem atrasou.", "Tudo separado por mês, sem planilha."),
    "pagar": ("4 · Mensalidades", "Recebeu? Registre em segundos.", "Escolha a forma: Pix, dinheiro ou cartão."),
    "pago": ("4 · Mensalidades", "Pagamento registrado.", "E o valor já entra sozinho no caixa."),
    "caixa": ("5 · Caixa", "O caixa do dia sempre certo.", "Entradas, saídas e saldo."),
    "tema": ("6 · Do seu jeito", "Claro ou escuro.", "E no tablet instala como um app."),
}
ORDEM = ["inicio", "agenda", "alunos", "mensalidades", "caixa", "tema"]
GRUPO = {"agendado": "agenda", "ficha": "alunos", "pagar": "mensalidades", "pago": "mensalidades"}
SUCESSO = ("agendado", "pago")  # momentos com o som de confirmação

INTRO, OUTRO, GAP = 3.6, 4.8, 0.6
phone_frames = log["frames"]
p0 = phone_frames[0]["t"]
phone_len = log["marks"][-1]["t"] - p0
desk_frames: list = []
d0 = 0.0
desk_len = 0.0
SEG_PHONE = INTRO
SEG_DESK = SEG_PHONE + phone_len + GAP
SEG_OUTRO = SEG_DESK
TOTAL = SEG_OUTRO + OUTRO
cache: dict[str, QImage] = {}


def ease(v: float) -> float:
    v = max(0.0, min(1.0, v))
    return v * v * (3 - 2 * v)


def out_cubic(v: float) -> float:
    v = max(0.0, min(1.0, v))
    return 1 - (1 - v) ** 3


def frame_for(frames, start: float, t: float) -> QImage:
    target = start + t
    low, high = 0, len(frames) - 1
    while low < high:
        mid = (low + high + 1) // 2
        if frames[mid]["t"] <= target:
            low = mid
        else:
            high = mid - 1
    path = str(ROOT / frames[low]["file"])
    if path not in cache:
        if len(cache) > 40:
            cache.clear()
        cache[path] = QImage(path)
        if cache[path].isNull():
            raise ValueError(f"Quadro ausente ou inválido: {path}")
    return cache[path]


def font(size, weight=QFont.Weight.Normal, family="Segoe UI", italic=False, spacing=0.0):
    result = QFont(family)
    result.setPixelSize(int(size))
    result.setWeight(weight)
    result.setItalic(italic)
    if spacing:
        result.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return result


def text(p, rect, value, size, color, weight=QFont.Weight.Normal, family="Segoe UI", align=Qt.AlignmentFlag.AlignLeft, opacity=1.0, italic=False, spacing=0.0):
    p.save()
    p.setOpacity(opacity)
    p.setFont(font(size, weight, family, italic, spacing))
    p.setPen(QColor(color))
    p.drawText(QRectF(*rect), align | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, value)
    p.restore()


def background(p: QPainter, t: float) -> None:
    p.fillRect(QRectF(0, 0, W, H), BG)
    glow = QRadialGradient(QPointF(W * 0.7 + 50 * math.sin(t / 6), -100), 1200)
    glow.setColorAt(0, QColor(201, 169, 107, 24))
    glow.setColorAt(1, QColor(201, 169, 107, 0))
    p.fillRect(QRectF(0, 0, W, H), glow)


def wordmark(p: QPainter, t: float, closing: bool) -> None:
    reveal = out_cubic(t / 1.2)
    text(p, (0, 360 - 14 * (1 - reveal), W, 60), "STUDIO FD PERFORMANCE", 20, GOLD.name(), QFont.Weight.Bold, align=Qt.AlignmentFlag.AlignHCenter, opacity=reveal, spacing=7)
    if closing:
        text(p, (0, 430, W, 120), "Teste você mesma:", 92, "#F3F1EC", family="Instrument Serif", align=Qt.AlignmentFlag.AlignHCenter, opacity=ease((t - 0.3) / 0.8))
        text(p, (0, 530, W, 120), "studio-fd-demo.onrender.com", 76, GOLD.name(), family="Instrument Serif", align=Qt.AlignmentFlag.AlignHCenter, italic=True, opacity=ease((t - 0.6) / 0.8))
        text(p, (0, 700, W, 40), "Versão de teste com alunos fictícios · pode mexer à vontade", 21, "#8E8B84", align=Qt.AlignmentFlag.AlignHCenter, opacity=ease((t - 1.4) / 0.8))
    else:
        text(p, (0, 430, W, 120), "O Studio inteiro", 96, "#F3F1EC", family="Instrument Serif", align=Qt.AlignmentFlag.AlignHCenter, opacity=ease((t - 0.3) / 0.8))
        text(p, (0, 535, W, 120), "no celular e no tablet.", 96, GOLD.name(), family="Instrument Serif", align=Qt.AlignmentFlag.AlignHCenter, italic=True, opacity=ease((t - 0.55) / 0.8))
        text(p, (0, 705, W, 40), "Agenda · Alunos · Mensalidades · Caixa · versão web", 21, "#8E8B84", align=Qt.AlignmentFlag.AlignHCenter, opacity=ease((t - 1.2) / 0.8))


def current_caption(t_rel: float):
    key, since = "inicio", 0.0
    for mark in log["marks"]:
        offset = max(0.0, mark["t"] - p0 - 0.9)  # a legenda chega um pouco antes da tela
        if offset <= t_rel and mark["key"] in CAPTIONS:
            key, since = mark["key"], offset
    return key, since


def caption_block(p: QPainter, x: float, y: float, caption, appear: float, width=760) -> None:
    eyebrow, title, detail = caption
    shift = 22 * (1 - appear)
    p.setOpacity(appear)
    p.fillRect(QRectF(x, y + 18 + shift, 36 * appear, 2), GOLD)
    p.setOpacity(1)
    text(p, (x + 52, y + shift, width, 38), eyebrow.upper(), 18, GOLD.name(), QFont.Weight.Bold, opacity=appear, spacing=4)
    text(p, (x - 4, y + 54 + shift, width, 190), title, 76, "#F3F1EC", family="Instrument Serif", opacity=appear)
    text(p, (x, y + 250 + shift * 1.3, width - 60, 80), detail, 26, "#A9A6A0", opacity=out_cubic((appear - 0.25) / 0.75))


def phone_scene(p: QPainter, t: float) -> None:
    key, since = current_caption(t)
    caption = CAPTIONS[key]
    # troca de legenda: a anterior some e a nova sobe
    appear = out_cubic((t - since - 0.05) / 0.7) if since > 0 else out_cubic(t / 0.8)
    caption_block(p, 150, 330, caption, appear)
    steps = ORDEM
    index = steps.index(GRUPO.get(key, key))
    for i in range(len(steps)):
        p.setBrush(GOLD if i <= index else QColor("#2E2D2A"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(150 + i * 46, 760, 34, 4), 2, 2)

    # celular
    scale = 1.03
    sw, sh = 412 * scale, (892 + 44) * scale
    cx, top = 1290, (H - sh) / 2
    rise = 40 * (1 - out_cubic(t / 1.0))
    screen = QRectF(cx - sw / 2, top + rise, sw, sh)
    body = screen.adjusted(-14, -14, 14, 14)
    for spread in range(60, 0, -6):
        shadow = QPainterPath()
        shadow.addRoundedRect(body.adjusted(-spread, -spread + 30, spread, spread + 30), 64 + spread, 64 + spread)
        p.fillPath(shadow, QColor(0, 0, 0, 10))
    frame = QPainterPath()
    frame.addRoundedRect(body, 62, 62)
    gradient = QLinearGradient(body.topLeft(), body.bottomRight())
    gradient.setColorAt(0, QColor("#2A2824"))
    gradient.setColorAt(0.5, QColor("#141416"))
    gradient.setColorAt(1, QColor("#26241F"))
    p.fillPath(frame, gradient)
    p.setPen(QPen(QColor("#3B3324"), 1.5))
    p.drawPath(frame)
    clip = QPainterPath()
    clip.addRoundedRect(screen, 50, 50)
    p.save()
    p.setClipPath(clip)
    status = 44 * scale
    p.fillRect(screen, QColor("#0B0B0C"))
    page = QRectF(screen.left(), screen.top() + status, sw, sh - status)
    p.drawImage(page, frame_for(phone_frames, p0, t))
    text(p, (screen.left() + 34, screen.top() + 10, 80, 30), "9:41", 17, "#F3F1EC", QFont.Weight.DemiBold)
    p.setBrush(QColor("#F3F1EC"))
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(4):
        p.drawRoundedRect(QRectF(screen.right() - 92 + i * 7, screen.top() + 31 - (i + 1) * 3.2, 4.5, (i + 1) * 3.2), 1, 1)
    p.setPen(QPen(QColor("#F3F1EC"), 1.4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(screen.right() - 56, screen.top() + 17, 26, 13), 3.5, 3.5)
    p.setBrush(QColor("#F3F1EC"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(screen.right() - 54, screen.top() + 19, 18, 9), 2, 2)
    # toques na tela
    for tap in log["taps"]:
        age = t - (tap["t"] - p0)
        if 0 <= age < 0.75:
            point = QPointF(screen.left() + tap["x"] * scale, screen.top() + status + tap["y"] * scale)
            radius = 14 + 34 * out_cubic(age / 0.75)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, int(70 * (1 - age / 0.75))))
            p.drawEllipse(point, radius, radius)
            p.setBrush(QColor(201, 169, 107, int(170 * max(0, 1 - age / 0.35))))
            p.drawEllipse(point, 15, 15)
    p.restore()
    island = QRectF(cx - 54, screen.top() + 11, 108, 30)
    p.setBrush(QColor("#050505"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(island, 16, 16)


def desk_scene(p: QPainter, t: float) -> None:
    image = frame_for(desk_frames, d0, t)
    card = QRectF(0, 0, 1440, 900)
    zoom = 1.0 + 0.05 * ease(t / desk_len)
    fit = 0.92 * zoom
    p.save()
    p.translate(W / 2, H / 2 - 10 + 30 * (1 - out_cubic(t / 1.0)))
    p.scale(fit, fit)
    p.translate(-720 - 60 * ease(t / desk_len), -450)
    bar = QRectF(0, -40, 1440, 40)
    browser = QPainterPath()
    browser.addRoundedRect(QRectF(0, -40, 1440, 940), 16, 16)
    for spread in range(50, 0, -5):
        shadow = QPainterPath()
        shadow.addRoundedRect(QRectF(-spread, -40 - spread + 26, 1440 + 2 * spread, 940 + 2 * spread), 16 + spread, 16 + spread)
        p.fillPath(shadow, QColor(0, 0, 0, 10))
    p.fillPath(browser, QColor("#18181B"))
    for i, color in enumerate(("#3A3A40", "#3A3A40", "#3A3A40")):
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(24 + i * 20, -20), 6, 6)
    p.setBrush(QColor("#0F0F11"))
    p.drawRoundedRect(QRectF(520, -31, 400, 22), 11, 11)
    text(p, (520, -31, 400, 22), "Demonstração local · /painel", 12, "#8E8B84", align=Qt.AlignmentFlag.AlignHCenter)
    clip = QPainterPath()
    clip.addRect(card)
    p.setClipPath(clip)
    p.drawImage(card, image)
    p.restore()
    p.setClipping(False)
    scrim = QLinearGradient(0, H - 330, 0, H)
    scrim.setColorAt(0, QColor(11, 11, 12, 0))
    scrim.setColorAt(0.55, QColor(11, 11, 12, 225))
    scrim.setColorAt(1, QColor(11, 11, 12, 245))
    p.fillRect(QRectF(0, H - 330, W * 0.62, 330), scrim)
    caption_block(p, 120, H - 360, ("7 · Painel do Studio", "Tudo reunido no painel.", "Cobranças, agenda e alunos com dados de demonstração."), out_cubic((t - 0.5) / 0.8), width=1100)


def frame_at(t: float) -> QImage:
    image = QImage(W, H, QImage.Format.Format_RGB888)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    background(p, t)
    segments = [(0, SEG_PHONE, lambda local: wordmark(p, local, False)),
                (SEG_PHONE, SEG_DESK, phone_scene),
                (SEG_DESK, SEG_OUTRO, desk_scene),
                (SEG_OUTRO, TOTAL, lambda local: wordmark(p, local, True))]
    for start, end, draw in segments:
        if start <= t < end:
            local = t - start
            fade = min(ease(local / 0.5), ease((end - t) / 0.45)) if start > 0 else min(ease(local / 0.8), ease((end - t) / 0.45))
            if end == TOTAL:
                fade = min(ease(local / 0.5), ease((end - t) / 1.2))
            if fade >= 0.999:  # sem transição: desenha direto, sem camada extra
                if draw in (phone_scene, desk_scene):
                    draw(p, local)
                else:
                    wordmark(p, local, end == TOTAL)
                continue
            layer = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
            layer.fill(Qt.GlobalColor.transparent)
            lp = QPainter(layer)
            lp.setRenderHints(p.renderHints())
            if draw in (phone_scene, desk_scene):
                draw(lp, local)
            else:
                globals()["_p"] = lp
                (wordmark(lp, local, end == TOTAL))
            lp.end()
            p.setOpacity(fade)
            p.drawImage(0, 0, layer)
            p.setOpacity(1)
    text(p, (60, 16, W - 120, 28), "VERSÃO DE TESTE · ALUNOS FICTÍCIOS", 16, GOLD.name(), align=Qt.AlignmentFlag.AlignRight, spacing=1)
    p.end()
    return image


def soundtrack(path: Path) -> None:
    rate = 44100
    size = int((TOTAL + 0.5) * rate)
    t = np.arange(size) / rate
    note = lambda m: 440 * 2 ** ((m - 69) / 12)
    chords = [[50, 57, 62, 66, 69], [47, 54, 62, 66, 71], [43, 55, 59, 62, 66], [45, 52, 57, 61, 64]]
    bar = 60 / 82 * 4
    left, right = np.zeros(size), np.zeros(size)
    for n in range(int(TOTAL / bar) + 2):
        chord, start = chords[n % 4], n * bar
        a, b = int(start * rate), min(size, int((start + bar + 1.8) * rate))
        if a >= size:
            break
        local = t[a:b] - start
        env = np.minimum(1, local / 1.0) * np.clip((bar + 1.8 - local) / 1.8, 0, 1)
        for m in chord:
            for det, pan in ((0.998, 0.7), (1.002, 0.3)):
                tone = np.sin(2 * np.pi * note(m) * det * t[a:b])
                left[a:b] += tone * env * 0.02 * pan
                right[a:b] += tone * env * 0.02 * (1 - pan)
        for step in range(4):
            onset = start + step * bar / 4
            c, d = int(onset * rate), min(size, int((onset + 2.2) * rate))
            if c >= size:
                continue
            lt = t[c:d] - onset
            f = note(chord[(step + n) % len(chord)] + 12)
            tone = (np.sin(2 * np.pi * f * lt) + 0.3 * np.sin(4 * np.pi * f * lt) * np.exp(-lt * 3)) * np.exp(-lt * 2.2) * np.minimum(1, lt / 0.005)
            left[c:d] += tone * 0.035 * (0.4 + 0.2 * (step % 2))
            right[c:d] += tone * 0.035 * (0.6 - 0.2 * (step % 2))
    for delay, gain in ((0.031, 0.3), (0.067, 0.24), (0.113, 0.18), (0.171, 0.12)):
        s = int(delay * rate)
        left[s:] += left[:-s] * gain
        right[s:] += right[:-s] * gain
    # Clique suave em cada toque e um "plim" de duas notas quando algo é salvo.
    def soma(inicio_s: float, sinal: np.ndarray, ganho: float) -> None:
        a = int(inicio_s * rate)
        b = min(size, a + len(sinal))
        if 0 <= a < size:
            left[a:b] += sinal[: b - a] * ganho
            right[a:b] += sinal[: b - a] * ganho
    clique_t = np.arange(int(0.05 * rate)) / rate
    clique = np.sin(2 * np.pi * 1850 * clique_t) * np.exp(-clique_t * 140) + 0.4 * np.sin(2 * np.pi * 900 * clique_t) * np.exp(-clique_t * 90)
    for toque in log["taps"]:
        soma(SEG_PHONE + toque["t"] - p0 + 0.02, clique, 0.05)
    plim_t = np.arange(int(0.9 * rate)) / rate
    nota = lambda f, atraso: np.where(plim_t >= atraso, np.sin(2 * np.pi * f * (plim_t - atraso)) * np.exp(-(plim_t - atraso).clip(0) * 5), 0)
    plim = nota(1318.5, 0.0) + nota(1760.0, 0.11)
    for marca in log["marks"]:
        if marca["key"] in SUCESSO:
            soma(SEG_PHONE + marca["t"] - p0 + 0.25, plim, 0.06)
    fade = np.minimum(1, t / 1.5) * np.clip((TOTAL - t) / 2.5, 0, 1)
    stereo = np.stack([left * fade, right * fade], axis=1)
    stereo /= max(1e-6, np.abs(stereo).max()) / 0.6
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes((stereo * 32767).astype("<i2").tobytes())


def main() -> None:
    app = QApplication([])
    fonts = ROOT / "frontend" / "node_modules"
    # O Qt daqui não lê .woff2: a serifa vem em .woff e o texto corrido usa a Segoe UI do Windows.
    for pattern in ("@fontsource/instrument-serif/files/instrument-serif-latin-400-normal.woff",
                    "@fontsource/instrument-serif/files/instrument-serif-latin-400-italic.woff"):
        if QFontDatabase.addApplicationFont(str(fonts / pattern)) < 0:
            raise SystemExit(f"Fonte não carregou: {pattern}")
    for name in ("segoeui.ttf", "seguisb.ttf", "segoeuib.ttf", "segoeuisl.ttf"):
        QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts" / name))
    preview = "--preview" in sys.argv
    if preview:
        for moment in (1.5, SEG_PHONE + 4, SEG_PHONE + 13, SEG_PHONE + 24, SEG_PHONE + 33, SEG_PHONE + 44, SEG_OUTRO + 2.5):
            frame_at(moment).save(str(OUT / f"previa-{moment:05.1f}.png"))
        print("prévias em", OUT)
        return
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    music = OUT / "trilha.wav"
    soundtrack(music)
    target = OUT / "Studio-FD-Versao-Web.mp4"
    partial = target.with_suffix(".partial.mp4")
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
               "-i", "pipe:0", "-i", str(music), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
               "-maxrate", "3000k", "-bufsize", "6000k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", str(partial)]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(command, stdin=subprocess.PIPE, creationflags=flags)
    try:
        for n in range(int(TOTAL * FPS)):
            image = frame_at(n / FPS)  # constBits aponta para a memória desta imagem
            process.stdin.write(bytes(image.constBits()))
            if n % (FPS * 10) == 0:
                print(f"{n / FPS:5.1f}s / {TOTAL:.1f}s", flush=True)
        process.stdin.close()
        if process.wait(timeout=60) != 0:
            raise RuntimeError("O codificador falhou.")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    # Só substituir a entrega depois de decodificar vídeo e áudio inteiros.
    subprocess.run([ffmpeg, "-v", "error", "-xerror", "-i", str(partial), "-f", "null", "-"],
                   check=True, timeout=120, creationflags=flags)
    partial.replace(target)
    print(json.dumps({"arquivo": str(target), "segundos": round(TOTAL, 1), "bytes": target.stat().st_size}))


if __name__ == "__main__":
    main()
