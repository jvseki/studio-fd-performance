"""Versões numéricas também compatíveis com os recursos de executáveis Windows."""

import re


def version_tuple(version: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise ValueError("Use uma versão como 0.2.1, com três números separados por pontos.")
    parts = tuple(int(part) for part in version.split("."))
    if any(part > 65535 for part in parts):
        raise ValueError("Cada parte da versão deve ser menor que 65536.")
    return parts
