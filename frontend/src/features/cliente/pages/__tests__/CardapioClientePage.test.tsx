import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
    const actual = await vi.importActual("react-router-dom");
    return { ...actual, useNavigate: () => mockNavigate };
});

const mockUseCardapioDoDia = vi.fn();
vi.mock("@/features/cardapio/hooks/useCardapioDoDia", () => ({
    useCardapioDoDia: () => mockUseCardapioDoDia(),
}));

const mockUseCarrinho = vi.fn();
vi.mock("@/features/pedido/contexts/CarrinhoContexts", () => ({
    useCarrinho: () => mockUseCarrinho(),
}));

vi.mock("@/features/cardapio/utils/corPorCategoria", () => ({
    corDaCategoria: () => "#F97316",
}));

vi.mock("@/features/cardapio/components/CardapioItemCard", () => ({
    default: (props: any) => (
        <div>
            <span>{props.nome}</span>
            <span data-testid={`qtd-${props.nome}`}>{props.quantidade}</span>
            <button onClick={props.onIncrementar}>+ {props.nome}</button>
            <button onClick={props.onDecrementar}>- {props.nome}</button>
        </div>
    ),
}));

vi.mock("@/features/cardapio/components/CardapioSkeleton", () => ({
    default: () => <div>carregando cardápio...</div>,
}));

vi.mock("@/features/cardapio/components/CardapioVazio", () => ({
    default: () => <div>nenhum cardápio disponível hoje</div>,
}));

import CardapioClientePage from "../CardapioClientePage";

const CARDAPIO_MOCK = {
    data: "2026-09-15",
    categorias: [
        {
            categoriaId: "cat-1",
            categoriaNome: "Arroz",
            itens: [
                {
                    itemId: "item-1",
                    nome: "Arroz Branco",
                    descricao: "",
                    preco: 8,
                },
            ],
        },
    ],
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
        mockNavigate.mockClear();
        mockUseCarrinho.mockReturnValue({
            getQuantidade: () => 0,
            definirQuantidade: vi.fn(),
            totalItens: 0,
        });
    });

    it("mostra o skeleton enquanto carrega", () => {
        mockUseCardapioDoDia.mockReturnValue({
            cardapio: null,
            carregando: true,
            erro: null,
            recarregar: vi.fn(),
        });
        renderPagina();
        expect(screen.getByText("carregando cardápio...")).toBeInTheDocument();
    });

    it("mostra erro com botão de tentar novamente", async () => {
        const recarregar = vi.fn();
        mockUseCardapioDoDia.mockReturnValue({
            cardapio: null,
            carregando: false,
            erro: "Falha ao carregar",
            recarregar,
        });
        renderPagina();

        expect(screen.getByText("Falha ao carregar")).toBeInTheDocument();
        await userEvent.setup().click(screen.getByText("Tentar novamente"));
        expect(recarregar).toHaveBeenCalled();
    });

    it("mostra estado vazio quando não há categorias", () => {
        mockUseCardapioDoDia.mockReturnValue({
            cardapio: { data: "2026-09-15", categorias: [] },
            carregando: false,
            erro: null,
            recarregar: vi.fn(),
        });
        renderPagina();
        expect(
            screen.getByText("nenhum cardápio disponível hoje"),
        ).toBeInTheDocument();
    });

    it("renderiza os itens e mantém o botão desabilitado sem seleção", () => {
        mockUseCardapioDoDia.mockReturnValue({
            cardapio: CARDAPIO_MOCK,
            carregando: false,
            erro: null,
            recarregar: vi.fn(),
        });
        renderPagina();

        expect(screen.getByText("Arroz Branco")).toBeInTheDocument();
        expect(screen.getByText("Selecione ao menos um item")).toBeDisabled();
    });

    it("habilita o botão e navega pra /revisao com itens selecionados", async () => {
        mockUseCardapioDoDia.mockReturnValue({
            cardapio: CARDAPIO_MOCK,
            carregando: false,
            erro: null,
            recarregar: vi.fn(),
        });
        mockUseCarrinho.mockReturnValue({
            getQuantidade: () => 1,
            definirQuantidade: vi.fn(),
            totalItens: 1,
        });
        renderPagina();

        const botao = screen.getByText("Continuar · 1 item");
        expect(botao).toBeEnabled();

        await userEvent.setup().click(botao);
        expect(mockNavigate).toHaveBeenCalledWith("/revisao");
    });

    it("clicar em + chama definirQuantidade com o item e a quantidade incrementada", async () => {
        const definirQuantidade = vi.fn();
        mockUseCardapioDoDia.mockReturnValue({
            cardapio: CARDAPIO_MOCK,
            carregando: false,
            erro: null,
            recarregar: vi.fn(),
        });
        mockUseCarrinho.mockReturnValue({
            getQuantidade: () => 0,
            definirQuantidade,
            totalItens: 0,
        });
        renderPagina();

        await userEvent.setup().click(screen.getByText("+ Arroz Branco"));

        expect(definirQuantidade).toHaveBeenCalledWith(
            { id: "item-1", name: "Arroz Branco", catName: "Arroz", price: 8 },
            1,
        );
    });
});
