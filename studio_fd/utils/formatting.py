"""Normalização de pesquisa, telefone e valores em reais."""

import re
import unicodedata


def search_key(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def normalize_phone(text: str) -> str:
    if re.search(r"[^0-9+()\s.-]", text):
        raise ValueError("Digite o telefone com DDD. Exemplo: (18) 99999-9999.")
    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) in (12, 13) and digits.startswith("55"):
        digits = digits[2:]
    if len(digits) not in (10, 11) or digits[0] == "0" or digits[1] == "0":
        raise ValueError("Digite um telefone brasileiro com DDD. Exemplo: (18) 99999-9999.")
    return "55" + digits


def display_phone(text: str) -> str:
    try:
        digits = normalize_phone(text)[2:]
    except ValueError:
        return text or "Não informado"
    return f"({digits[:2]}) {digits[2:-4]}-{digits[-4:]}"


def normalize_cpf(text: str | None) -> str | None:
    if not text or not text.strip():
        return None
    if re.search(r"[^0-9.\s-]", text):
        raise ValueError("Confira o CPF ou deixe esse campo em branco.")
    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) != 11 or len(set(digits)) == 1:
        raise ValueError("Confira o CPF: ele precisa ter 11 números válidos.")
    for length in (9, 10):
        total = sum(int(digits[index]) * (length + 1 - index) for index in range(length))
        remainder = total % 11
        expected = 0 if remainder < 2 else 11 - remainder
        if int(digits[length]) != expected:
            raise ValueError("Confira o CPF: os dígitos verificadores não conferem.")
    return digits


def brl(cents: int | None) -> str:
    if cents is None:
        return "Não informado"
    whole, fraction = divmod(cents, 100)
    return f"R$ {whole:,}".replace(",", ".") + f",{fraction:02d}"
