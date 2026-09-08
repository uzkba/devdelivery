import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useRestauranteInfo } from "../useRestauranteInfo";
import { clientApi } from "../../../../shared/api/clientApi";

vi.mock("../../../../shared/api/clientApi", () => ({
    clientApi: { get: vi.fn() },
}));

const mockedGet = clientApi.get as unknown as ReturnType<typeof vi.fn>;

describe("useRestauranteInfo", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("carrega os dados do restaurante com sucesso", async () => {
        mockedGet.mockResolvedValueOnce({
            data: {
                id: "1",
                trade_name: "Marmitaria Sabor & Arte",
                phone: "11999999999",
                is_active: true,
            },
        });

        const { result } = renderHook(() => useRestauranteInfo());

        expect(result.current.loading).toBe(true);

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.restaurante?.trade_name).toBe(
            "Marmitaria Sabor & Arte",
        );
        expect(mockedGet).toHaveBeenCalledWith("/restaurante");
    });

    it("mantém restaurante como null quando a chamada falha (ex: 404 sem restaurante ativo)", async () => {
        mockedGet.mockRejectedValueOnce(new Error("404"));

        const { result } = renderHook(() => useRestauranteInfo());

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.restaurante).toBeNull();
    });
});
