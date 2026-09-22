import { describe, it, expect, vi, beforeEach } from "vitest";

const mockPost = vi.fn();
vi.mock("@/shared/api/clientApi", () => ({
    clientApi: { post: (...args: any[]) => mockPost(...args) },
}));

import { criarPedido } from "../pedidoService";

describe("pedidoService.criarPedido", () => {
    beforeEach(() => {
        mockPost.mockReset();
    });

    it("faz POST em /pedidos com o payload recebido e devolve os dados da resposta", async () => {
        const payload = {
            restaurante_id: "rest-1",
            itens: [{ alimento_id: "item-1", quantidade: 2 }],
            endereco_id: "end-1",
            forma_pagamento: "PIX" as const,
            observacoes: undefined,
        };
        mockPost.mockResolvedValue({
            data: { id: "pedido-1", numero_pedido: 42 },
        });

        const resultado = await criarPedido(payload);

        expect(mockPost).toHaveBeenCalledWith("/pedidos", payload);
        expect(resultado).toEqual({ id: "pedido-1", numero_pedido: 42 });
    });
});
