import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import PixPage from "../PixPage";
import type { CartItem, Address } from "../../types/checkout";
import { gerarPix } from "../../services/pagamentoService";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
    const actual =
        await vi.importActual<typeof import("react-router-dom")>(
            "react-router-dom",
        );
    return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("../../services/pagamentoService", () => ({
    gerarPix: vi.fn(),
}));

// stub simples pra não depender da renderização real da lib de QR code
vi.mock("qrcode.react", () => ({
    QRCodeSVG: ({ value }: { value: string }) => (
        <div data-testid="qr-code">{value}</div>
    ),
}));

const cartItems: CartItem[] = [
    { id: "1", nome: "Marmita tradicional", preco: 22, quantidade: 1 },
];
const address: Address = {
    id: "end-1",
    street: "Rua das Flores",
    number: "100",
    neighborhood: "Centro",
    primary_address: true,
};

function renderPage(total = 27) {
    return render(
        <MemoryRouter
            initialEntries={[
                {
                    pathname: "/pedido/pagamento/pix",
                    state: { cartItems, address, method: "PIX", total },
                },
            ]}
        >
            <Routes>
                <Route path="/pedido/pagamento/pix" element={<PixPage />} />
            </Routes>
        </MemoryRouter>,
    );
}

const respostaPixMock = {
    copy_and_paste_code: "000201...6304ABCD",
    pix_key: "chave@exemplo.com",
    account_holder: "FULANO DE TAL",
    amount: 27,
};

describe("PixPage", () => {
    beforeEach(() => {
        mockNavigate.mockReset();
        vi.mocked(gerarPix).mockReset();
    });

    it("mostra o estado de carregamento e depois o código Pix gerado pelo backend", async () => {
        vi.mocked(gerarPix).mockResolvedValueOnce(respostaPixMock);
        renderPage(27);

        expect(screen.getByText("Gerando código Pix...")).toBeInTheDocument();
        expect(gerarPix).toHaveBeenCalledWith(27);

        await waitFor(() =>
            expect(screen.getByTestId("qr-code")).toBeInTheDocument(),
        );
        expect(screen.getByTestId("qr-code")).toHaveTextContent(
            respostaPixMock.copy_and_paste_code,
        );

        // O código aparece duas vezes na tela: dentro do stub do QR code e na div
        // de "copiar código". getByText sozinho gera erro de múltiplos elementos,
        // então usamos getAllByText e conferimos as duas ocorrências.
        const ocorrencias = screen.getAllByText(
            respostaPixMock.copy_and_paste_code,
        );
        expect(ocorrencias).toHaveLength(2);
    });

    it("mostra tela de erro quando a geração do código falha", async () => {
        vi.mocked(gerarPix).mockRejectedValueOnce(new Error("falha"));
        renderPage(27);

        await waitFor(() =>
            expect(
                screen.getByText("Não foi possível gerar o código Pix."),
            ).toBeInTheDocument(),
        );
    });

    it("copia o código pro clipboard e mostra a confirmação temporária", async () => {
        vi.mocked(gerarPix).mockResolvedValueOnce(respostaPixMock);
        const user = userEvent.setup();

        // userEvent.setup() stuba a Clipboard API do jsdom com sua própria
        // implementação real (não é um mock) quando o ambiente não a suporta
        // nativamente — que é exatamente o caso aqui (navigator.clipboard não
        // tem writeText nesse jsdom). Por isso o mock precisa ser aplicado DEPOIS
        // do setup(); se vier antes (ex: num beforeEach), o setup() o sobrescreve.
        if (!navigator.clipboard) {
            Object.defineProperty(navigator, "clipboard", {
                value: {},
                writable: true,
                configurable: true,
            });
        }
        const writeTextMock = vi.fn().mockResolvedValue(undefined);
        Object.defineProperty(navigator.clipboard, "writeText", {
            value: writeTextMock,
            writable: true,
            configurable: true,
        });

        renderPage(27);

        await waitFor(() =>
            expect(screen.getByText("Copiar código")).toBeInTheDocument(),
        );
        await user.click(screen.getByText("Copiar código"));

        expect(writeTextMock).toHaveBeenCalledWith(
            respostaPixMock.copy_and_paste_code,
        );
        expect(screen.getByText("Código copiado")).toBeInTheDocument();
    });

    it("confirma o pagamento ao simular o recebimento e permite continuar", async () => {
        // timers reais de propósito aqui: misturar fake timers com userEvent
        // (que também depende de timers) é frágil, e o setTimeout do componente
        // é só 1.8s - deixa rodar de verdade e só aumenta o timeout do waitFor.
        vi.mocked(gerarPix).mockResolvedValueOnce(respostaPixMock);
        const user = userEvent.setup();
        renderPage(27);

        await waitFor(() =>
            expect(
                screen.getByText("Simular pagamento recebido"),
            ).toBeInTheDocument(),
        );
        await user.click(screen.getByText("Simular pagamento recebido"));

        await waitFor(
            () =>
                expect(
                    screen.getByText("Pagamento confirmado"),
                ).toBeInTheDocument(),
            { timeout: 3000 },
        );

        await user.click(screen.getByText("Continuar"));
        expect(mockNavigate).toHaveBeenCalledWith("/pedido/revisao", {
            state: {
                cartItems,
                address,
                payment: "PIX",
                paymentStatus: "confirmed",
                total: 27,
            },
        });
    });
});
