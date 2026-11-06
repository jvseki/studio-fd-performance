"""Datas em português, sem depender do idioma configurado no Windows."""

import calendar
from datetime import date, datetime, timedelta

MONTHS = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
          "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
WEEKDAYS_SHORT = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


def first_of_month(value: date) -> date:
    return value.replace(day=1)


def add_months(value: date, months: int) -> date:
    index = value.year * 12 + value.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def day_in_month(month: date, day: int) -> date:
    """O dia pedido ou o último do mês (vencimento 31 em fevereiro cai no dia 28/29)."""
    return month.replace(day=min(day, calendar.monthrange(month.year, month.month)[1]))


def month_label(value: date) -> str:
    return f"{MONTHS[value.month - 1]} {value.year}"


def short_month(value: date) -> str:
    return MONTHS[value.month - 1][:3]


def long_date(value: date) -> str:
    return f"{WEEKDAYS[value.weekday()]}, {value.day} de {MONTHS[value.month - 1].lower()}"


def br_date(value: date | None, empty: str = "—") -> str:
    return value.strftime("%d/%m/%Y") if value else empty


def week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def parse_time(text: str) -> int:
    """'07:30' -> minutos desde a meia-noite. Valida o formato HH:MM."""
    try:
        moment = datetime.strptime(text.strip(), "%H:%M")
    except ValueError as error:
        raise ValueError("Use o horário no formato HH:MM, por exemplo 07:00.") from error
    return moment.hour * 60 + moment.minute


def format_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
