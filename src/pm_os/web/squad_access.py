"""Squad identifier and membership authorization helpers."""

import re

_SQUAD_KEY_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?$")


def normalize_squad_key(value: str) -> str:
    key = re.sub(r"\s+", "-", value.strip().lower())
    return key if _SQUAD_KEY_PATTERN.fullmatch(key) else ""


def authorized_squad(
    current_squad: str,
    user_email: str,
    squads: dict,
) -> str:
    if not current_squad or not user_email:
        return ""
    squad = squads.get(current_squad)
    if not isinstance(squad, dict):
        return ""
    return current_squad if user_email in squad.get("members", []) else ""
