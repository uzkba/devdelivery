import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "../StaffAuthContext";

const { mockGet, mockSet, mockClear } = vi.hoisted(() => ({
    mockGet: vi.fn(),
    mockSet: vi.fn(),
    mockClear: vi.fn(),
}));

vi.mock("../tokenStorage", () => ({
    adminTokenStorage: { get: mockGet, set: mockSet, clear: mockClear },
}));

function buildToken(payload: object) {
    return `header.${btoa(JSON.stringify(payload))}.sig`;
}

const VALID_PAYLOAD = {
    sub: "admin-001",
    login: "marcos@devdelivery.com",
    name: "Marcos Ferreira",
    role: "admin",
    restaurant_id: "rest-001",
    type: "admin",
    exp: 9999999999,
};
const VALID_TOKEN = buildToken(VALID_PAYLOAD);

function TestConsumer() {
    const { user, isAuthenticated, login, logout } = useAuth();
    return (
        <div>
            <span data-testid="status">{isAuthenticated ? "logado" : "deslogado"}</span>
            <span data-testid="nome">{user?.nome ?? ""}</span>
            <span data-testid="email">{user?.email ?? ""}</span>
            <button onClick={() => login(VALID_TOKEN)}>login</button>
            <button onClick={logout}>logout</button>
        </div>
    );
}

describe("StaffAuthContext", () => {
    beforeEach(() => {
        mockGet.mockReset();
        mockSet.mockReset();
        mockClear.mockReset();
    });

    it("inicia deslogado quando não há token salvo", () => {
        mockGet.mockReturnValue(null);
        render(<AuthProvider><TestConsumer /></AuthProvider>);

        expect(screen.getByTestId("status").textContent).toBe("deslogado");
    });

    it("restaura a sessão a partir de um token válido salvo no storage", () => {
        mockGet.mockReturnValue(VALID_TOKEN);
        render(<AuthProvider><TestConsumer /></AuthProvider>);

        expect(screen.getByTestId("status").textContent).toBe("logado");
        expect(screen.getByTestId("nome").textContent).toBe("Marcos Ferreira");
        expect(screen.getByTestId("email").textContent).toBe("marcos@devdelivery.com");
    });

    it("limpa o storage e inicia deslogado se o token salvo estiver corrompido", () => {
        mockGet.mockReturnValue("token-invalido");
        render(<AuthProvider><TestConsumer /></AuthProvider>);

        expect(screen.getByTestId("status").textContent).toBe("deslogado");
        expect(mockClear).toHaveBeenCalled();
    });

    it("login() persiste o token e atualiza o usuário", async () => {
        mockGet.mockReturnValue(null);
        render(<AuthProvider><TestConsumer /></AuthProvider>);

        await act(async () => {
            screen.getByText("login").click();
        });

        expect(mockSet).toHaveBeenCalledWith(VALID_TOKEN);
        expect(screen.getByTestId("status").textContent).toBe("logado");
    });

    it("logout() limpa o token e o usuário", async () => {
        mockGet.mockReturnValue(VALID_TOKEN);
        render(<AuthProvider><TestConsumer /></AuthProvider>);

        await act(async () => {
            screen.getByText("logout").click();
        });

        expect(mockClear).toHaveBeenCalled();
        expect(screen.getByTestId("status").textContent).toBe("deslogado");
    });

    it("useAuth lança erro se usado fora do AuthProvider", () => {
        const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
        expect(() => render(<TestConsumer />)).toThrow(
            "useAuth deve ser utilizado dentro de um AuthProvider",
        );
        consoleError.mockRestore();
    });
});