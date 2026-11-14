from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from app.core.tempo import FUSO_LOCAL, agora_local

NOMES_DIA_SEMANA = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")


@dataclass(frozen=True)
class JanelaDoDia:
    dia: date
    inicio: datetime
    fim: datetime


def _utc_sem_fuso(momento: datetime) -> datetime:
    return momento.astimezone(timezone.utc).replace(tzinfo=None)


def _local_para_utc(dia: date, hora: time) -> datetime:
    return _utc_sem_fuso(datetime.combine(dia, hora, tzinfo=FUSO_LOCAL))


def intervalo_do_mes_em_utc(mes: str) -> tuple[datetime, datetime]:
    ano, numero = (int(parte) for parte in mes.split("-"))
    proximo_ano, proximo_mes = (ano + 1, 1) if numero == 12 else (ano, numero + 1)
    inicio = datetime(ano, numero, 1, tzinfo=FUSO_LOCAL)
    fim = datetime(proximo_ano, proximo_mes, 1, tzinfo=FUSO_LOCAL)
    return _utc_sem_fuso(inicio), _utc_sem_fuso(fim)


def mes_local(momento: datetime) -> str:
    local = momento.replace(tzinfo=timezone.utc).astimezone(FUSO_LOCAL)
    return f"{local.year:04d}-{local.month:02d}"


def intervalo_do_dia_em_utc(dia: date) -> tuple[datetime, datetime]:
    return _local_para_utc(dia, time.min), _local_para_utc(dia + timedelta(days=1), time.min)


def janelas_comparaveis(agora: datetime | None = None) -> tuple[JanelaDoDia, JanelaDoDia]:
    local = agora_local(agora)
    hoje = local.date()
    semana_passada = hoje - timedelta(days=7)
    atual = JanelaDoDia(hoje, _local_para_utc(hoje, time.min), _utc_sem_fuso(local))
    anterior = JanelaDoDia(
        semana_passada,
        _local_para_utc(semana_passada, time.min),
        _local_para_utc(semana_passada, local.time()),
    )
    return atual, anterior


def rotulo_semana_passada(dia: date) -> str:
    sufixo = "passado" if dia.weekday() >= 5 else "passada"
    return f"{NOMES_DIA_SEMANA[dia.weekday()]} {sufixo}"


def agora_em_utc(agora: datetime | None = None) -> datetime:
    return _utc_sem_fuso(agora_local(agora))