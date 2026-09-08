import { describe, it, expect, vi } from "vitest";
import { loginCliente, registrarCliente } from "../clienteAuthService";
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

describe("clienteAuthService.registrarCliente", () => {
    it("chama POST /clientes/registrar com o payload e retorna os dados do cliente criado", async () => {
        const payload = {
            name: "Maria Silva",
            phone: "84999999999",
            password: "123456",
        };
        const responseData = {
            id: "cliente-1",
            name: "Maria Silva",
            phone: "84999999999",
            is_active: true,
        };
        (clientApi.post as any).mockResolvedValue({ data: responseData });

        const result = await registrarCliente(payload);

        expect(clientApi.post).toHaveBeenCalledWith("/clientes/registrar", payload);
        expect(result).toEqual(responseData);
    });

    it("propaga o erro 409 quando o telefone já está cadastrado", async () => {
        const error = { response: { status: 409 } };
        (clientApi.post as any).mockRejectedValue(error);

        await expect(
            registrarCliente({
                name: "Maria Silva",
                phone: "84999999999",
                password: "123456",
            }),
        ).rejects.toBe(error);
    });

    it("propaga o erro 422 quando os dados são inválidos", async () => {
        const error = { response: { status: 422 } };
        (clientApi.post as any).mockRejectedValue(error);

        await expect(
            registrarCliente({ name: "Jo", phone: "123", password: "123" }),
        ).rejects.toBe(error);
    });
});