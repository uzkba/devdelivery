import { describe, expect, it, vi, beforeEach } from "vitest";
import { buscarCardapioDoDia } from "../../api/cardapioApi";
import { obterCardapioDoDia } from "../cardapioService";

vi.mock("../../api/cardapioApi", () => ({
    buscarCardapioDoDia: vi.fn(),
}));

describe("obterCardapioDoDia", () => {
    beforeEach(() => {
        vi.mocked(buscarCardapioDoDia).mockReset();
    });

    it("busca via api e devolve já mapeado (camelCase, preco number)", async () => {
        vi.mocked(buscarCardapioDoDia).mockResolvedValue({
            data: "2026-09-12",
            categorias: [
                {
                    categoria_id: "cat-1",
                    categoria_nome: "Bebidas",
                    itens: [
                        {
                            item_id: "item-1",
                            alimento_id: "alimento-1",
                            nome: "Suco de laranja",
                            descricao: null,
                            preco: "7.00",
                            grupos_complemento: [],
                        },
                    ],
                },
            ],
        });

        const resultado = await obterCardapioDoDia("restaurante-123");

        expect(buscarCardapioDoDia).toHaveBeenCalledWith("restaurante-123");
        expect(resultado.categorias[0].itens[0].preco).toBe(7);
        expect(resultado.categorias[0].itens[0].itemId).toBe("item-1");
    });

    it("propaga erro da api", async () => {
        vi.mocked(buscarCardapioDoDia).mockRejectedValue(
            new Error("erro de rede"),
        );
        await expect(obterCardapioDoDia("restaurante-123")).rejects.toThrow(
            "erro de rede",
        );
    });
});
