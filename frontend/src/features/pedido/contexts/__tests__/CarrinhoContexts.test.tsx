import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CarrinhoProvider, useCarrinho } from "../CarrinhoContexts";

function Consumidor() {
    const {
        itens,
        totalItens,
        subtotal,
        getQuantidade,
        definirQuantidade,
        limparCarrinho,
    } = useCarrinho();

    const item1 = { id: "1", name: "Arroz", catName: "Arroz", price: 10 };
    const item2 = { id: "2", name: "Feijão", catName: "Feijão", price: 5 };

    return (
        <div>
            <p data-testid="total-itens">{totalItens}</p>
            <p data-testid="subtotal">{subtotal}</p>
            <p data-testid="qtd-item-1">{getQuantidade("1")}</p>
            <ul>
                {itens.map((i) => (
                    <li key={i.id}>
                        {i.name} x{i.qty}
                    </li>
                ))}
            </ul>
            <button onClick={() => definirQuantidade(item1, 1)}>
                add item 1
            </button>
            <button onClick={() => definirQuantidade(item1, 2)}>
                set item 1 to 2
            </button>
            <button onClick={() => definirQuantidade(item1, 0)}>
                remove item 1
            </button>
            <button onClick={() => definirQuantidade(item2, 1)}>
                add item 2
            </button>
            <button onClick={limparCarrinho}>limpar</button>
        </div>
    );
}

function renderComProvider() {
    return render(
        <CarrinhoProvider>
            <Consumidor />
        </CarrinhoProvider>,
    );
}

describe("CarrinhoContext", () => {
    beforeEach(() => {
        sessionStorage.clear();
    });

    it("começa vazio", () => {
        renderComProvider();
        expect(screen.getByTestId("total-itens")).toHaveTextContent("0");
        expect(screen.getByTestId("subtotal")).toHaveTextContent("0");
    });

    it("adiciona um item e atualiza os totais", async () => {
        const user = userEvent.setup();
        renderComProvider();

        await user.click(screen.getByText("add item 1"));

        expect(screen.getByTestId("total-itens")).toHaveTextContent("1");
        expect(screen.getByTestId("subtotal")).toHaveTextContent("10");
        expect(screen.getByText("Arroz x1")).toBeInTheDocument();
    });

    it("atualiza a quantidade do mesmo item em vez de duplicar", async () => {
        const user = userEvent.setup();
        renderComProvider();

        await user.click(screen.getByText("add item 1"));
        await user.click(screen.getByText("set item 1 to 2"));

        expect(screen.getByTestId("total-itens")).toHaveTextContent("2");
        expect(screen.getByTestId("subtotal")).toHaveTextContent("20");
        expect(screen.getAllByText(/Arroz/)).toHaveLength(1);
    });

    it("remove o item quando a quantidade vira 0", async () => {
        const user = userEvent.setup();
        renderComProvider();

        await user.click(screen.getByText("add item 1"));
        await user.click(screen.getByText("remove item 1"));

        expect(screen.getByTestId("total-itens")).toHaveTextContent("0");
        expect(screen.queryByText(/Arroz/)).not.toBeInTheDocument();
    });

    it("soma o subtotal de múltiplos itens", async () => {
        const user = userEvent.setup();
        renderComProvider();

        await user.click(screen.getByText("add item 1")); // 10
        await user.click(screen.getByText("add item 2")); // 5

        expect(screen.getByTestId("subtotal")).toHaveTextContent("15");
        expect(screen.getByTestId("total-itens")).toHaveTextContent("2");
    });

    it("getQuantidade devolve 0 pra item que não está no carrinho", () => {
        renderComProvider();
        expect(screen.getByTestId("qtd-item-1")).toHaveTextContent("0");
    });

    it("limparCarrinho esvazia tudo", async () => {
        const user = userEvent.setup();
        renderComProvider();

        await user.click(screen.getByText("add item 1"));
        await user.click(screen.getByText("add item 2"));
        await user.click(screen.getByText("limpar"));

        expect(screen.getByTestId("total-itens")).toHaveTextContent("0");
        expect(screen.getByTestId("subtotal")).toHaveTextContent("0");
    });

    it("persiste no sessionStorage e recupera numa nova instância do provider", async () => {
        const user = userEvent.setup();
        const { unmount } = renderComProvider();

        await user.click(screen.getByText("add item 1"));
        unmount();

        renderComProvider();
        expect(screen.getByTestId("total-itens")).toHaveTextContent("1");
        expect(screen.getByText("Arroz x1")).toBeInTheDocument();
    });

    it("useCarrinho lança erro se usado fora do CarrinhoProvider", () => {
        const consoleErrorSpy = vi
            .spyOn(console, "error")
            .mockImplementation(() => {});
        expect(() => render(<Consumidor />)).toThrow(
            "useCarrinho precisa estar dentro de um CarrinhoProvider",
        );
        consoleErrorSpy.mockRestore();
    });
});
