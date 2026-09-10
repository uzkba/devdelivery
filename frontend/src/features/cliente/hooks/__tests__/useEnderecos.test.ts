import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useEnderecos } from "../useEnderecos";
import * as enderecoService from "../../services/enderecoService";

vi.mock("../../services/enderecoService");

const mockEndereco = (overrides = {}) => ({
    id: "1",
    client_id: "c1",
    created_at: "2026-01-01T00:00:00Z",
    street: "Rua A",
    number: "10",
    neighborhood: "Centro",
    complement: "",
    reference_point: "",
    primary_address: false,
    latitude: null,
    longitude: null,
    ...overrides,
});

describe("useEnderecos", () => {
    beforeEach(() => vi.clearAllMocks());

    it("carrega os endereços ao montar", async () => {
        vi.mocked(enderecoService.listarEnderecos).mockResolvedValue([
            mockEndereco(),
        ]);
        const { result } = renderHook(() => useEnderecos());
        expect(result.current.loading).toBe(true);
        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.enderecos).toHaveLength(1);
        expect(result.current.error).toBeNull();
    });

    it("seta erro quando a listagem falha", async () => {
        vi.mocked(enderecoService.listarEnderecos).mockRejectedValue(
            new Error("fail"),
        );
        const { result } = renderHook(() => useEnderecos());
        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.error).toBe(
            "Não foi possível carregar seus endereços.",
        );
    });

    it("adicionar insere o novo endereço na lista", async () => {
        vi.mocked(enderecoService.listarEnderecos).mockResolvedValue([]);
        const novo = mockEndereco({ id: "2", street: "Rua Nova" });
        vi.mocked(enderecoService.criarEndereco).mockResolvedValue(novo);
        const { result } = renderHook(() => useEnderecos());
        await waitFor(() => expect(result.current.loading).toBe(false));
        await act(async () => {
            await result.current.adicionar({
                street: "Rua Nova",
                number: "1",
                neighborhood: "B",
            });
        });
        expect(result.current.enderecos).toContainEqual(novo);
    });

    it("atualizar substitui o endereço correspondente", async () => {
        const original = mockEndereco();
        vi.mocked(enderecoService.listarEnderecos).mockResolvedValue([
            original,
        ]);
        const atualizado = { ...original, neighborhood: "Novo Bairro" };
        vi.mocked(enderecoService.atualizarEndereco).mockResolvedValue(
            atualizado,
        );
        const { result } = renderHook(() => useEnderecos());
        await waitFor(() => expect(result.current.loading).toBe(false));
        await act(async () => {
            await result.current.atualizar("1", {
                neighborhood: "Novo Bairro",
            });
        });
        expect(result.current.enderecos[0].neighborhood).toBe("Novo Bairro");
    });

    it("remover tira o endereço da lista", async () => {
        vi.mocked(enderecoService.listarEnderecos).mockResolvedValue([
            mockEndereco(),
        ]);
        vi.mocked(enderecoService.removerEndereco).mockResolvedValue(undefined);
        const { result } = renderHook(() => useEnderecos());
        await waitFor(() => expect(result.current.loading).toBe(false));
        await act(async () => {
            await result.current.remover("1");
        });
        expect(result.current.enderecos).toHaveLength(0);
    });

    it("definirPadrao marca só o endereço escolhido como principal", async () => {
        const a = mockEndereco({ id: "1", primary_address: true });
        const b = mockEndereco({ id: "2", primary_address: false });
        vi.mocked(enderecoService.listarEnderecos).mockResolvedValue([a, b]);
        vi.mocked(enderecoService.definirEnderecoPadrao).mockResolvedValue({
            ...b,
            primary_address: true,
        });
        const { result } = renderHook(() => useEnderecos());
        await waitFor(() => expect(result.current.loading).toBe(false));
        await act(async () => {
            await result.current.definirPadrao("2");
        });
        expect(
            result.current.enderecos.find((e) => e.id === "1")?.primary_address,
        ).toBe(false);
        expect(
            result.current.enderecos.find((e) => e.id === "2")?.primary_address,
        ).toBe(true);
    });
});
