import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import EnderecoPage from "../EnderecoPage";
import { useEnderecos } from "@/features/cliente/hooks/useEnderecos";

vi.mock("@/features/cliente/hooks/useEnderecos");

const navigateMock = vi.fn();
vi.mock("react-router-dom", async () => {
    const actual =
        await vi.importActual<typeof import("react-router-dom")>(
            "react-router-dom",
        );
    return {
        ...actual,
        useNavigate: () => navigateMock,
        useLocation: () => ({
            state: { cartItems: [{ id: "i1", name: "Marmita", quantity: 1 }] },
        }),
    };
});

const endereco = {
    id: "1",
    client_id: "c1",
    created_at: "2026-01-01T00:00:00Z",
    street: "Rua A",
    number: "10",
    neighborhood: "Centro",
    complement: "",
    reference_point: "",
    primary_address: true,
    latitude: null,
    longitude: null,
};

function mockHook(overrides = {}) {
    vi.mocked(useEnderecos).mockReturnValue({
        enderecos: [],
        loading: false,
        error: null,
        recarregar: vi.fn(),
        adicionar: vi.fn(),
        atualizar: vi.fn(),
        remover: vi.fn(),
        definirPadrao: vi.fn(),
        ...overrides,
    });
}

function renderPage() {
    return render(
        <MemoryRouter>
            <EnderecoPage />
        </MemoryRouter>,
    );
}

describe("EnderecoPage", () => {
    beforeEach(() => vi.clearAllMocks());

    it("mostra estado de carregamento", () => {
        mockHook({ loading: true });
        renderPage();
        expect(
            screen.getByText("Carregando seus endereços..."),
        ).toBeInTheDocument();
    });

    it("seleciona automaticamente o endereço padrão e permite continuar", async () => {
        const definirPadrao = vi.fn();
        mockHook({ enderecos: [endereco], definirPadrao });
        renderPage();
        fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
        await waitFor(() =>
            expect(navigateMock).toHaveBeenCalledWith("/pedido/pagamento", {
                state: {
                    cartItems: [{ id: "i1", name: "Marmita", quantity: 1 }],
                    address: endereco,
                },
            }),
        );
        expect(definirPadrao).not.toHaveBeenCalled();
    });

    it("marca como padrão o endereço escolhido antes de continuar, se não era o padrão", async () => {
        const secundario = {
            ...endereco,
            id: "2",
            street: "Rua B",
            number: "20",
            primary_address: false,
        };
        const definirPadrao = vi.fn().mockResolvedValue(undefined);
        mockHook({ enderecos: [endereco, secundario], definirPadrao });
        renderPage();
        fireEvent.click(screen.getByText("Rua B, 20"));
        fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
        await waitFor(() => expect(definirPadrao).toHaveBeenCalledWith("2"));
    });

    it("mostra o formulário quando não há endereços salvos", () => {
        mockHook({ enderecos: [] });
        renderPage();
        expect(
            screen.getByText("Nenhum endereço cadastrado"),
        ).toBeInTheDocument();
    });
});
