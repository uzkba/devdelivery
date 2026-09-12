import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CardapioItemCard from "../CardapioItemCard";

describe("CardapioItemCard", () => {
    it("mostra nome, descrição e preço formatado em BRL", () => {
        render(
            <CardapioItemCard
                nome="Bife acebolado"
                descricao="Com cebola caramelizada"
                preco={18.5}
                quantidade={0}
                accent="#DC2626"
                onIncrementar={vi.fn()}
                onDecrementar={vi.fn()}
            />,
        );

        expect(screen.getByText("Bife acebolado")).toBeInTheDocument();
        expect(screen.getByText("Com cebola caramelizada")).toBeInTheDocument();
        expect(screen.getByText("R$ 18,50")).toBeInTheDocument();
    });

    it("quando quantidade é 0, mostra só o botão de adicionar", () => {
        render(
            <CardapioItemCard
                nome="Bife"
                preco={18.5}
                quantidade={0}
                accent="#DC2626"
                onIncrementar={vi.fn()}
                onDecrementar={vi.fn()}
            />,
        );

        expect(
            screen.getByLabelText("Adicionar Bife ao carrinho"),
        ).toBeInTheDocument();
        expect(
            screen.queryByLabelText("Remover uma unidade de Bife"),
        ).not.toBeInTheDocument();
    });

    it("quando quantidade > 0, mostra stepper com o número atual", () => {
        render(
            <CardapioItemCard
                nome="Bife"
                preco={18.5}
                quantidade={3}
                accent="#DC2626"
                onIncrementar={vi.fn()}
                onDecrementar={vi.fn()}
            />,
        );

        expect(screen.getByText("3")).toBeInTheDocument();
        expect(
            screen.getByLabelText("Adicionar uma unidade de Bife"),
        ).toBeInTheDocument();
        expect(
            screen.getByLabelText("Remover uma unidade de Bife"),
        ).toBeInTheDocument();
    });

    it("chama onIncrementar e onDecrementar ao clicar", () => {
        const onIncrementar = vi.fn();
        const onDecrementar = vi.fn();

        render(
            <CardapioItemCard
                nome="Bife"
                preco={18.5}
                quantidade={1}
                accent="#DC2626"
                onIncrementar={onIncrementar}
                onDecrementar={onDecrementar}
            />,
        );

        fireEvent.click(screen.getByLabelText("Adicionar uma unidade de Bife"));
        fireEvent.click(screen.getByLabelText("Remover uma unidade de Bife"));

        expect(onIncrementar).toHaveBeenCalledTimes(1);
        expect(onDecrementar).toHaveBeenCalledTimes(1);
    });

    it("não quebra quando descricao é null/omitida", () => {
        render(
            <CardapioItemCard
                nome="Bife"
                preco={18.5}
                quantidade={0}
                accent="#DC2626"
                onIncrementar={vi.fn()}
                onDecrementar={vi.fn()}
            />,
        );
        expect(screen.getByText("Bife")).toBeInTheDocument();
    });
});
