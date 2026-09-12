import { describe, expect, it } from "vitest";
import { mapCardapioDoDia, type CardapioDoDiaApi } from "../cardapioMapper";

function criarApiFake(overrides?: Partial<CardapioDoDiaApi>): CardapioDoDiaApi {
    return {
        data: "2026-09-12",
        categorias: [
            {
                categoria_id: "cat-1",
                categoria_nome: "Carnes",
                itens: [
                    {
                        item_id: "item-1",
                        alimento_id: "alimento-1",
                        nome: "Bife acebolado",
                        descricao: "Com cebola caramelizada",
                        preco: "18.50",
                        grupos_complemento: [
                            {
                                id: "grupo-1",
                                nome: "Ponto da carne",
                                min_choices: 1,
                                max_choices: 1,
                                opcoes: [
                                    {
                                        id: "opcao-1",
                                        nome: "Mal passado",
                                        preco_adicional: "0.00",
                                        disponivel: true,
                                    },
                                    {
                                        id: "opcao-2",
                                        nome: "Bem passado",
                                        preco_adicional: "0.00",
                                        disponivel: false,
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
        ...overrides,
    };
}

describe("mapCardapioDoDia", () => {
    it("converte data e mantém a estrutura de categorias", () => {
        const resultado = mapCardapioDoDia(criarApiFake());
        expect(resultado.data).toBe("2026-09-12");
        expect(resultado.categorias).toHaveLength(1);
        expect(resultado.categorias[0].categoriaId).toBe("cat-1");
        expect(resultado.categorias[0].categoriaNome).toBe("Carnes");
    });

    it("converte preço de string para number", () => {
        const resultado = mapCardapioDoDia(criarApiFake());
        const item = resultado.categorias[0].itens[0];
        expect(item.preco).toBe(18.5);
        expect(typeof item.preco).toBe("number");
    });

    it("mapeia item_id/alimento_id pra itemId/alimentoId", () => {
        const resultado = mapCardapioDoDia(criarApiFake());
        const item = resultado.categorias[0].itens[0];
        expect(item.itemId).toBe("item-1");
        expect(item.alimentoId).toBe("alimento-1");
    });

    it("mapeia grupos e opções de complemento, convertendo preco_adicional", () => {
        const resultado = mapCardapioDoDia(criarApiFake());
        const [grupo] = resultado.categorias[0].itens[0].gruposComplemento;
        expect(grupo.minChoices).toBe(1);
        expect(grupo.maxChoices).toBe(1);
        expect(grupo.opcoes[0]).toEqual({
            id: "opcao-1",
            nome: "Mal passado",
            precoAdicional: 0,
            disponivel: true,
        });
        expect(grupo.opcoes[1].disponivel).toBe(false);
    });

    it("lida com item sem complementos (array vazio)", () => {
        const api = criarApiFake();
        api.categorias[0].itens[0].grupos_complemento = [];
        const resultado = mapCardapioDoDia(api);
        expect(resultado.categorias[0].itens[0].gruposComplemento).toEqual([]);
    });

    it("lida com cardápio sem categorias", () => {
        const resultado = mapCardapioDoDia({
            data: "2026-09-12",
            categorias: [],
        });
        expect(resultado.categorias).toEqual([]);
    });

    it("preserva descricao null", () => {
        const api = criarApiFake();
        api.categorias[0].itens[0].descricao = null;
        const resultado = mapCardapioDoDia(api);
        expect(resultado.categorias[0].itens[0].descricao).toBeNull();
    });
});
