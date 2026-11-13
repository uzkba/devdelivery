from datetime import datetime, timezone
from zoneinfo import ZoneInfo

FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")


def _utc_sem_fuso(momento: datetime) -> datetime:
    return momento.astimezone(timezone.utc).replace(tzinfo=None)


def intervalo_do_mes_em_utc(mes: str) -> tuple[datetime, datetime]:
    ano, numero = (int(parte) for parte in mes.split("-"))
    proximo_ano, proximo_mes = (ano + 1, 1) if numero == 12 else (ano, numero + 1)
    inicio = datetime(ano, numero, 1, tzinfo=FUSO_LOCAL)
    fim = datetime(proximo_ano, proximo_mes, 1, tzinfo=FUSO_LOCAL)
    return _utc_sem_fuso(inicio), _utc_sem_fuso(fim)


def mes_local(momento: datetime) -> str:
    local = momento.replace(tzinfo=timezone.utc).astimezone(FUSO_LOCAL)
    return f"{local.year:04d}-{local.month:02d}"