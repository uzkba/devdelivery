import { describe, it, expect, vi } from "vitest";
import { loginCliente } from "../clienteAuthService";
import { clientApi } from "../../../../shared/api/clientApi";

vi.mock("../../../../shared/api/clientApi", () => ({
    clientApi: { post: vi.fn() },
}));

describe("clienteAuthService.loginCliente", () => {
    it("chama POST /clientes/login com o payload e retorna os dados da resposta", async () => {
        const payload = { phone: "84999999999", password: "123456" };
        const responseData = {
            access_token: "token-cliente-123",
            expires_in: 3600,
        };
        (clientApi.post as any).mockResolvedValue({ data: responseData });

        const result = await loginCliente(payload);

        expect(clientApi.post).toHaveBeenCalledWith("/clientes/login", payload);
        expect(result).toEqual(responseData);
    });

    it("propaga o erro 401 quando telefone/senha são inválidos", async () => {
        const error = { response: { status: 401 } };
        (clientApi.post as any).mockRejectedValue(error);

        await expect(loginCliente({ phone: "x", password: "y" })).rejects.toBe(
        error,
        );
    });

    it("propaga o erro 403 quando o cliente está inativo", async () => {
        const error = { response: { status: 403 } };
        (clientApi.post as any).mockRejectedValue(error);

        await expect(
            loginCliente({ phone: "84999999999", password: "123456" }),
        ).rejects.toBe(error);
    });
});
