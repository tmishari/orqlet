"""A fixed table of libraries Orqlet recognises by name. Anything not listed is not guessed."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Technology:
    name: str
    category: str  # "web", "cli", "orm" or "tasks"


_TABLE = {
    "fastapi": Technology("FastAPI", "web"),
    "flask": Technology("Flask", "web"),
    "django": Technology("Django", "web"),
    "starlette": Technology("Starlette", "web"),
    "aiohttp": Technology("aiohttp", "web"),
    "tornado": Technology("Tornado", "web"),
    "sanic": Technology("Sanic", "web"),
    "litestar": Technology("Litestar", "web"),
    "typer": Technology("Typer", "cli"),
    "click": Technology("Click", "cli"),
    "sqlalchemy": Technology("SQLAlchemy", "orm"),
    "sqlmodel": Technology("SQLModel", "orm"),
    "celery": Technology("Celery", "tasks"),
}


def normalize_name(name: str) -> str:
    """PEP 503 name normalisation: case-insensitive, runs of `-`, `_` and `.` are one `-`."""
    return re.sub(r"[-_.]+", "-", name).lower()


def lookup(name: str) -> Technology | None:
    return _TABLE.get(normalize_name(name))
