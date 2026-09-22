import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import EnderecosPage from "../EnderecosPage";
import { useEnderecos } from "../../hooks/useEnderecos";
import { buscarCoordenadasPorEndereco } from "@/features/cliente/services/geocodingService";

vi.mock("../../hooks/useEnderecos");
vi.mock("@/features/cliente/services/geocodingService");

const baseEndereco = {
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

describe("EnderecosPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(buscarCoordenadasPorEndereco).mockResolvedValue({
            latitude: -7.3196,
            longitude: -35.1119,
        });
    });

    it("mostra o estado de carregamento", () => {
        mockHook({ loading: true });
        render(<EnderecosPage />);
        expect(
            screen.getByText("Carregando seus endereços..."),
        ).toBeInTheDocument();
    });

    it("mostra erro com botão de tentar novamente", () => {
        const recarregar = vi.fn();
        mockHook({
            error: "Não foi possível carregar seus endereços.",
            recarregar,
        });
        render(<EnderecosPage />);
        fireEvent.click(
            screen.getByRole("button", { name: /Tentar novamente/ }),
        );
        expect(recarregar).toHaveBeenCalled();
    });

    it("mostra o estado vazio quando não há endereços", () => {
        mockHook({ enderecos: [] });
        render(<EnderecosPage />);
        expect(
            screen.getByText("Nenhum endereço cadastrado"),
        ).toBeInTheDocument();
    });

    it("lista os endereços existentes com o selo de padrão", () => {
        mockHook({ enderecos: [baseEndereco] });
        render(<EnderecosPage />);
        expect(screen.getByText(/Rua A, 10/)).toBeInTheDocument();
        expect(screen.getByText("Padrão")).toBeInTheDocument();
    });

    it("exclui um endereço e mostra feedback de sucesso", async () => {
        const remover = vi.fn().mockResolvedValue(undefined);
        mockHook({
            enderecos: [{ ...baseEndereco, primary_address: false }],
            remover,
        });
        render(<EnderecosPage />);
        fireEvent.click(screen.getByRole("button", { name: /Excluir/ }));
        await waitFor(() => expect(remover).toHaveBeenCalledWith("1"));
        expect(
            await screen.findByText("Endereço removido."),
        ).toBeInTheDocument();
    });

    it("define um endereço como padrão", async () => {
        const definirPadrao = vi.fn().mockResolvedValue(undefined);
        mockHook({
            enderecos: [{ ...baseEndereco, primary_address: false }],
            definirPadrao,
        });
        render(<EnderecosPage />);
        fireEvent.click(
            screen.getByRole("button", { name: /Definir como padrão/ }),
        );
        await waitFor(() => expect(definirPadrao).toHaveBeenCalledWith("1"));
        expect(
            await screen.findByText("Endereço definido como padrão."),
        ).toBeInTheDocument();
    });

    it("abre o formulário de novo endereço e envia os dados", async () => {
        const adicionar = vi
            .fn()
            .mockResolvedValue({ ...baseEndereco, id: "2" });
        mockHook({ enderecos: [], adicionar });
        render(<EnderecosPage />);
        fireEvent.click(
            screen.getByRole("button", { name: /Adicionar endereço/ }),
        );
        fireEvent.change(screen.getByLabelText("Rua"), {
            target: { value: "Rua Nova" },
        });
        fireEvent.change(screen.getByLabelText("Número"), {
            target: { value: "99" },
        });
        fireEvent.change(screen.getByLabelText("Bairro"), {
            target: { value: "Bairro Novo" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Adicionar" }));

        // handleSubmit agora é assíncrono (passa pelo geocoding
        // antes de chamar onSubmit quando não há lat/long capturada)
        await waitFor(() => expect(adicionar).toHaveBeenCalled());

        expect(
            await screen.findByText("Endereço adicionado com sucesso!"),
        ).toBeInTheDocument();
    });
});