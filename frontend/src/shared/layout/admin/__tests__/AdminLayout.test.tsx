import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuth } from "../../../auth/StaffAuthContext";
import { AdminLayout } from "../AdminLayout";

vi.mock("../../../auth/StaffAuthContext", async () => {
  const actual = await vi.importActual<
    typeof import("../../../auth/StaffAuthContext")
  >("../../../auth/StaffAuthContext");
  return { ...actual, useAuth: vi.fn() };
});

const mockedUseAuth = vi.mocked(useAuth);
const logoutMock = vi.fn();

function renderLayout(initialPath = "/admin") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Tela de login</div>} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<div>Página de visão geral</div>} />
          <Route path="pedidos" element={<div>Página de pedidos</div>} />
          <Route path="relatorios" element={<div>Página de relatórios</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  logoutMock.mockReset();
});

describe("AdminLayout", () => {
  it("redireciona para /login quando não há usuário logado", () => {
    mockedUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      login: vi.fn(),
      logout: logoutMock,
    });

    renderLayout();

    expect(screen.getByText("Tela de login")).toBeInTheDocument();
  });

  it("mostra apenas os itens de menu permitidos para a role atendente", () => {
    mockedUseAuth.mockReturnValue({
      user: { id: "2", nome: "Carla", email: "carla@x.com", role: "atendente" },
      isAuthenticated: true,
      login: vi.fn(),
      logout: logoutMock,
    });

    renderLayout();

    expect(screen.getByRole("link", { name: /início/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /cardápio/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pedidos/i })).toBeInTheDocument();

    expect(
      screen.queryByRole("link", { name: /relatórios/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /caixa/i }),
    ).not.toBeInTheDocument();
  });

  it("mostra todos os itens de menu para o admin", () => {
    mockedUseAuth.mockReturnValue({
      user: { id: "1", nome: "Marcos", email: "marcos@x.com", role: "admin" },
      isAuthenticated: true,
      login: vi.fn(),
      logout: logoutMock,
    });

    renderLayout();

    expect(screen.getByRole("link", { name: /início/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /cardápio/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pedidos/i })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /relatórios/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /caixa/i })).toBeInTheDocument();
  });

  it("exibe o nome do usuário logado e o rótulo da sua role", () => {
    mockedUseAuth.mockReturnValue({
      user: {
        id: "1",
        nome: "Marcos Ferreira",
        email: "marcos@x.com",
        role: "admin",
      },
      isAuthenticated: true,
      login: vi.fn(),
      logout: logoutMock,
    });

    renderLayout();

    expect(screen.getByText("Marcos Ferreira")).toBeInTheDocument();
    expect(screen.getByText("Administrador")).toBeInTheDocument();
  });

  it("chama logout e redireciona para /login ao clicar em Sair", async () => {
    const user = userEvent.setup();

    mockedUseAuth.mockReturnValue({
      user: { id: "1", nome: "Marcos", email: "marcos@x.com", role: "admin" },
      isAuthenticated: true,
      login: vi.fn(),
      logout: logoutMock,
    });

    renderLayout();

    await user.click(screen.getByRole("button", { name: /sair/i }));

    expect(logoutMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Tela de login")).toBeInTheDocument();
  });

  it("renderiza o conteúdo da rota filha ativa através do Outlet", () => {
    mockedUseAuth.mockReturnValue({
      user: { id: "1", nome: "Marcos", email: "marcos@x.com", role: "admin" },
      isAuthenticated: true,
      login: vi.fn(),
      logout: logoutMock,
    });

    renderLayout("/admin/pedidos");

    expect(screen.getByText("Página de pedidos")).toBeInTheDocument();
  });
});
