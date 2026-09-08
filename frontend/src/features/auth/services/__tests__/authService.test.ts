import { describe, it, expect, vi } from "vitest";
import { loginAdmin } from "../authService";
import { adminApi } from "../../../../shared/api/adminApi";

vi.mock("../../../../shared/api/adminApi", () => ({
    adminApi: { post: vi.fn() },
}));

describe("authService.loginAdmin", () => {
    it("chama POST /auth/login/admin com o payload e retorna os dados da resposta", async () => {
        const payload = { login: "marcos@devdelivery.com", password: "123456" };
        const responseData = { access_token: "token-123", expires_in: 3600 };
        (adminApi.post as any).mockResolvedValue({ data: responseData });

        const result = await loginAdmin(payload);

        expect(adminApi.post).toHaveBeenCalledWith("/auth/login/admin", payload);
        expect(result).toEqual(responseData);
    });

    it("propaga o erro quando a requisição falha", async () => {
        const error = { response: { status: 401 } };
        (adminApi.post as any).mockRejectedValue(error);

        await expect(loginAdmin({ login: "x", password: "y" })).rejects.toBe(error);
    });
});