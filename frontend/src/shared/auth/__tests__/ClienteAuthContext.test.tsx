import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { ClienteAuthProvider, useClienteAuth } from "../ClienteAuthContext";

const { mockGet, mockSet, mockClear } = vi.hoisted(() => ({
    mockGet: vi.fn(),
    mockSet: vi.fn(),
    mockClear: vi.fn(),
}));

vi.mock("../tokenStorage", () => ({
    clientTokenStorage: { get: mockGet, set: mockSet, clear: mockClear },
}));

function buildToken(payload: object) {
    return `header.${btoa(JSON.stringify(payload))}.sig`;
}

const FULL_PAYLOAD = {
    sub: "cliente-001",
    type: "client",
    name: "Ana Souza",
    phone: "84999999999",
    is_active: true,
    exp: 9999999999,
};
const FULL_TOKEN = buildToken(FULL_PAYLOAD);

const MINIMAL_PAYLOAD = { sub: "cliente-002", type: "client", exp: 9999999999 };
const MINIMAL_TOKEN = buildToken(MINIMAL_PAYLOAD);

function Probe() {
    const { cliente, isAuthenticated, login, logout } = useClienteAuth();

    return (
        <div>
            <span data-testid="nome">{cliente?.nome ?? "sem-cliente"}</span>
            <span data-testid="telefone">{cliente?.telefone ?? "sem-telefone"}</span>
            <span data-testid="ativo">
                {cliente ? String(cliente.ativo) : "sem-cliente"}
            </span>
            <span data-testid="autenticado">{String(isAuthenticated)}</span>

            <button onClick={() => login(FULL_TOKEN)}>login</button>
            <button onClick={() => login(MINIMAL_TOKEN, "(84) 98888-8888")}>
                login-minimo
            </button>
            <button onClick={logout}>logout</button>
        </div>
    );
}

describe("ClienteAuthContext", () => {
    beforeEach(() => {
        mockGet.mockReset();
        mockSet.mockReset();
        mockClear.mockReset();
    });

    it("inicia deslogado quando não há token salvo", () => {
        mockGet.mockReturnValue(null);
        render(<ClienteAuthProvider><Probe /></ClienteAuthProvider>);

        expect(screen.getByTestId("autenticado")).toHaveTextContent("false");
    });

    it("restaura a sessão a partir de um token com todas as claims", () => {
        mockGet.mockReturnValue(FULL_TOKEN);
        render(<ClienteAuthProvider><Probe /></ClienteAuthProvider>);

        expect(screen.getByTestId("autenticado")).toHaveTextContent("true");
        expect(screen.getByTestId("nome")).toHaveTextContent("Ana Souza");
        expect(screen.getByTestId("telefone")).toHaveTextContent("84999999999");
        expect(screen.getByTestId("ativo")).toHaveTextContent("true");
    });

    it("limpa o storage e inicia deslogado se o token salvo estiver corrompido", () => {
        mockGet.mockReturnValue("token-invalido");
        render(<ClienteAuthProvider><Probe /></ClienteAuthProvider>);

        expect(screen.getByTestId("autenticado")).toHaveTextContent("false");
        expect(mockClear).toHaveBeenCalled();
    });

    it("login() com token completo persiste o token e preenche o cliente", async () => {
        mockGet.mockReturnValue(null);
        render(<ClienteAuthProvider><Probe /></ClienteAuthProvider>);

        await act(async () => {
            screen.getByText("login").click();
        });

        expect(mockSet).toHaveBeenCalledWith(FULL_TOKEN);
        expect(screen.getByTestId("nome")).toHaveTextContent("Ana Souza");
        expect(screen.getByTestId("telefone")).toHaveTextContent("84999999999");
        expect(screen.getByTestId("ativo")).toHaveTextContent("true");
    });

    it("login() com token mínimo usa o telefone informado e valores padrão", async () => {
        mockGet.mockReturnValue(null);
        render(<ClienteAuthProvider><Probe /></ClienteAuthProvider>);

        await act(async () => {
            screen.getByText("login-minimo").click();
        });

        expect(screen.getByTestId("nome")).toHaveTextContent("Cliente");
        expect(screen.getByTestId("telefone")).toHaveTextContent("(84) 98888-8888");
        expect(screen.getByTestId("ativo")).toHaveTextContent("true");
    });

    it("logout limpa o token e o cliente", async () => {
        mockGet.mockReturnValue(FULL_TOKEN);
        render(<ClienteAuthProvider><Probe /></ClienteAuthProvider>);

        await act(async () => {
            screen.getByText("logout").click();
        });

        expect(mockClear).toHaveBeenCalled();
        expect(screen.getByTestId("autenticado")).toHaveTextContent("false");
    });

    it("useClienteAuth lança erro fora do provider", () => {
        const spy = vi.spyOn(console, "error").mockImplementation(() => {});
        expect(() => render(<Probe />)).toThrow(
            "useClienteAuth deve ser utilizado dentro de um ClienteAuthProvider",
        );
        spy.mockRestore();
    });
});