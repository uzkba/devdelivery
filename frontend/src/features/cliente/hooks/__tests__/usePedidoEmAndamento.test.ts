import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { usePedidoEmAndamento } from "../usePedidoEmAndamento";
import { clientApi } from "../../../../shared/api/clientApi";
import { useClienteAuth } from "@/shared/auth/ClienteAuthContext";

vi.mock("../../../../shared/api/clientApi", () => ({
    clientApi: { get: vi.fn() },
}));

vi.mock("@/shared/auth/ClienteAuthContext", () => ({
    useClienteAuth: vi.fn(),
}));

const mockedGet = clientApi.get as unknown as ReturnType<typeof vi.fn>;
const mockedUseClienteAuth = useClienteAuth as unknown as ReturnType<typeof vi.fn>;

describe("usePedidoEmAndamento", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("não chama a API quando o cliente não está autenticado", () => {
        mockedUseClienteAuth.mockReturnValue({ isAuthenticated: false });

        const { result } = renderHook(() => usePedidoEmAndamento());

        expect(result.current).toBeNull();
        expect(mockedGet).not.toHaveBeenCalled();
    });

    it("retorna o pedido cujo status.is_final é false", async () => {
        mockedUseClienteAuth.mockReturnValue({ isAuthenticated: true });
        mockedGet.mockResolvedValueOnce({
            data: {
                items: [
                    {
                        id: "1",
                        numero_pedido: 10,
                        status: {
                            code: "ENTREGUE",
                            name: "Entregue",
                            is_final: true,
                        },
                        data_hora: "",
                        valor_total: 30,
                    },
                    {
                        id: "2",
                        numero_pedido: 11,
                        status: {
                            code: "EM_PREPARACAO",
                            name: "Em preparação",
                            is_final: false,
                        },
                        data_hora: "",
                        valor_total: 20,
                    },
                ],
                total: 2,
            },
        });

        const { result } = renderHook(() => usePedidoEmAndamento());

        await waitFor(() => expect(result.current?.id).toBe("2"));
        expect(mockedGet).toHaveBeenCalledWith("/pedidos/me", {
            params: { page: 1, page_size: 5 },
        });
    });

    it("retorna null quando todos os pedidos estão em status final", async () => {
        mockedUseClienteAuth.mockReturnValue({ isAuthenticated: true });
        mockedGet.mockResolvedValueOnce({
            data: {
                items: [
                    {
                        id: "1",
                        numero_pedido: 10,
                        status: {
                            code: "ENTREGUE",
                            name: "Entregue",
                            is_final: true,
                        },
                        data_hora: "",
                        valor_total: 30,
                    },
                ],
                total: 1,
            },
        });

        const { result } = renderHook(() => usePedidoEmAndamento());

        await waitFor(() => expect(mockedGet).toHaveBeenCalled());
        expect(result.current).toBeNull();
    });

    it("retorna null quando a chamada falha", async () => {
        mockedUseClienteAuth.mockReturnValue({ isAuthenticated: true });
        mockedGet.mockRejectedValueOnce(new Error("erro de rede"));

        const { result } = renderHook(() => usePedidoEmAndamento());

        await waitFor(() => expect(mockedGet).toHaveBeenCalled());
        expect(result.current).toBeNull();
    });

    it("busca novamente a cada 30 segundos enquanto autenticado", async () => {
        vi.useFakeTimers();
        mockedUseClienteAuth.mockReturnValue({ isAuthenticated: true });
        mockedGet.mockResolvedValue({ data: { items: [], total: 0 } });

        renderHook(() => usePedidoEmAndamento());
        expect(mockedGet).toHaveBeenCalledTimes(1);

        await vi.advanceTimersByTimeAsync(30000);
        expect(mockedGet).toHaveBeenCalledTimes(2);

        vi.useRealTimers();
    });
});
