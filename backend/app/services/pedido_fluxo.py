from app.model.models import OrderServiceType

CRIADO = "CRIADO"
CONFIRMADO = "CONFIRMADO"
EM_PREPARO = "EM_PREPARO"
PRONTO = "PRONTO"
SAIU_PARA_ENTREGA = "SAIU_PARA_ENTREGA"
ENTREGUE = "ENTREGUE"
RETIRADO = "RETIRADO"
CANCELADO = "CANCELADO"
RECUSADO = "RECUSADO"

FLUXO_ENTREGA = (CRIADO, CONFIRMADO, EM_PREPARO, PRONTO, SAIU_PARA_ENTREGA, ENTREGUE)
FLUXO_RETIRADA = (CRIADO, CONFIRMADO, EM_PREPARO, PRONTO, RETIRADO)
FINAIS = frozenset({ENTREGUE, RETIRADO, CANCELADO, RECUSADO})
COM_MOTIVO = frozenset({CANCELADO, RECUSADO})
TODOS = frozenset(FLUXO_ENTREGA) | frozenset(FLUXO_RETIRADA) | {CANCELADO, RECUSADO}


def fluxo_do_tipo(tipo: OrderServiceType) -> tuple[str, ...]:
    if tipo == OrderServiceType.PICKUP:
        return FLUXO_RETIRADA
    return FLUXO_ENTREGA


def transicoes_permitidas(tipo: OrderServiceType, atual: str) -> list[str]:
    if atual in FINAIS:
        return []
    fluxo = fluxo_do_tipo(tipo)
    if atual not in fluxo:
        return []
    permitidas = [fluxo[fluxo.index(atual) + 1]]
    if atual == CRIADO:
        permitidas.append(RECUSADO)
    else:
        permitidas.append(CANCELADO)
    return permitidas


def pode_transitar(tipo: OrderServiceType, atual: str, novo: str) -> bool:
    return novo in transicoes_permitidas(tipo, atual)


ACAO_POR_STATUS = {
    CONFIRMADO: "aceitar",
    EM_PREPARO: "preparo",
    PRONTO: "pronto",
    SAIU_PARA_ENTREGA: "enviar",
    ENTREGUE: "entregue",
    RETIRADO: "retirado",
    CANCELADO: "cancelar",
    RECUSADO: "recusar",
}

ROTULOS = {
    CRIADO: "Aguardando confirmação",
    CONFIRMADO: "Pedido confirmado",
    EM_PREPARO: "Em preparo",
    PRONTO: "Pronto",
    SAIU_PARA_ENTREGA: "Saiu para entrega",
    ENTREGUE: "Entregue",
    RETIRADO: "Retirado",
    CANCELADO: "Cancelado",
    RECUSADO: "Recusado",
}

ROTULOS_ENTREGA = {PRONTO: "Pronto, aguardando o entregador"}
ROTULOS_RETIRADA = {PRONTO: "Pronto para retirada"}


def acoes_disponiveis(tipo: OrderServiceType, atual: str) -> list[str]:
    return [ACAO_POR_STATUS[codigo] for codigo in transicoes_permitidas(tipo, atual)]


def rotulo(tipo: OrderServiceType, codigo: str, padrao: str) -> str:
    especificos = ROTULOS_RETIRADA if tipo == OrderServiceType.PICKUP else ROTULOS_ENTREGA
    return especificos.get(codigo) or ROTULOS.get(codigo) or padrao


ABAS = {
    "novos": frozenset({CRIADO}),
    "em_andamento": frozenset({CONFIRMADO, EM_PREPARO, PRONTO, SAIU_PARA_ENTREGA}),
    "finalizados": FINAIS,
}