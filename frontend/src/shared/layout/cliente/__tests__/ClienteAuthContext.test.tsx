import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  ClienteAuthProvider,
  useClienteAuth,
} from "../../../auth/ClienteAuthContext";

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

      <button onClick={login}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

describe("ClienteAuthContext", () => {
  it("inicia autenticado com o cliente mockado", () => {
    render(
      <ClienteAuthProvider>
        <Probe />
      </ClienteAuthProvider>,
    );

    expect(screen.getByTestId("autenticado")).toHaveTextContent("true");
    expect(screen.getByTestId("nome")).toHaveTextContent("Ana Souza");
    expect(screen.getByTestId("telefone")).toHaveTextContent("(84) 99999-9999");
    expect(screen.getByTestId("ativo")).toHaveTextContent("true");
  });

  it("logout limpa o cliente e login restaura o mock", () => {
    render(
      <ClienteAuthProvider>
        <Probe />
      </ClienteAuthProvider>,
    );

    fireEvent.click(screen.getByText("logout"));

    expect(screen.getByTestId("autenticado")).toHaveTextContent("false");
    expect(screen.getByTestId("nome")).toHaveTextContent("sem-cliente");
    expect(screen.getByTestId("telefone")).toHaveTextContent("sem-telefone");
    expect(screen.getByTestId("ativo")).toHaveTextContent("sem-cliente");

    fireEvent.click(screen.getByText("login"));

    expect(screen.getByTestId("autenticado")).toHaveTextContent("true");
    expect(screen.getByTestId("nome")).toHaveTextContent("Ana Souza");
    expect(screen.getByTestId("telefone")).toHaveTextContent("(84) 99999-9999");
    expect(screen.getByTestId("ativo")).toHaveTextContent("true");
  });

  it("useClienteAuth lança erro fora do provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<Probe />)).toThrow(
      "useClienteAuth deve ser utilizado dentro de um ClienteAuthProvider",
    );

    spy.mockRestore();
  });
});
