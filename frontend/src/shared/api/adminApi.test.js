import { describe, it, expect, beforeEach, afterEach } from "vitest";
import MockAdapter from "axios-mock-adapter";
import { adminApi } from "./adminApi";
import { adminTokenStorage } from "../auth/tokenStorage";
describe("adminApi - interceptors", () => {
    let mock;
    const originalLocation = window.location;
    beforeEach(() => {
        mock = new MockAdapter(adminApi);
        localStorage.clear();
        Object.defineProperty(window, "location", {
            writable: true,
            value: { ...originalLocation, href: "", pathname: "/painel" },
        });
    });
    afterEach(() => {
        mock.restore();
        Object.defineProperty(window, "location", { writable: true, value: originalLocation });
    });
    it("injeta Authorization quando há token salvo", async () => {
        adminTokenStorage.set("token-abc");
        mock.onGet("/rota").reply((config) => {
            expect(config.headers?.Authorization).toBe("Bearer token-abc");
            return [200, {}];
        });
        await adminApi.get("/rota");
    });
    it("não injeta Authorization quando não há token", async () => {
        mock.onGet("/rota").reply((config) => {
            expect(config.headers?.Authorization).toBeUndefined();
            return [200, {}];
        });
        await adminApi.get("/rota");
    });
    it("em 401: limpa o token e redireciona pro login", async () => {
        adminTokenStorage.set("token-expirado");
        mock.onGet("/rota-protegida").reply(401);
        await expect(adminApi.get("/rota-protegida")).rejects.toBeDefined();
        expect(adminTokenStorage.get()).toBeNull();
        expect(window.location.href).toBe("/login");
    });
    it("não redireciona de novo se já estiver na tela de login", async () => {
        window.location.pathname = "/login";
        mock.onGet("/rota-protegida").reply(401);
        await expect(adminApi.get("/rota-protegida")).rejects.toBeDefined();
        expect(window.location.href).toBe("");
    });
    it("em erro diferente de 401 (ex.: 500): não limpa o token nem redireciona", async () => {
        adminTokenStorage.set("token-valido");
        mock.onGet("/rota-com-erro").reply(500);
        await expect(adminApi.get("/rota-com-erro")).rejects.toBeDefined();
        expect(adminTokenStorage.get()).toBe("token-valido"); // token intacto
        expect(window.location.href).toBe(""); // não redirecionou
    });
});
