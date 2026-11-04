"""Somente prepara links. Não envia mensagens nem registra pagamentos."""

from urllib.parse import quote

from studio_fd.utils.formatting import normalize_phone


def greeting(full_name: str) -> str:
    first_name = full_name.strip().split()[0] if full_name.strip() else ""
    return f"Olá, {first_name}! Aqui é do Studio FD Performance. Tudo bem?"


def chat_url(phone: str, message: str = "") -> str:
    number = normalize_phone(phone)
    if len(message) > 2000:
        raise ValueError("Use uma mensagem de até 2.000 caracteres.")
    url = f"https://wa.me/{number}"
    return url + ("?text=" + quote(message, safe="") if message else "")
