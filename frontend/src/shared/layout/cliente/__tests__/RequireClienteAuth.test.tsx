import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { RequireClienteAuth } from "../RequireClienteAuth";
import * as ClienteAuthContext from "../../../auth/ClienteAuthContext";

function renderWithAuth(isAuthenticated: boolean) {
    vi.spyOn(ClienteAuthContext, "useClienteAuth").mockReturnValue({
        cliente: isAuthenticated
                ? {
                    id: "1",
                    nome: "Ana",
                    telefone: "(84) 99999-9999",
                    ativo: true,
                }
            : null,
        isAuthenticated,
        login: vi.fn(),
        logout: vi.fn(),
    });

    return render(
        <MemoryRouter initialEntries={["/cardapio"]}>
            <Routes>
                <Route path="/login" element={<div>Tela de login</div>} />
                <Route
                    path="/cardapio"
                    element={
                        <RequireClienteAuth>
                            <div>Conteúdo protegido</div>
                        </RequireClienteAuth>
                    }
                />
            </Routes>
        </MemoryRouter>,
    );
}

describe("RequireClienteAuth", () => {
    it("renderiza o conteúdo quando autenticado", () => {
        renderWithAuth(true);

        expect(screen.getByText("Conteúdo protegido")).toBeInTheDocument();
    });

    it("redireciona pra /login quando não autenticado", () => {
        renderWithAuth(false);

        expect(screen.getByText("Tela de login")).toBeInTheDocument();
        expect(
            screen.queryByText("Conteúdo protegido"),
        ).not.toBeInTheDocument();
    });
});