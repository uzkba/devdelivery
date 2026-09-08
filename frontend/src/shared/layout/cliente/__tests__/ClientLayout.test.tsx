import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ClientLayout from "../ClientLayout";
import { useRestauranteInfo } from "../../../../features/cliente/hooks/useRestauranteInfo";
import { usePedidoEmAndamento } from "../../../../features/cliente/hooks/usePedidoEmAndamento";

vi.mock("../../../../features/cliente/hooks/useRestauranteInfo", () => ({
    useRestauranteInfo: vi.fn(),
}));
vi.mock("../../../../features/cliente/hooks/usePedidoEmAndamento", () => ({
    usePedidoEmAndamento: vi.fn(),
}));

const mockedUseRestauranteInfo = useRestauranteInfo as unknown as ReturnType<typeof vi.fn>;
const mockedUsePedidoEmAndamento = usePedidoEmAndamento as unknown as ReturnType<typeof vi.fn>;

function renderComLayout(initialPath: string) {
    return render(
        <MemoryRouter initialEntries={[initialPath]}>
            <Routes>
                <Route element={<ClientLayout />}>
                    <Route path="/" element={<div>Conteúdo Início</div>} />
                    <Route path="/cardapio" element={<div>Conteúdo Cardápio</div>} />
                    <Route path="/pedido/endereco" element={<div>Conteúdo Endereço</div>} />
                    <Route path="/pedido/pagamento" element={<div>Conteúdo Pagamento</div>} />
                    <Route path="/pedidos" element={<div>Conteúdo Pedidos</div>} />
                    <Route path="/pedidos/:id" element={<div>Conteúdo Detalhe do Pedido</div>} />
                    <Route path="/conta" element={<div>Conteúdo Conta</div>} />
                </Route>
            </Routes>
        </MemoryRouter>,
    );
}

describe("ClientLayout", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockedUseRestauranteInfo.mockReturnValue({ restaurante: null, loading: false });
        mockedUsePedidoEmAndamento.mockReturnValue(null);
    });

    it('mostra o título correto pra rota atual', () => {
        renderComLayout("/cardapio");
        expect(screen.getByRole("heading", { name: "Monte sua marmita" })).toBeInTheDocument();
    });

    it("mostra o nome do restaurante vindo da API na tela inicial", () => {
        mockedUseRestauranteInfo.mockReturnValue({
            restaurante: { id: "1", trade_name: "Marmitaria Sabor & Arte", phone: "11999999999", is_active: true },
            loading: false,
        });
        renderComLayout("/");
        expect(screen.getByText("Marmitaria Sabor & Arte")).toBeInTheDocument();
    });

    it('usa "DevDelivery" como fallback quando não há restaurante carregado', () => {
        renderComLayout("/");
        expect(screen.getByText("DevDelivery")).toBeInTheDocument();
    });

    it("não mostra botão Voltar na tela inicial", () => {
        renderComLayout("/");
        expect(screen.queryByText("Voltar")).not.toBeInTheDocument();
    });

    it("mostra botão Voltar e navega pra rota correta ao clicar", () => {
        renderComLayout("/cardapio");
        fireEvent.click(screen.getByText("Voltar"));
        expect(screen.getByText("Conteúdo Início")).toBeInTheDocument();
    });

    it('mostra título "Acompanhar pedido" e esconde a navegação inferior no detalhe do pedido', () => {
        renderComLayout("/pedidos/123");
        expect(screen.getByRole("heading", { name: "Acompanhar pedido" })).toBeInTheDocument();
        expect(screen.queryByText("Início")).not.toBeInTheDocument();
    });

    it("no detalhe do pedido, o botão Voltar aponta pra /pedidos", () => {
        renderComLayout("/pedidos/123");
        fireEvent.click(screen.getByText("Voltar"));
        expect(screen.getByText("Conteúdo Pedidos")).toBeInTheDocument();
    });

    it("esconde a navegação inferior durante o checkout", () => {
        renderComLayout("/pedido/endereco");
        expect(screen.queryByText("Início")).not.toBeInTheDocument();
    });

    it("mostra a navegação inferior fora do checkout", () => {
        renderComLayout("/cardapio");
        expect(screen.getByText("Início")).toBeInTheDocument();
        expect(screen.getByText("Cardápio")).toBeInTheDocument();
        expect(screen.getByText("Pedidos")).toBeInTheDocument();
        expect(screen.getByText("Conta")).toBeInTheDocument();
    });

    it("mostra os passos do checkout nas rotas de checkout", () => {
        renderComLayout("/pedido/endereco");
        expect(screen.getByText("Endereço")).toBeInTheDocument();
        expect(screen.getByText("Pagamento")).toBeInTheDocument();
        expect(screen.getByText("Revisão")).toBeInTheDocument();
    });

    it("não mostra os passos do checkout fora do fluxo de checkout", () => {
        renderComLayout("/cardapio");
        expect(screen.queryByText("Revisão")).not.toBeInTheDocument();
    });

    it("renderiza o conteúdo da rota filha via Outlet", () => {
        renderComLayout("/conta");
        expect(screen.getByText("Conteúdo Conta")).toBeInTheDocument();
    });

    it("mostra o indicador na aba Pedidos quando há um pedido em andamento", () => {
        mockedUsePedidoEmAndamento.mockReturnValue({
            id: "1",
            numero_pedido: 10,
            status: { code: "EM_PREPARACAO", name: "Em preparação", is_final: false },
            data_hora: "",
            valor_total: 20,
        });
        const { container } = renderComLayout("/cardapio");
        expect(container.querySelector(".w-2.h-2.rounded-full")).toBeInTheDocument();
    });

    it("não mostra o indicador quando não há pedido em andamento", () => {
        const { container } = renderComLayout("/cardapio");
        expect(container.querySelector(".w-2.h-2.rounded-full")).not.toBeInTheDocument();
    });
});