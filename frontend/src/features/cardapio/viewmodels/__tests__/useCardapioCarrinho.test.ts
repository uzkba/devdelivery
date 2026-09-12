import { describe, expect, it } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCardapioCarrinho } from "../useCardapioCarrinho";
import type { CardapioDoDia } from "../../types/cardapio";

const CARDAPIO: CardapioDoDia = {
    data: "2026-09-12",
    categorias: [
        {
            categoriaId: "cat-1",
            categoriaNome: "Carnes",
            itens: [
                {
                    itemId: "item-1",
                    alimentoId: "a-1",
                    nome: "Bife",
                    descricao: null,
                    preco: 18.5,
                    gruposComplemento: [],
                },
                {
                    itemId: "item-2",
                    alimentoId: "a-2",
                    nome: "Frango",
                    descricao: null,
                    preco: 15,
                    gruposComplemento: [],
                },
            ],
        },
    ],
};

describe("useCardapioCarrinho", () => {
    it("começa vazio quando não há cardápio", () => {
        const { result } = renderHook(() => useCardapioCarrinho(null));
        expect(result.current.itensCarrinho).toEqual([]);
        expect(result.current.totalItens).toBe(0);
        expect(result.current.total).toBe(0);
    });

    it("adiciona um item ao definir quantidade", () => {
        const { result } = renderHook(() => useCardapioCarrinho(CARDAPIO));

        act(() => result.current.definirQuantidade("item-1", 2));

        expect(result.current.itensCarrinho).toEqual([
            { id: "item-1", nome: "Bife", preco: 18.5, quantidade: 2 },
        ]);
        expect(result.current.totalItens).toBe(2);
    });

    it("remove o item quando a quantidade cai pra 0 ou menos", () => {
        const { result } = renderHook(() => useCardapioCarrinho(CARDAPIO));

        act(() => result.current.definirQuantidade("item-1", 1));
        act(() => result.current.definirQuantidade("item-1", 0));

        expect(result.current.itensCarrinho).toEqual([]);
    });

    it("calcula subtotal e total (subtotal + taxa de entrega de 5) só quando há itens", () => {
        const { result } = renderHook(() => useCardapioCarrinho(CARDAPIO));

        act(() => {
            result.current.definirQuantidade("item-1", 1); // 18.5
            result.current.definirQuantidade("item-2", 2); // 15 * 2 = 30
        });

        expect(result.current.subtotal).toBe(48.5);
        expect(result.current.total).toBe(53.5); // 48.5 + 5
    });

    it("total fica 0 quando o carrinho está vazio (sem taxa de entrega fantasma)", () => {
        const { result } = renderHook(() => useCardapioCarrinho(CARDAPIO));
        expect(result.current.total).toBe(0);
    });

    it("lida com múltiplos itens de categorias diferentes", () => {
        const cardapioComDuasCategorias: CardapioDoDia = {
            data: "2026-09-12",
            categorias: [
                ...CARDAPIO.categorias,
                {
                    categoriaId: "cat-2",
                    categoriaNome: "Bebidas",
                    itens: [
                        {
                            itemId: "item-3",
                            alimentoId: "a-3",
                            nome: "Suco",
                            descricao: null,
                            preco: 7,
                            gruposComplemento: [],
                        },
                    ],
                },
            ],
        };
        const { result } = renderHook(() =>
            useCardapioCarrinho(cardapioComDuasCategorias),
        );

        act(() => {
            result.current.definirQuantidade("item-1", 1);
            result.current.definirQuantidade("item-3", 1);
        });

        expect(result.current.itensCarrinho).toHaveLength(2);
        expect(result.current.itensCarrinho.map((i) => i.id)).toEqual([
            "item-1",
            "item-3",
        ]);
    });
});
