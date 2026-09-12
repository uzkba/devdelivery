import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useCardapioDoDia } from "@/features/cardapio/hooks/useCardapioDoDia";
import { useCardapioCarrinho } from "@/features/cardapio/viewmodels/useCardapioCarrinho";
import CardapioClientePage from "../CardapioClientePage";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
    const actual = await importOriginal<typeof import("react-router-dom")>();
    return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("@/features/cardapio/hooks/useCardapioDoDia", () => ({
    useCardapioDoDia: vi.fn(),
}));

vi.mock("@/features/cardapio/viewmodels/useCardapioCarrinho", () => ({
    useCardapioCarrinho: vi.fn(),
}));

const CARRINHO_VAZIO = {
    quantidades: {},
    definirQuantidade: vi.fn(),
    itensCarrinho: [],
    totalItens: 0,
    subtotal: 0,
    total: 0,
};

function renderPagina() {
    return render(
        <MemoryRouter>
            <CardapioClientePage />
        </MemoryRouter>,
    );
}

describe("CardapioClientePage", () => {
    beforeEach(() => {
        mockNavigate.mockReset();
        vi.mocked(useCardapioCarrinho).mockReturnValue(CARRINHO_VAZIO);
    });

    it("mostra o skeleton enquanto carrega", () => {
        vi.mocked(useCardapioDoDia).mockReturnValue({
            cardapio: null,
            carregando: true,
            erro: null,
            recarregar: vi.fn(),
        });

        const { container } = renderPagina();
        expect(container.querySelector(".animate-pulse")).not.toBeNull();
    });

    it("mostra a mensagem de erro com botão de tentar novamente", () => {
        const recarregar = vi.fn();
        vi.mocked(useCardapioDoDia).mockReturnValue({
            cardapio: null,
            carregando: false,
            erro: "Não foi possível carregar o cardápio de hoje. Tente novamente.",
            recarregar,
        });

        renderPagina();

        expect(
            screen.getByText(
                "Não foi possível carregar o cardápio de hoje. Tente novamente.",
            ),
        ).toBeInTheDocument();
        fireEvent.click(screen.getByText("Tentar novamente"));
        expect(recarregar).toHaveBeenCalledTimes(1);
    });

    it("mostra o estado vazio quando não há categorias", () => {
        vi.mocked(useCardapioDoDia).mockReturnValue({
            cardapio: { data: "2026-09-12", categorias: [] },
            carregando: false,
            erro: null,
            recarregar: vi.fn(),
        });

        renderPagina();

        expect(
            screen.getByText("Nenhum cardápio disponível hoje"),
        ).toBeInTheDocument();
    });

    it("renderiza as categorias e itens do cardápio", () => {
        vi.mocked(useCardapioDoDia).mockReturnValue({
            cardapio: {
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
                        ],
                    },
                ],
            },
            carregando: false,
            erro: null,
            recarregar: vi.fn(),
        });

        renderPagina();

        expect(screen.getAllByText("Carnes").length).toBeGreaterThan(0);
        expect(screen.getByText("Bife")).toBeInTheDocument();
    });

    it("não mostra o resumo/CTA quando o carrinho está vazio", () => {
        vi.mocked(useCardapioDoDia).mockReturnValue({
            cardapio: {
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
                        ],
                    },
                ],
            },
            carregando: false,
            erro: null,
            recarregar: vi.fn(),
        });

        renderPagina();

        expect(
            screen.getByText(
                "Toque em um alimento para adicioná-lo ao pedido.",
            ),
        ).toBeInTheDocument();
        expect(screen.queryByText("Continuar")).not.toBeInTheDocument();
    });

    it("mostra o resumo e navega pro checkout com os itens do carrinho ao clicar em Continuar", () => {
        vi.mocked(useCardapioDoDia).mockReturnValue({
            cardapio: {
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
                        ],
                    },
                ],
            },
            carregando: false,
            erro: null,
            recarregar: vi.fn(),
        });

        const itensCarrinho = [
            { id: "item-1", nome: "Bife", preco: 18.5, quantidade: 2 },
        ];
        vi.mocked(useCardapioCarrinho).mockReturnValue({
            ...CARRINHO_VAZIO,
            itensCarrinho,
            totalItens: 2,
            total: 42,
        });

        renderPagina();

        fireEvent.click(screen.getByText("Continuar"));

        expect(mockNavigate).toHaveBeenCalledWith("/pedido/endereco", {
            state: { cartItems: itensCarrinho },
        });
    });
});
