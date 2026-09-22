// features/pedido/services/pedidoService.ts
import { clientApi } from "@/shared/api/clientApi";

export type FormaPagamento =
    | "PIX"
    | "CARTAO_CREDITO"
    | "CARTAO_DEBITO"
    | "DINHEIRO";

export interface ItemPedidoPayload {
    alimento_id: string;
    quantidade: number;
}

export interface CriarPedidoPayload {
    restaurante_id: string;
    endereco_id: string;
    forma_pagamento: FormaPagamento;
    valor_pago_dinheiro?: number;
    itens: ItemPedidoPayload[];
    observacoes?: string;
}

export interface PedidoCriadoOut {
    id: string;
    numero_pedido: number;
}

export async function criarPedido(
    payload: CriarPedidoPayload,
): Promise<PedidoCriadoOut> {
    const { data } = await clientApi.post("/pedidos", payload);
    return data;
}
