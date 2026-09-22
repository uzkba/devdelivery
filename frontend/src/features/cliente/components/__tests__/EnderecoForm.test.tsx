import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EnderecoForm from "../EnderecoForm";

const mockBuscarEnderecoPorCep = vi.fn();
vi.mock("@/shared/services/viaCepService", () => ({
    buscarEnderecoPorCep: (...args: any[]) => mockBuscarEnderecoPorCep(...args),
    formatarCep: (raw: string) => raw, // identidade — a máscara em si não é desta task
}));

const mockBuscarCoordenadasPorEndereco = vi.fn();
vi.mock("@/features/cliente/services/geocodingService", () => ({
    buscarCoordenadasPorEndereco: (...args: any[]) =>
        mockBuscarCoordenadasPorEndereco(...args),
}));

async function preencherObrigatorios(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText("Rua"), "Rua das Flores");
    await user.type(screen.getByLabelText("Número"), "123");
    await user.type(screen.getByLabelText("Bairro"), "Centro");
}

describe("EnderecoForm", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    beforeEach(() => {
        onSubmit.mockClear();
        onCancel.mockClear();
        mockBuscarEnderecoPorCep.mockReset();
        mockBuscarCoordenadasPorEndereco.mockReset();
        mockBuscarCoordenadasPorEndereco.mockResolvedValue({
            latitude: -23.55,
            longitude: -46.63,
        });
    });

    it("mostra o título recebido", () => {
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );
        expect(screen.getByText("Novo endereço")).toBeInTheDocument();
    });

    it("mostra a mensagem de erro quando fornecida", () => {
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                errorMessage="Falha ao salvar"
                onSubmit={onSubmit}
            />,
        );
        expect(screen.getByText("Falha ao salvar")).toBeInTheDocument();
    });

    it("não mostra banner de erro quando errorMessage é omitido", () => {
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );
        expect(screen.queryByText(/Falha/)).not.toBeInTheDocument();
    });

    it("botão salvar fica desabilitado até rua, número e bairro estarem preenchidos", async () => {
        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        const botaoSalvar = screen.getByText("Salvar");
        expect(botaoSalvar).toBeDisabled();

        await user.type(screen.getByLabelText("Rua"), "Rua das Flores");
        expect(botaoSalvar).toBeDisabled();

        await user.type(screen.getByLabelText("Número"), "123");
        expect(botaoSalvar).toBeDisabled();

        await user.type(screen.getByLabelText("Bairro"), "Centro");
        expect(botaoSalvar).toBeEnabled();
    });

    it("chama onSubmit com o payload preenchido (com coordenadas do geocoding), sem o campo cep", async () => {
        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        await preencherObrigatorios(user);
        await user.type(screen.getByLabelText("Complemento"), "Apto 12");
        await user.type(
            screen.getByLabelText("Ponto de referência"),
            "Perto do mercado",
        );
        await user.click(screen.getByText("Salvar"));

        // handleSubmit agora é assíncrono: sem localização capturada,
        // passa pelo geocoding antes de chamar onSubmit
        await waitFor(() =>
            expect(mockBuscarCoordenadasPorEndereco).toHaveBeenCalledWith({
                street: "Rua das Flores, 123",
                city: "Malta",
                state: "PB",
                neighborhood: "Centro",
                postalCode: "",
            }),
        );

        await waitFor(() =>
            expect(onSubmit).toHaveBeenCalledWith({
                street: "Rua das Flores",
                number: "123",
                complement: "Apto 12",
                neighborhood: "Centro",
                reference_point: "Perto do mercado",
                latitude: -23.55,
                longitude: -46.63,
            }),
        );
        expect(onSubmit.mock.calls[0][0]).not.toHaveProperty("cep");
    });

    it("mostra erro de geocodificação quando o endereço não é localizado e não chama onSubmit", async () => {
        mockBuscarCoordenadasPorEndereco.mockResolvedValueOnce(null);
        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        await preencherObrigatorios(user);
        await user.click(screen.getByText("Salvar"));

        await waitFor(() =>
            expect(
                screen.getByText(
                    "Não conseguimos localizar esse endereço. Confira rua, número, bairro e CEP.",
                ),
            ).toBeInTheDocument(),
        );
        expect(onSubmit).not.toHaveBeenCalled();
    });

    it("preenche os campos a partir de initialValue e permite salvar imediatamente", () => {
        render(
            <EnderecoForm
                title="Editar endereço"
                submitLabel="Atualizar"
                submitting={false}
                onSubmit={onSubmit}
                initialValue={{
                    street: "Rua X",
                    number: "1",
                    complement: "",
                    neighborhood: "Bairro Y",
                    reference_point: "",
                    latitude: null,
                    longitude: null,
                }}
            />,
        );

        expect(screen.getByLabelText("Rua")).toHaveValue("Rua X");
        expect(screen.getByLabelText("Número")).toHaveValue("1");
        expect(screen.getByLabelText("Bairro")).toHaveValue("Bairro Y");
        expect(screen.getByText("Atualizar")).toBeEnabled();
    });

    it("busca o endereço pelo CEP e preenche rua/bairro automaticamente", async () => {
        mockBuscarEnderecoPorCep.mockResolvedValue({
            logradouro: "Rua Encontrada",
            bairro: "Bairro Encontrado",
        });
        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        await user.type(screen.getByLabelText("CEP"), "01001000");

        await waitFor(
            () =>
                expect(mockBuscarEnderecoPorCep).toHaveBeenCalledWith(
                    "01001000",
                ),
            { timeout: 2000 },
        );
        await waitFor(() =>
            expect(screen.getByLabelText("Rua")).toHaveValue("Rua Encontrada"),
        );
        expect(screen.getByLabelText("Bairro")).toHaveValue(
            "Bairro Encontrado",
        );
    });

    it("não sobrescreve rua/bairro já preenchidos manualmente quando a API não devolve esses campos", async () => {
        mockBuscarEnderecoPorCep.mockResolvedValue({
            logradouro: "",
            bairro: "",
        });
        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        await user.type(screen.getByLabelText("Rua"), "Rua Já Digitada");
        await user.type(screen.getByLabelText("CEP"), "01001000");

        await waitFor(
            () => expect(mockBuscarEnderecoPorCep).toHaveBeenCalled(),
            { timeout: 2000 },
        );
        expect(screen.getByLabelText("Rua")).toHaveValue("Rua Já Digitada");
    });

    it("mostra aviso de CEP não encontrado quando a busca devolve null", async () => {
        mockBuscarEnderecoPorCep.mockResolvedValue(null);
        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        await user.type(screen.getByLabelText("CEP"), "99999999");

        await waitFor(() =>
            expect(
                screen.getByText(
                    "Não encontramos rua e bairro cadastrados pra esse CEP — preencha manualmente.",
                ),
            ).toBeInTheDocument(),
        );
    });

    it("não dispara busca antes de completar 8 dígitos", async () => {
        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        await user.type(screen.getByLabelText("CEP"), "0100100"); // 7 dígitos
        await new Promise((r) => setTimeout(r, 600));

        expect(mockBuscarEnderecoPorCep).not.toHaveBeenCalled();
    });

    it("mostra estado de carregando/desabilita salvar e cancelar enquanto submitting", () => {
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={true}
                onSubmit={onSubmit}
                onCancel={onCancel}
            />,
        );

        expect(screen.getByText("Salvando...")).toBeDisabled();
        expect(screen.getByText("Cancelar")).toBeDisabled();
    });

    it("não mostra botão cancelar quando onCancel não é fornecido", () => {
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );
        expect(screen.queryByText("Cancelar")).not.toBeInTheDocument();
    });

    it("chama onCancel ao clicar em Cancelar", async () => {
        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
                onCancel={onCancel}
            />,
        );

        await user.click(screen.getByText("Cancelar"));
        expect(onCancel).toHaveBeenCalled();
    });

    it("captura localização com sucesso, atualiza o texto do botão e envia sem passar pelo geocoding", async () => {
        const getCurrentPosition = vi.fn(
            (
                success: (pos: {
                    coords: { latitude: number; longitude: number };
                }) => void,
            ) => {
                success({ coords: { latitude: -10.1, longitude: -20.2 } });
            },
        );
        Object.defineProperty(globalThis.navigator, "geolocation", {
            value: { getCurrentPosition },
            configurable: true,
        });

        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        await preencherObrigatorios(user);

        await user.click(screen.getByText("Usar minha localização atual"));

        expect(getCurrentPosition).toHaveBeenCalled();
        expect(screen.getByText("Localização capturada ✓")).toBeInTheDocument();

        await user.click(screen.getByText("Salvar"));

        await waitFor(() =>
            expect(onSubmit).toHaveBeenCalledWith(
                expect.objectContaining({ latitude: -10.1, longitude: -20.2 }),
            ),
        );
        expect(mockBuscarCoordenadasPorEndereco).not.toHaveBeenCalled();
    });

    it("mantém o texto padrão quando a captura de localização falha", async () => {
        const getCurrentPosition = vi.fn(
            (
                _success: (pos: unknown) => void,
                error: (err: unknown) => void,
            ) => {
                error({});
            },
        );
        Object.defineProperty(globalThis.navigator, "geolocation", {
            value: { getCurrentPosition },
            configurable: true,
        });

        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        await user.click(screen.getByText("Usar minha localização atual"));

        expect(
            screen.getByText("Usar minha localização atual"),
        ).toBeInTheDocument();
    });

    it("não quebra ao clicar em localização quando o navegador não suporta geolocalização", async () => {
        Object.defineProperty(globalThis.navigator, "geolocation", {
            value: undefined,
            configurable: true,
        });

        const user = userEvent.setup();
        render(
            <EnderecoForm
                title="Novo endereço"
                submitLabel="Salvar"
                submitting={false}
                onSubmit={onSubmit}
            />,
        );

        await user.click(screen.getByText("Usar minha localização atual"));
        expect(
            screen.getByText("Usar minha localização atual"),
        ).toBeInTheDocument();
    });
});
