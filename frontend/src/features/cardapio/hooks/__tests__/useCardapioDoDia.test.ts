import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useRestauranteInfo } from "@/features/cliente/hooks/useRestauranteInfo";
import { obterCardapioDoDia } from "../../services/cardapioService";
import { useCardapioDoDia } from "../useCardapioDoDia";

vi.mock("@/features/cliente/hooks/useRestauranteInfo", () => ({
    useRestauranteInfo: vi.fn(),
}));

vi.mock("../../services/cardapioService", () => ({
    obterCardapioDoDia: vi.fn(),
}));

const CARDAPIO_FAKE = { data: "2026-09-12", categorias: [] };

describe("useCardapioDoDia", () => {
    beforeEach(() => {
        vi.mocked(useRestauranteInfo).mockReset();
        vi.mocked(obterCardapioDoDia).mockReset();
    });

    it("fica carregando enquanto o restaurante ainda está carregando", () => {
        vi.mocked(useRestauranteInfo).mockReturnValue({
            restaurante: null,
            loading: true,
        });

        const { result } = renderHook(() => useCardapioDoDia());

        expect(result.current.carregando).toBe(true);
        expect(obterCardapioDoDia).not.toHaveBeenCalled();
    });

    it("seta erro quando o restaurante não foi encontrado", async () => {
        vi.mocked(useRestauranteInfo).mockReturnValue({
            restaurante: null,
            loading: false,
        });

        const { result } = renderHook(() => useCardapioDoDia());

        await waitFor(() => expect(result.current.carregando).toBe(false));
        expect(result.current.erro).toBe(
            "Não foi possível identificar o restaurante.",
        );
        expect(obterCardapioDoDia).not.toHaveBeenCalled();
    });

    it("busca o cardápio quando o restaurante existe", async () => {
        vi.mocked(useRestauranteInfo).mockReturnValue({
            restaurante: {
                id: "restaurante-123",
                trade_name: "Marmita Boa",
                phone: "",
                is_active: true,
            },
            loading: false,
        });
        vi.mocked(obterCardapioDoDia).mockResolvedValue(CARDAPIO_FAKE);

        const { result } = renderHook(() => useCardapioDoDia());

        await waitFor(() => expect(result.current.carregando).toBe(false));
        expect(obterCardapioDoDia).toHaveBeenCalledWith("restaurante-123");
        expect(result.current.cardapio).toEqual(CARDAPIO_FAKE);
        expect(result.current.erro).toBeNull();
    });

    it("seta erro quando a busca do cardápio falha", async () => {
        vi.mocked(useRestauranteInfo).mockReturnValue({
            restaurante: {
                id: "restaurante-123",
                trade_name: "Marmita Boa",
                phone: "",
                is_active: true,
            },
            loading: false,
        });
        vi.mocked(obterCardapioDoDia).mockRejectedValue(new Error("falhou"));

        const { result } = renderHook(() => useCardapioDoDia());

        await waitFor(() => expect(result.current.carregando).toBe(false));
        expect(result.current.erro).toBe(
            "Não foi possível carregar o cardápio de hoje. Tente novamente.",
        );
        expect(result.current.cardapio).toBeNull();
    });

    it("recarregar() dispara uma nova busca", async () => {
        vi.mocked(useRestauranteInfo).mockReturnValue({
            restaurante: {
                id: "restaurante-123",
                trade_name: "Marmita Boa",
                phone: "",
                is_active: true,
            },
            loading: false,
        });
        vi.mocked(obterCardapioDoDia).mockResolvedValue(CARDAPIO_FAKE);

        const { result } = renderHook(() => useCardapioDoDia());
        await waitFor(() => expect(result.current.carregando).toBe(false));

        act(() => result.current.recarregar());

        await waitFor(() =>
            expect(obterCardapioDoDia).toHaveBeenCalledTimes(2),
        );
    });
});
