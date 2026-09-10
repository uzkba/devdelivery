import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import EnderecoForm from "../EnderecoForm";
import * as viaCepService from "@/shared/services/viaCepService";

vi.mock("@/shared/services/viaCepService", async () => {
    const actual = await vi.importActual<typeof viaCepService>(
        "@/shared/services/viaCepService",
    );
    return { ...actual, buscarEnderecoPorCep: vi.fn() };
});

describe("EnderecoForm", () => {
    beforeEach(() => vi.clearAllMocks());

    it("desabilita o botão de salvar quando faltam campos obrigatórios", () => {
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Adicionar"
                submitting={false}
                onSubmit={vi.fn()}
            />,
        );
        expect(
            screen.getByRole("button", { name: "Adicionar" }),
        ).toBeDisabled();
    });

    it("habilita o botão e envia o payload sem o CEP", () => {
        const onSubmit = vi.fn();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Adicionar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        fireEvent.change(screen.getByLabelText("Rua"), {
            target: { value: "Rua das Flores" },
        });
        fireEvent.change(screen.getByLabelText("Número"), {
            target: { value: "123" },
        });
        fireEvent.change(screen.getByLabelText("Bairro"), {
            target: { value: "Centro" },
        });

        const botao = screen.getByRole("button", { name: "Adicionar" });
        expect(botao).not.toBeDisabled();
        fireEvent.click(botao);

        expect(onSubmit).toHaveBeenCalledWith(
            expect.objectContaining({
                street: "Rua das Flores",
                number: "123",
                neighborhood: "Centro",
            }),
        );
        expect(onSubmit.mock.calls[0][0]).not.toHaveProperty("cep");
    });

    it("preenche rua e bairro automaticamente ao digitar um CEP válido", async () => {
        vi.mocked(viaCepService.buscarEnderecoPorCep).mockResolvedValue({
            logradouro: "Rua Autopreenchida",
            bairro: "Bairro Auto",
            localidade: "Cidade",
            uf: "RN",
        });
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Adicionar"
                submitting={false}
                onSubmit={vi.fn()}
            />,
        );
        fireEvent.change(screen.getByLabelText("CEP"), {
            target: { value: "59300000" },
        });
        await waitFor(
            () =>
                expect(screen.getByLabelText("Rua")).toHaveValue(
                    "Rua Autopreenchida",
                ),
            { timeout: 1000 },
        );
        expect(screen.getByLabelText("Bairro")).toHaveValue("Bairro Auto");
    });

    it("mostra aviso quando o CEP não é encontrado", async () => {
        vi.mocked(viaCepService.buscarEnderecoPorCep).mockResolvedValue(null);
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Adicionar"
                submitting={false}
                onSubmit={vi.fn()}
            />,
        );
        fireEvent.change(screen.getByLabelText("CEP"), {
            target: { value: "00000000" },
        });
        await waitFor(
            () =>
                expect(
                    screen.getByText(/CEP não encontrado/),
                ).toBeInTheDocument(),
            { timeout: 1000 },
        );
    });

    it("chama onCancel ao clicar em cancelar", () => {
        const onCancel = vi.fn();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Adicionar"
                submitting={false}
                onSubmit={vi.fn()}
                onCancel={onCancel}
            />,
        );
        fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
        expect(onCancel).toHaveBeenCalled();
    });

    it("mostra a mensagem de erro quando errorMessage é passado", () => {
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Adicionar"
                submitting={false}
                errorMessage="Não foi possível salvar."
                onSubmit={vi.fn()}
            />,
        );
        expect(
            screen.getByText("Não foi possível salvar."),
        ).toBeInTheDocument();
    });
});
