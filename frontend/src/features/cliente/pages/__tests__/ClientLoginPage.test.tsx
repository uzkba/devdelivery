import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ClientLoginPage from "../ClientLoginPage";
import { loginCliente } from "../../services/clienteAuthService";
import { useClienteAuth } from "../../../../shared/auth/ClienteAuthContext";

vi.mock("../../services/clienteAuthService", () => ({
  loginCliente: vi.fn(),
}));

const mockNavigate = vi.fn();
let mockLocationState: { from?: string } | undefined;

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ state: mockLocationState }),
}));

vi.mock("../../../../shared/auth/ClienteAuthContext", () => ({
  useClienteAuth: vi.fn(),
}));

const mockLogin = vi.fn();

function fillForm(phone: string, password: string) {
  fireEvent.change(screen.getByLabelText("Telefone"), {
    target: { value: phone },
  });
  fireEvent.change(screen.getByLabelText("Senha"), {
    target: { value: password },
  });
}

function axiosError(status: number) {
  return Object.assign(new Error("request failed"), {
    isAxiosError: true,
    response: { status },
  });
}

describe("ClienteLoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocationState = undefined;
    (useClienteAuth as any).mockReturnValue({ login: mockLogin });
  });

  it("renderiza os campos de telefone e senha", () => {
    render(<ClientLoginPage />);
    expect(screen.getByLabelText("Telefone")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
  });

  it("mantém o botão Entrar desabilitado com telefone incompleto", () => {
    render(<ClientLoginPage />);
    fillForm("849999", "123456");
    expect(screen.getByRole("button", { name: "Entrar" })).toBeDisabled();
  });

  it("aplica a máscara de telefone enquanto o usuário digita", () => {
    render(<ClientLoginPage />);
    const input = screen.getByLabelText("Telefone") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "84999999999" } });
    expect(input.value).toBe("(84) 99999-9999");
  });

  it("habilita o botão quando telefone (10+ dígitos) e senha são preenchidos", () => {
    render(<ClientLoginPage />);
    fillForm("84999999999", "123456");
    expect(screen.getByRole("button", { name: "Entrar" })).toBeEnabled();
  });

  it("login com sucesso: envia só os dígitos do telefone e navega pra / por padrão", async () => {
    (loginCliente as any).mockResolvedValue({
      access_token: "token-abc",
      expires_in: 3600,
    });
    render(<ClientLoginPage />);

    fillForm("84999999999", "123456");
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => {
      expect(loginCliente).toHaveBeenCalledWith({
        phone: "84999999999",
        password: "123456",
      });
    });
    expect(mockLogin).toHaveBeenCalledWith("token-abc", "(84) 99999-9999");
    expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
  });

  it("navega pra location.state.from quando presente", async () => {
    mockLocationState = { from: "/pedidos" };
    (loginCliente as any).mockResolvedValue({
      access_token: "token-abc",
      expires_in: 3600,
    });
    render(<ClientLoginPage />);

    fillForm("84999999999", "123456");
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/pedidos", { replace: true });
    });
  });

  it("mostra 'Telefone ou senha inválidos.' em erro 401", async () => {
    (loginCliente as any).mockRejectedValue(axiosError(401));
    render(<ClientLoginPage />);

    fillForm("84999999999", "senha-errada");
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(
      await screen.findByText("Telefone ou senha inválidos."),
    ).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("mostra 'Cliente inativo...' em erro 403", async () => {
    (loginCliente as any).mockRejectedValue(axiosError(403));
    render(<ClientLoginPage />);

    fillForm("84999999999", "123456");
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(
      await screen.findByText(
        "Cliente inativo. Entre em contato com o restaurante.",
      ),
    ).toBeInTheDocument();
  });

  it("mostra mensagem genérica de conexão pra outros status HTTP", async () => {
    (loginCliente as any).mockRejectedValue(axiosError(500));
    render(<ClientLoginPage />);

    fillForm("84999999999", "123456");
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(
      await screen.findByText("Não foi possível conectar. Tente novamente."),
    ).toBeInTheDocument();
  });

  it("mostra mensagem de erro inesperado quando o erro não é do axios", async () => {
    (loginCliente as any).mockRejectedValue(new Error("falha qualquer"));
    render(<ClientLoginPage />);

    fillForm("84999999999", "123456");
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(
      await screen.findByText("Erro inesperado. Tente novamente."),
    ).toBeInTheDocument();
  });

  it("alterna a visibilidade da senha ao clicar em Ver/Ocultar", () => {
    render(<ClientLoginPage />);
    const passwordInput = screen.getByLabelText("Senha") as HTMLInputElement;
    expect(passwordInput.type).toBe("password");

    fireEvent.click(screen.getByText("Ver"));
    expect(passwordInput.type).toBe("text");

    fireEvent.click(screen.getByText("Ocultar"));
    expect(passwordInput.type).toBe("password");
  });
});
