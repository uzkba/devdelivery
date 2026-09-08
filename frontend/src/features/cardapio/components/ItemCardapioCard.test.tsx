import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ItemCardapioCard } from "./ItemCardapioCard";
import type { ItemCardapio } from "../types/cardapio.types";

const item: ItemCardapio = {
    id: 1, alimentoId: 1, nome: "Frango grelhado", categoria: "Carnes", disponivel: true, preco: 18.9,
};

describe("ItemCardapioCard", () => {
    it("mostra nome e preço do item", () => {
        render(<ItemCardapioCard item={item} onAdicionar={() => {}} />);
        expect(screen.getByText("Frango grelhado")).toBeInTheDocument();
        expect(screen.getByText("R$ 18.90")).toBeInTheDocument();
    });

    it("chama onAdicionar ao clicar", async () => {
        const onAdicionar = vi.fn();
        render(<ItemCardapioCard item={item} onAdicionar={onAdicionar} />);
        await userEvent.click(screen.getByRole("button"));
        expect(onAdicionar).toHaveBeenCalledWith(item);
    });
});