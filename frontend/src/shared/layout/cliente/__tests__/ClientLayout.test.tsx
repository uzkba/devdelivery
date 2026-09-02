import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ClientLayout } from "../ClientLayout";
import * as ClienteAuthContext from "../../../auth/ClienteAuthContext";

describe("ClientLayout", () => {
    it("mostra o nome do cliente e navega pelo Outlet", () => {
        const logout = vi.fn();

        vi.spyOn(ClienteAuthContext, "useClienteAuth").mockReturnValue({
            cliente: {
                id: "1",
                nome: "Ana Souza",
                telefone: "(84) 99999-9999",
                ativo: true,
            },
            isAuthenticated: true,
            login: vi.fn(),
            logout,
        });

        render(
            <MemoryRouter initialEntries={["/cardapio"]}>
                <Routes>
                    <Route path="/" element={<ClientLayout />}>
                        <Route
                            path="cardapio"
                            element={<div>Página do cardápio</div>}
                        />
                    </Route>
                </Routes>
            </MemoryRouter>,
        );

        expect(screen.getByText("Ana Souza")).toBeInTheDocument();
        expect(
            screen.getByText("Página do cardápio"),
        ).toBeInTheDocument();
    });

    it("chama logout ao clicar em Sair", () => {
        const logout = vi.fn();

        vi.spyOn(ClienteAuthContext, "useClienteAuth").mockReturnValue({
            cliente: {
                id: "1",
                nome: "Ana Souza",
                telefone: "(84) 99999-9999",
                ativo: true,
            },
            isAuthenticated: true,
            login: vi.fn(),
            logout,
        });

        render(
            <MemoryRouter>
                <ClientLayout />
            </MemoryRouter>,
        );

        fireEvent.click(screen.getByText("Sair"));

        expect(logout).toHaveBeenCalledTimes(1);
    });
});