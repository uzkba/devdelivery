import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { useAuth } from "../../../auth/AuthContext";
import { RequireRole } from "../RequireRole";

vi.mock("../../../auth/AuthContext", async () => {
    const actual = await vi.importActual<typeof import("../../../auth/AuthContext")>(
        "../../../auth/AuthContext",
    );
    return { ...actual, useAuth: vi.fn() };
});

const mockedUseAuth = vi.mocked(useAuth);

function renderWithRoute(initialPath: string, roles: Array<"admin" | "atendente" | "caixa" | "entregador">) {
    return render(
        <MemoryRouter initialEntries={[initialPath]}>
            <Routes>
                <Route path="/login" element={<div>Tela de login</div>} />
                <Route path="/admin" element={<div>Visão geral</div>} />
                <Route
                    path="/admin/relatorios"
                    element={
                        <RequireRole roles={roles}>
                            <div>Conteúdo protegido</div>
                        </RequireRole>
                    }
                />
            </Routes>
        </MemoryRouter>,
    );
}

describe("RequireRole", () => {
    it("redireciona para /login quando não há usuário autenticado", () => {
        mockedUseAuth.mockReturnValue({ user: null, isAuthenticated: false, login: vi.fn(), logout: vi.fn() });

        renderWithRoute("/admin/relatorios", ["admin"]);

        expect(screen.getByText("Tela de login")).toBeInTheDocument();
    });

    it("redireciona para /admin quando a role do usuário não está na lista permitida", () => {
        mockedUseAuth.mockReturnValue({
            user: { id: "1", nome: "Ana", email: "ana@x.com", role: "atendente" },
            isAuthenticated: true,
            login: vi.fn(),
            logout: vi.fn(),
        });

        renderWithRoute("/admin/relatorios", ["admin"]);

        expect(screen.getByText("Visão geral")).toBeInTheDocument();
        expect(screen.queryByText("Conteúdo protegido")).not.toBeInTheDocument();
    });

    it("renderiza o conteúdo quando a role do usuário está na lista permitida", () => {
        mockedUseAuth.mockReturnValue({
            user: { id: "1", nome: "Marcos", email: "marcos@x.com", role: "admin" },
            isAuthenticated: true,
            login: vi.fn(),
            logout: vi.fn(),
        });

        renderWithRoute("/admin/relatorios", ["admin"]);

        expect(screen.getByText("Conteúdo protegido")).toBeInTheDocument();
    });
});