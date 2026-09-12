import { describe, expect, it } from "vitest";
import { corDaCategoria } from "../corPorCategoria";

describe("corDaCategoria", () => {
    it("retorna a cor certa pra categorias conhecidas", () => {
        expect(corDaCategoria("Arroz")).toBe("#D97706");
        expect(corDaCategoria("Carnes")).toBe("#DC2626");
        expect(corDaCategoria("Bebidas")).toBe("#0EA5E9");
    });

    it("é case-insensitive", () => {
        expect(corDaCategoria("CARNES")).toBe("#DC2626");
        expect(corDaCategoria("carnes")).toBe("#DC2626");
    });

    it("ignora acento (ex: Feijão vs feijao)", () => {
        expect(corDaCategoria("Feijão")).toBe("#EA580C");
    });

    it("ignora espaços nas pontas", () => {
        expect(corDaCategoria("  Saladas  ")).toBe("#16A34A");
    });

    it("retorna a cor padrão pra categoria desconhecida", () => {
        expect(corDaCategoria("Sobremesas")).toBe("#F97316");
    });
});
