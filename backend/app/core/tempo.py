from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")


def agora_local(agora: datetime | None = None) -> datetime:
    if agora is None:
        agora = datetime.now(timezone.utc)
    elif agora.tzinfo is None:
        raise ValueError("`agora` precisa ter fuso (tzinfo).")
    return agora.astimezone(FUSO_LOCAL)


def hoje_local(agora: datetime | None = None) -> date:
    return agora_local(agora).date()