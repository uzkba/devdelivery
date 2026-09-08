import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as ClienteAuthContext from "../../../auth/ClienteAuthContext";
import { RequireClientAuth } from "../RequireClientAuth";

function renderWithAuth(isAuthenticated: boolean, initialEntry = "/cardapio") {
    vi.spyOn(ClienteAuthContext, "useClienteAuth").mockReturnValue({
        cliente: isAuthenticated
            ? { id: "1", nome: "Ana", telefone: "(84) 99999-9999", ativo: true }
            : null,
        isAuthenticated,
        login: vi.fn(),
        logout: vi.fn(),
    });

    return render(
        <MemoryRouter initialEntries={[initialEntry]}>
            <Routes>
                <Route path="/cliente/login" element={<div>Tela de login</div>} />
                <Route
                    path="/cardapio"
                    element={
                        <RequireClientAuth>
                            <div>Conteúdo protegido</div>
                        </RequireClientAuth>
                    }
                />
                <Route
                    path="/pedidos"
                    element={
                        <RequireClientAuth>
                            <div>Meus pedidos</div>
                        </RequireClientAuth>
                    }
                />
            </Routes>
        </MemoryRouter>,
    );
}

describe("RequireClientAuth", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it("renderiza o conteúdo quando autenticado", () => {
        renderWithAuth(true);

        expect(screen.getByText("Conteúdo protegido")).toBeInTheDocument();
    });

    it("redireciona pra /cliente/login quando não autenticado", () => {
        renderWithAuth(false);

        expect(screen.getByText("Tela de login")).toBeInTheDocument();
        expect(screen.queryByText("Conteúdo protegido")).not.toBeInTheDocument();
    });

    it("funciona em qualquer rota protegida, não só numa fixa", () => {
        renderWithAuth(true, "/pedidos");

        expect(screen.getByText("Meus pedidos")).toBeInTheDocument();
    });

    it("redireciona também quando não autenticado numa rota diferente", () => {
        renderWithAuth(false, "/pedidos");

        expect(screen.getByText("Tela de login")).toBeInTheDocument();
        expect(screen.queryByText("Meus pedidos")).not.toBeInTheDocument();
    });

    it("renderiza múltiplos filhos quando autenticado", () => {
        vi.spyOn(ClienteAuthContext, "useClienteAuth").mockReturnValue({
            cliente: { id: "1", nome: "Ana", telefone: "(84) 99999-9999", ativo: true },
            isAuthenticated: true,
            login: vi.fn(),
            logout: vi.fn(),
        });

        render(
            <MemoryRouter initialEntries={["/cardapio"]}>
                <Routes>
                    <Route path="/cliente/login" element={<div>Tela de login</div>} />
                    <Route
                        path="/cardapio"
                        element={
                            <RequireClientAuth>
                                <div>Filho 1</div>
                                <div>Filho 2</div>
                            </RequireClientAuth>
                        }
                    />
                </Routes>
            </MemoryRouter>,
        );

        expect(screen.getByText("Filho 1")).toBeInTheDocument();
        expect(screen.getByText("Filho 2")).toBeInTheDocument();
    });
});