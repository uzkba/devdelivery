from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")


def hoje_local(agora: datetime | None = None) -> date:
    """Data local atual. `agora` (com fuso) existe para os testes."""
    if agora is None:
        agora = datetime.now(timezone.utc)
    elif agora.tzinfo is None:
        raise ValueError("`agora` precisa ter fuso (tzinfo).")
    return agora.astimezone(FUSO_LOCAL).date()