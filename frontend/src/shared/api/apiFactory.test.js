import { describe, it, expect } from "vitest";
import { createApiInstance } from "./apiFactory";
describe("createApiInstance", () => {
    it("usa a baseURL configurada por variável de ambiente", () => {
        const instance = createApiInstance();
        expect(instance.defaults.baseURL).toBe(import.meta.env.VITE_API_URL ?? "http://localhost:8000");
    });
    it("define Content-Type JSON por padrão", () => {
        const instance = createApiInstance();
        expect(instance.defaults.headers["Content-Type"]).toBe("application/json");
    });
    it("cada chamada cria uma instância independente", () => {
        expect(createApiInstance()).not.toBe(createApiInstance());
    });
});
