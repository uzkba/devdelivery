import { describe, expect, it, vi, beforeEach } from "vitest";
import { clientApi } from "@/shared/api/clientApi";
import { buscarCardapioDoDia } from "../cardapioApi";

vi.mock("@/shared/api/clientApi", () => ({
    clientApi: { get: vi.fn() },
}));

describe("buscarCardapioDoDia", () => {
    beforeEach(() => {
        vi.mocked(clientApi.get).mockReset();
    });

    it("chama o endpoint correto com o restauranteId", async () => {
        vi.mocked(clientApi.get).mockResolvedValue({
            data: { data: "2026-09-12", categorias: [] },
        });

        await buscarCardapioDoDia("restaurante-123");

        expect(clientApi.get).toHaveBeenCalledWith(
            "/restaurantes/restaurante-123/cardapio-do-dia",
        );
    });

    it("retorna o payload bruto da resposta", async () => {
        const payload = { data: "2026-09-12", categorias: [] };
        vi.mocked(clientApi.get).mockResolvedValue({ data: payload });

        const resultado = await buscarCardapioDoDia("restaurante-123");

        expect(resultado).toEqual(payload);
    });

    it("propaga erro quando a chamada falha", async () => {
        vi.mocked(clientApi.get).mockRejectedValue(new Error("falhou"));

        await expect(buscarCardapioDoDia("restaurante-123")).rejects.toThrow(
            "falhou",
        );
    });
});
