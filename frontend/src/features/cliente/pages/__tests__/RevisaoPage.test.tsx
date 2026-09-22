import { describe, it, expect, vi, beforeEach } from "vitest";
import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
    const actual = await vi.importActual("react-router-dom");
    return { ...actual, useNavigate: () => mockNavigate };
});

const mockUseCarrinho = vi.fn();
vi.mock("@/features/pedido/contexts/CarrinhoContexts", () => ({
    useCarrinho: () => mockUseCarrinho(),
}));

const mockUseEnderecos = vi.fn();
vi.mock("@/features/cliente/hooks/useEnderecos", () => ({
    useEnderecos: () => mockUseEnderecos(),
}));

const mockUseRestauranteInfo = vi.fn();
vi.mock("@/features/cliente/hooks/useRestauranteInfo", () => ({
    useRestauranteInfo: () => mockUseRestauranteInfo(),
}));

const mockCriarPedido = vi.fn();
vi.mock("@/features/pedido/services/pedidoService", () => ({
    criarPedido: (...args: any[]) => mockCriarPedido(...args),
}));

vi.mock("@/features/pedido/utils/sugestoesValoresTroco", () => ({
    suggestChangeAmounts: () => [20, 50, 100],
}));

vi.mock("@/features/cliente/components/EnderecoForm", () => ({
    default: (props: any) => (
        <div>
            {props.errorMessage && <p>{props.errorMessage}</p>}
            <button
                onClick={() =>
                    props.onSubmit({
                        street: "Rua Nova",
                        number: "99",
                        neighborhood: "Centro",
                    })
                }
                disabled={props.submitting}
            >
                {props.submitLabel}
            </button>
            <button onClick={props.onCancel}>Cancelar form</button>
        </div>
    ),
}));

import RevisaoPage from "../RevisaoPage";

function fmtMoney(n: number) {
    return n
        .toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
        .replace(/[\u00A0\u202F]/g, " "); // normaliza o espaço especial do Intl pra espaço comum
}

const ITENS_CARRINHO = [
    { id: "item-1", name: "Arroz Branco", catName: "Arroz", price: 8, qty: 2 },
];

const ENDERECOS = [
    {
        id: "end-1",
        street: "Rua A",
        number: "10",
        neighborhood: "Centro",
        complement: null,
        reference_point: null,
        primary_address: true,
        latitude: null,
        longitude: null,
    },
    {
        id: "end-2",
        street: "Rua B",
        number: "20",
        neighborhood: "Bairro",
        complement: null,
        reference_point: null,
        primary_address: false,
        latitude: null,
        longitude: null,
    },
];

function renderPagina() {
    return render(
        <MemoryRouter>
            <RevisaoPage />
        </MemoryRouter>,
    );
}

describe("RevisaoPage", () => {
    beforeEach(() => {
        mockNavigate.mockClear();
        mockCriarPedido.mockReset();
        mockUseCarrinho.mockReturnValue({
            itens: ITENS_CARRINHO,
            subtotal: 16,
            limparCarrinho: vi.fn(),
        });
        mockUseEnderecos.mockReturnValue({
            enderecos: ENDERECOS,
            loading: false,
            adicionar: vi.fn(),
        });
        mockUseRestauranteInfo.mockReturnValue({
            restaurante: {
                id: "rest-1",
                trade_name: "DevDelivery",
                phone: "123",
                is_active: true,
            },
        });
    });

    it("mostra os itens do carrinho e o total (subtotal + entrega)", () => {
        renderPagina();
        expect(screen.getByText("Arroz Branco")).toBeInTheDocument();
        expect(screen.getByText("x 2")).toBeInTheDocument();
        expect(screen.getByText(fmtMoney(21))).toBeInTheDocument(); // 16 + 5
    });

    it("navega pro cardápio ao clicar em Alterar nos itens", async () => {
        renderPagina();
        await userEvent.setup().click(screen.getByText("Alterar"));
        expect(mockNavigate).toHaveBeenCalledWith("/cardapio");
    });

    it("pré-seleciona o endereço padrão", () => {
        renderPagina();
        expect(screen.getByText("Rua A, 10")).toBeInTheDocument();
    });

    it("expande a seção de endereço e permite trocar a seleção", async () => {
        const user = userEvent.setup();
        renderPagina();

        await user.click(screen.getByText("Rua A, 10"));
        expect(screen.getByText(/Rua B, 20/)).toBeInTheDocument();

        await user.click(screen.getByText(/Rua B, 20/));
        expect(screen.getByText("Rua B, 20")).toBeInTheDocument();
    });

    it("adiciona um novo endereço pelo form inline e reflete no resumo", async () => {
        const novoEndereco = {
            id: "end-3",
            street: "Rua Nova",
            number: "99",
            neighborhood: "Centro",
            complement: null,
            reference_point: null,
            primary_address: false,
            latitude: null,
            longitude: null,
        };
        mockUseEnderecos.mockImplementation(() => {
            const [enderecos, setEnderecos] = useState(ENDERECOS);
            return {
                enderecos,
                loading: false,
                adicionar: vi.fn(async () => {
                    setEnderecos((prev) => [...prev, novoEndereco]);
                    return novoEndereco;
                }),
            };
        });

        const user = userEvent.setup();
        renderPagina();

        await user.click(screen.getByText("Rua A, 10"));
        await user.click(screen.getByText("Adicionar novo endereço"));
        await user.click(screen.getByText("Salvar endereço"));

        await waitFor(() =>
            expect(screen.getByText("Rua Nova, 99")).toBeInTheDocument(),
        );
    });

    it("mostra erro se salvar o novo endereço falhar", async () => {
        const adicionar = vi.fn().mockRejectedValue(new Error("falhou"));
        mockUseEnderecos.mockReturnValue({
            enderecos: ENDERECOS,
            loading: false,
            adicionar,
        });
        const user = userEvent.setup();
        renderPagina();

        await user.click(screen.getByText("Rua A, 10"));
        await user.click(screen.getByText("Adicionar novo endereço"));
        await user.click(screen.getByText("Salvar endereço"));

        await waitFor(() =>
            expect(
                screen.getByText(
                    "Não foi possível salvar o endereço. Tente novamente.",
                ),
            ).toBeInTheDocument(),
        );
    });

    it("seleciona Dinheiro e calcula o troco corretamente", async () => {
        const user = userEvent.setup();
        renderPagina();

        await user.click(screen.getByText("Selecionar forma de pagamento"));
        await user.click(screen.getByText("Dinheiro"));

        await user.type(screen.getByPlaceholderText(fmtMoney(21)), "30");

        expect(screen.getByText(fmtMoney(9))).toBeInTheDocument();
    });

    it('mostra "sem troco" quando o valor pago é exato', async () => {
        const user = userEvent.setup();
        renderPagina();

        await user.click(screen.getByText("Selecionar forma de pagamento"));
        await user.click(screen.getByText("Dinheiro"));
        await user.type(screen.getByPlaceholderText(fmtMoney(21)), "21");

        expect(screen.getByText("Valor exato — sem troco")).toBeInTheDocument();
    });

    it("mantém Confirmar pedido desabilitado com Dinheiro e valor insuficiente", async () => {
        const user = userEvent.setup();
        renderPagina();

        await user.click(screen.getByText("Selecionar forma de pagamento"));
        await user.click(screen.getByText("Dinheiro"));
        await user.type(screen.getByPlaceholderText(fmtMoney(21)), "10");

        expect(screen.getByText("Confirmar pedido")).toBeDisabled();
    });

    it("mostra a alternância Crédito/Débito ao escolher Cartão", async () => {
        const user = userEvent.setup();
        renderPagina();

        await user.click(screen.getByText("Selecionar forma de pagamento"));
        await user.click(screen.getByText("Cartão"));

        expect(screen.getByText("Crédito")).toBeInTheDocument();
        expect(screen.getByText("Débito")).toBeInTheDocument();
    });

    it("Confirmar pedido fica desabilitado sem forma de pagamento selecionada", () => {
        renderPagina();
        expect(screen.getByText("Confirmar pedido")).toBeDisabled();
    });

    it("confirma o pedido com Pix: cria o pedido, limpa o carrinho e navega", async () => {
        const limparCarrinho = vi.fn();
        mockUseCarrinho.mockReturnValue({
            itens: ITENS_CARRINHO,
            subtotal: 16,
            limparCarrinho,
        });
        mockCriarPedido.mockResolvedValue({
            id: "pedido-1",
            numero_pedido: 42,
        });

        const user = userEvent.setup();
        renderPagina();

        await user.click(screen.getByText("Selecionar forma de pagamento"));
        await user.click(screen.getByText("Pix"));

        const botaoConfirmar = screen.getByText("Confirmar pedido");
        expect(botaoConfirmar).toBeEnabled();
        await user.click(botaoConfirmar);

        await waitFor(() =>
            expect(mockCriarPedido).toHaveBeenCalledWith({
                restaurante_id: "rest-1",
                itens: [{ alimento_id: "item-1", quantidade: 2 }],
                endereco_id: "end-1",
                forma_pagamento: "PIX",
                valor_pago_dinheiro: undefined,
                observacoes: undefined,
            }),
        );
        expect(limparCarrinho).toHaveBeenCalled();
        expect(mockNavigate).toHaveBeenCalledWith("/pedido-confirmado", {
            state: { numero: 42 },
        });
    });

    it("mostra mensagem de erro se a criação do pedido falhar, sem navegar", async () => {
        mockCriarPedido.mockRejectedValue(new Error("erro de rede"));
        const user = userEvent.setup();
        renderPagina();

        await user.click(screen.getByText("Selecionar forma de pagamento"));
        await user.click(screen.getByText("Pix"));
        await user.click(screen.getByText("Confirmar pedido"));

        await waitFor(() =>
            expect(
                screen.getByText(
                    "Não deu pra confirmar o pedido agora. Tente novamente em instantes.",
                ),
            ).toBeInTheDocument(),
        );
        expect(mockNavigate).not.toHaveBeenCalledWith(
            "/pedido-confirmado",
            expect.anything(),
        );
    });

    it("inclui observações no payload quando preenchidas", async () => {
        mockCriarPedido.mockResolvedValue({
            id: "pedido-1",
            numero_pedido: 42,
        });
        const user = userEvent.setup();
        renderPagina();

        await user.type(
            screen.getByPlaceholderText(/Sem cebola/),
            "Sem cebola por favor",
        );
        await user.click(screen.getByText("Selecionar forma de pagamento"));
        await user.click(screen.getByText("Pix"));
        await user.click(screen.getByText("Confirmar pedido"));

        await waitFor(() =>
            expect(mockCriarPedido).toHaveBeenCalledWith(
                expect.objectContaining({
                    observacoes: "Sem cebola por favor",
                }),
            ),
        );
    });
});
