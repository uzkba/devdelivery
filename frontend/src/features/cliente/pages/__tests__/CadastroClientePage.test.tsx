import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ClientRegisterPage from "../CadastroClientePage";
import {
    loginCliente,
    registrarCliente,
} from "../../services/clienteAuthService";
import { useClienteAuth } from "../../../../shared/auth/ClienteAuthContext";

vi.mock("../../services/clienteAuthService", () => ({
    loginCliente: vi.fn(),
    registrarCliente: vi.fn(),
}));

const mockNavigate = vi.fn();

vi.mock("react-router-dom", () => ({
    useNavigate: () => mockNavigate,
}));

vi.mock("../../../../shared/auth/ClienteAuthContext", () => ({
    useClienteAuth: vi.fn(),
}));

const mockLogin = vi.fn();

function fillForm({
    name = "Maria Silva",
    phone = "84999999999",
    password = "12345678",
    confirmPassword = password,
}: {
    name?: string;
    phone?: string;
    password?: string;
    confirmPassword?: string;
} = {}) {
    fireEvent.change(screen.getByLabelText("Nome completo"), {
        target: { value: name },
    });
    fireEvent.change(screen.getByLabelText("Telefone"), {
        target: { value: phone },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
        target: { value: password },
    });
    fireEvent.change(screen.getByLabelText("Confirmar senha"), {
        target: { value: confirmPassword },
    });
}

function axiosError(status: number) {
    return Object.assign(new Error("request failed"), {
        isAxiosError: true,
        response: { status },
    });
}

async function submitAndWaitEnabled() {
    const button = screen.getByRole("button", { name: "Criar minha conta" });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    return button;
}

describe("ClientRegisterPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        (useClienteAuth as any).mockReturnValue({ login: mockLogin });
    });

    it("renderiza os campos de nome, telefone, senha e confirmar senha", () => {
        render(<ClientRegisterPage />);
        expect(screen.getByLabelText("Nome completo")).toBeInTheDocument();
        expect(screen.getByLabelText("Telefone")).toBeInTheDocument();
        expect(screen.getByLabelText("Senha")).toBeInTheDocument();
        expect(screen.getByLabelText("Confirmar senha")).toBeInTheDocument();
    });

    it("aplica a máscara de telefone enquanto o usuário digita", () => {
        render(<ClientRegisterPage />);
        const input = screen.getByLabelText("Telefone") as HTMLInputElement;
        fireEvent.change(input, { target: { value: "84999999999" } });
        expect(input.value).toBe("(84) 99999-9999");
    });

    it("mantém o botão desabilitado enquanto o formulário é inválido", () => {
        render(<ClientRegisterPage />);
        fillForm({ name: "Jo" });
        expect(
            screen.getByRole("button", { name: "Criar minha conta" }),
        ).toBeDisabled();
    });

    it("mostra erro de nome muito curto", async () => {
        render(<ClientRegisterPage />);
        fillForm({ name: "Jo" });
        expect(
            await screen.findByText("Informe seu nome completo"),
        ).toBeInTheDocument();
    });

    it("mostra erro de telefone inválido", async () => {
        render(<ClientRegisterPage />);
        fillForm({ phone: "8499999" });
        expect(
            await screen.findByText("Informe um telefone válido"),
        ).toBeInTheDocument();
    });

    it("mostra erro de senha curta", async () => {
        render(<ClientRegisterPage />);
        fillForm({ password: "123", confirmPassword: "123" });
        expect(
            await screen.findByText("A senha deve ter pelo menos 8 caracteres"),
        ).toBeInTheDocument();
    });

    it("mostra erro quando as senhas não coincidem", async () => {
        render(<ClientRegisterPage />);
        fillForm({ password: "12345678", confirmPassword: "87654321" });
        expect(
            await screen.findByText("As senhas não coincidem"),
        ).toBeInTheDocument();
        expect(
            screen.getByRole("button", { name: "Criar minha conta" }),
        ).toBeDisabled();
    });

    it("habilita o botão quando todos os campos são válidos", async () => {
        render(<ClientRegisterPage />);
        fillForm();
        await waitFor(() =>
            expect(
                screen.getByRole("button", { name: "Criar minha conta" }),
            ).toBeEnabled(),
        );
    });

    it("cadastro com sucesso: registra, loga automaticamente e navega pra /", async () => {
        (registrarCliente as any).mockResolvedValue({
            id: "cliente-1",
            name: "Maria Silva",
            phone: "84999999999",
            is_active: true,
        });
        (loginCliente as any).mockResolvedValue({
            access_token: "token-abc",
            expires_in: 3600,
        });

        render(<ClientRegisterPage />);
        fillForm();
        await submitAndWaitEnabled();

        await waitFor(() => {
            expect(registrarCliente).toHaveBeenCalledWith({
                name: "Maria Silva",
                phone: "84999999999",
                password: "12345678",
            });
        });
        expect(loginCliente).toHaveBeenCalledWith({
            phone: "84999999999",
            password: "12345678",
        });
        expect(mockLogin).toHaveBeenCalledWith("token-abc", "(84) 99999-9999");
        expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });

    it("mostra mensagem de telefone já cadastrado em erro 409", async () => {
        (registrarCliente as any).mockRejectedValue(axiosError(409));

        render(<ClientRegisterPage />);
        fillForm();
        await submitAndWaitEnabled();

        expect(
            await screen.findByText(
                "Esse telefone já está cadastrado. Faça login ou use outro número.",
            ),
        ).toBeInTheDocument();
        expect(loginCliente).not.toHaveBeenCalled();
        expect(mockLogin).not.toHaveBeenCalled();
        expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("mostra mensagem de dados inválidos em erro 422", async () => {
        (registrarCliente as any).mockRejectedValue(axiosError(422));

        render(<ClientRegisterPage />);
        fillForm();
        await submitAndWaitEnabled();

        expect(
            await screen.findByText(
                "Verifique os dados informados e tente novamente.",
            ),
        ).toBeInTheDocument();
    });

    it("mostra mensagem genérica em outros erros HTTP do cadastro", async () => {
        (registrarCliente as any).mockRejectedValue(axiosError(500));

        render(<ClientRegisterPage />);
        fillForm();
        await submitAndWaitEnabled();

        expect(
            await screen.findByText(
                "Não foi possível concluir o cadastro. Tente novamente.",
            ),
        ).toBeInTheDocument();
    });

    it("mostra mensagem de erro inesperado quando o erro do cadastro não é do axios", async () => {
        (registrarCliente as any).mockRejectedValue(
            new Error("falha qualquer"),
        );

        render(<ClientRegisterPage />);
        fillForm();
        await submitAndWaitEnabled();

        expect(
            await screen.findByText("Erro inesperado. Tente novamente."),
        ).toBeInTheDocument();
    });

    it("cadastro OK mas login automático falha: manda pro /cliente/login sem chamar login()", async () => {
        (registrarCliente as any).mockResolvedValue({
            id: "cliente-1",
            name: "Maria Silva",
            phone: "84999999999",
            is_active: true,
        });
        (loginCliente as any).mockRejectedValue(axiosError(401));

        render(<ClientRegisterPage />);
        fillForm();
        await submitAndWaitEnabled();

        await waitFor(() => {
            expect(mockNavigate).toHaveBeenCalledWith("/cliente/login", {
                replace: true,
                state: { from: "/" },
            });
        });
        expect(mockLogin).not.toHaveBeenCalled();
    });

    it("alterna a visibilidade da senha e da confirmação de senha", () => {
        render(<ClientRegisterPage />);
        const passwordInput = screen.getByLabelText(
            "Senha",
        ) as HTMLInputElement;
        const confirmInput = screen.getByLabelText(
            "Confirmar senha",
        ) as HTMLInputElement;

        expect(passwordInput.type).toBe("password");
        expect(confirmInput.type).toBe("password");

        fireEvent.click(screen.getAllByText("Ver")[0]);
        expect(passwordInput.type).toBe("text");
        expect(confirmInput.type).toBe("password");

        fireEvent.click(screen.getAllByText("Ver")[0]);
        expect(confirmInput.type).toBe("text");
    });

    it("o link 'Entrar' navega pra /cliente/login", () => {
        render(<ClientRegisterPage />);
        fireEvent.click(screen.getByText("Entrar"));
        expect(mockNavigate).toHaveBeenCalledWith("/cliente/login");
    });
});
