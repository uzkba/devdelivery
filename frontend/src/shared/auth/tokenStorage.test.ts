import { describe, it, expect, beforeEach } from "vitest";
import { adminTokenStorage, clientTokenStorage } from "./tokenStorage";

describe("tokenStorage", () => {
    beforeEach(() => localStorage.clear());

    it("salva e recupera o token do admin", () => {
        adminTokenStorage.set("abc123");
        expect(adminTokenStorage.get()).toBe("abc123");
    });

    it("retorna null quando não há token salvo", () => {
        expect(adminTokenStorage.get()).toBeNull();
    });

    it("limpa o token", () => {
        adminTokenStorage.set("abc123");
        adminTokenStorage.clear();
        expect(adminTokenStorage.get()).toBeNull();
    });

    it("mantém sessões de admin e cliente independentes", () => {
        adminTokenStorage.set("token-admin");
        clientTokenStorage.set("token-cliente");

        adminTokenStorage.clear();

        expect(adminTokenStorage.get()).toBeNull();
        expect(clientTokenStorage.get()).toBe("token-cliente"); // não foi afetado
    });
});