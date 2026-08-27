import { describe, it, expect } from "vitest";
import { agruparPorCategoria } from "./cardapio.utils";
import type { ItemCardapio } from "../types/cardapio.types";

const item = (overrides: Partial<ItemCardapio>): ItemCardapio => ({
    id: 1, alimentoId: 1, nome: "Item", categoria: "Carnes", disponivel: true, preco: 10,
    ...overrides,
});

describe("agruparPorCategoria", () => {
    it("agrupa itens pela categoria", () => {
        const itens = [
        item({ id: 1, nome: "Frango", categoria: "Carnes" }),
        item({ id: 2, nome: "Arroz", categoria: "Acompanhamentos" }),
        item({ id: 3, nome: "Bife", categoria: "Carnes" }),
        ];
        const resultado = agruparPorCategoria(itens);

        expect(resultado["Carnes"]).toHaveLength(2);
        expect(resultado["Acompanhamentos"]).toHaveLength(1);
    });

    it("retorna objeto vazio para lista vazia", () => {
        expect(agruparPorCategoria([])).toEqual({});
    });
});