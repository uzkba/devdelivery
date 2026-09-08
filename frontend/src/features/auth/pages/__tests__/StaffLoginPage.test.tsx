import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import StaffLoginPage from "../StaffLoginPage";
import { loginAdmin } from "../../services/authService";
import { useAuth } from "../../../../shared/auth/StaffAuthContext";

vi.mock("../../services/authService", () => ({
    loginAdmin: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
    useNavigate: () => mockNavigate,
}));

vi.mock("../../../../shared/auth/StaffAuthContext", () => ({
    useAuth: vi.fn(),
}));

const mockSetSession = vi.fn();

function fillForm(login: string, password: string) {
    fireEvent.change(screen.getByLabelText("Usuário"), { target: { value: login } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: password } });
}

function axiosError(status: number) {
    return Object.assign(new Error("request failed"), {
        isAxiosError: true,
        response: { status },
    });
}

describe("StaffLoginPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        (useAuth as any).mockReturnValue({ login: mockSetSession });
    });

    it("renderiza os campos de usuário e senha", () => {
        render(<StaffLoginPage />);
        expect(screen.getByLabelText("Usuário")).toBeInTheDocument();
        expect(screen.getByLabelText("Senha")).toBeInTheDocument();
    });

    it("mantém o botão Entrar desabilitado enquanto os campos estão vazios", () => {
        render(<StaffLoginPage />);
        expect(screen.getByRole("button", { name: "Entrar" })).toBeDisabled();
    });

    it("habilita o botão quando usuário e senha são preenchidos", () => {
        render(<StaffLoginPage />);
        fillForm("marcos@devdelivery.com", "123456");
        expect(screen.getByRole("button", { name: "Entrar" })).toBeEnabled();
    });

    it("faz login com sucesso: persiste o token e navega pra /admin", async () => {
        (loginAdmin as any).mockResolvedValue({ access_token: "token-123", expires_in: 3600 });
        render(<StaffLoginPage />);

        fillForm("marcos@devdelivery.com", "123456");
        fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

        await waitFor(() => {
            expect(loginAdmin).toHaveBeenCalledWith({
                login: "marcos@devdelivery.com",
                password: "123456",
            });
        });
        expect(mockSetSession).toHaveBeenCalledWith("token-123");
        expect(mockNavigate).toHaveBeenCalledWith("/admin", { replace: true });
    });

    it("mostra 'Login ou senha inválidos.' em erro 401", async () => {
        (loginAdmin as any).mockRejectedValue(axiosError(401));
        render(<StaffLoginPage />);

        fillForm("marcos@devdelivery.com", "senha-errada");
        fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

        expect(await screen.findByText("Login ou senha inválidos.")).toBeInTheDocument();
        expect(mockSetSession).not.toHaveBeenCalled();
        expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("mostra 'Usuário inativo...' em erro 403", async () => {
        (loginAdmin as any).mockRejectedValue(axiosError(403));
        render(<StaffLoginPage />);

        fillForm("marcos@devdelivery.com", "123456");
        fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

        expect(
            await screen.findByText("Usuário inativo. Contate o administrador."),
        ).toBeInTheDocument();
    });

    it("mostra mensagem genérica de conexão pra outros status HTTP", async () => {
        (loginAdmin as any).mockRejectedValue(axiosError(500));
        render(<StaffLoginPage />);

        fillForm("marcos@devdelivery.com", "123456");
        fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

        expect(
            await screen.findByText("Não foi possível conectar. Tente novamente."),
        ).toBeInTheDocument();
    });

    it("mostra mensagem de erro inesperado quando o erro não é do axios", async () => {
        (loginAdmin as any).mockRejectedValue(new Error("falha qualquer"));
        render(<StaffLoginPage />);

        fillForm("marcos@devdelivery.com", "123456");
        fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

        expect(await screen.findByText("Erro inesperado. Tente novamente.")).toBeInTheDocument();
    });

    it("alterna a visibilidade da senha ao clicar em Ver/Ocultar", () => {
        render(<StaffLoginPage />);
        const passwordInput = screen.getByLabelText("Senha") as HTMLInputElement;
        expect(passwordInput.type).toBe("password");

        fireEvent.click(screen.getByText("Ver"));
        expect(passwordInput.type).toBe("text");

        fireEvent.click(screen.getByText("Ocultar"));
        expect(passwordInput.type).toBe("password");
    });
});