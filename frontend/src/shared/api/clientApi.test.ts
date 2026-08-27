import { describe, it, expect, beforeEach, afterEach } from "vitest";
import MockAdapter from "axios-mock-adapter";
import { clientApi } from "./clientApi";
import { clientTokenStorage } from "../auth/tokenStorage";

describe("clientApi - interceptors", () => {
    let mock: MockAdapter;
    const originalLocation = window.location;

    beforeEach(() => {
        mock = new MockAdapter(clientApi);
        localStorage.clear();
        Object.defineProperty(window, "location", {
        writable: true,
        value: { ...originalLocation, href: "", pathname: "/cardapio" },
        });
    });

    afterEach(() => {
        mock.restore();
        Object.defineProperty(window, "location", { writable: true, value: originalLocation });
    });

    it("injeta Authorization com o token do cliente", async () => {
        clientTokenStorage.set("token-cliente");
        mock.onGet("/rota").reply((config) => {
        expect(config.headers?.Authorization).toBe("Bearer token-cliente");
        return [200, {}];
        });
        await clientApi.get("/rota");
    });

    it("não injeta Authorization quando não há token", async () => {
        mock.onGet("/rota").reply((config) => {
        expect(config.headers?.Authorization).toBeUndefined();
        return [200, {}];
        });
        await clientApi.get("/rota");
    });

    it("em 401: limpa o token e redireciona pro login do cliente", async () => {
        clientTokenStorage.set("token-expirado");
        mock.onGet("/rota-protegida").reply(401);

        await expect(clientApi.get("/rota-protegida")).rejects.toBeDefined();

        expect(clientTokenStorage.get()).toBeNull();
        expect(window.location.href).toBe("/cliente/login");
    });

    it("não redireciona de novo se já estiver na tela de login do cliente", async () => {
        window.location.pathname = "/cliente/login";
        mock.onGet("/rota-protegida").reply(401);

        await expect(clientApi.get("/rota-protegida")).rejects.toBeDefined();

        expect(window.location.href).toBe("");
    });

    it("em erro diferente de 401 (ex.: 500): não limpa o token nem redireciona", async () => {
        clientTokenStorage.set("token-valido");
        mock.onGet("/rota-com-erro").reply(500);

        await expect(clientApi.get("/rota-com-erro")).rejects.toBeDefined();

        expect(clientTokenStorage.get()).toBe("token-valido");
        expect(window.location.href).toBe("");
    });
});