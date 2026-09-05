import { describe, it, expect, vi, beforeEach } from "vitest";

const mockGet = vi.fn();
const mockClear = vi.fn();

vi.mock("../../auth/tokenStorage", () => ({
    clientTokenStorage: { get: mockGet, set: vi.fn(), clear: mockClear },
}));

let requestHandler: (config: any) => any;
let responseErrorHandler: (error: any) => Promise<never>;

vi.mock("../apiFactory", () => ({
    createApiInstance: () => ({
        interceptors: {
            request: { use: (fn: any) => { requestHandler = fn; } },
            response: { use: (_success: any, errorFn: any) => { responseErrorHandler = errorFn; } },
        },
    }),
}));

function mockLocation(initialPath: string) {
    const location: any = {
        pathname: initialPath,
        get href() {
            return `http://localhost${this.pathname}`;
        },
        set href(value: string) {
            this.pathname = new URL(value, "http://localhost").pathname;
        },
    };
    Object.defineProperty(window, "location", {
        value: location,
        writable: true,
        configurable: true,
    });
}

describe("clientApi - interceptors", () => {
    beforeEach(async () => {
        vi.resetModules();
        mockGet.mockReset();
        mockClear.mockReset();
        await import("../clientApi");
    });

    it("injeta o Authorization header quando há token salvo", () => {
        mockGet.mockReturnValue("token-cliente");
        const config = requestHandler({ headers: {} });
        expect(config.headers.Authorization).toBe("Bearer token-cliente");
    });

    it("não injeta header quando não há token", () => {
        mockGet.mockReturnValue(null);
        const config = requestHandler({ headers: {} });
        expect(config.headers.Authorization).toBeUndefined();
    });

    it("limpa o token e redireciona pro login ao receber 401 fora da tela de login", async () => {
        mockLocation("/cardapio");
        const error = { response: { status: 401 } };

        await expect(responseErrorHandler(error)).rejects.toBe(error);

        expect(mockClear).toHaveBeenCalled();
        expect(window.location.pathname).toBe("/cliente/login");
    });

    it("não redireciona de novo se já estiver na tela de login", async () => {
        mockLocation("/cliente/login");
        const error = { response: { status: 401 } };

        await expect(responseErrorHandler(error)).rejects.toBe(error);

        expect(mockClear).toHaveBeenCalled();
        expect(window.location.pathname).toBe("/cliente/login");
    });

    it("não limpa o token em erros que não sejam 401", async () => {
        mockLocation("/cardapio");
        const error = { response: { status: 403 } };
        await expect(responseErrorHandler(error)).rejects.toBe(error);
        expect(mockClear).not.toHaveBeenCalled();
    });
});