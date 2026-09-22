import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, MapPin, CreditCard, Plus } from "lucide-react";
import { useCarrinho } from "@/features/pedido/contexts/CarrinhoContexts";
import { useEnderecos } from "@/features/cliente/hooks/useEnderecos";
import EnderecoForm from "@/features/cliente/components/EnderecoForm";
import {
    criarPedido,
    type FormaPagamento,
} from "@/features/pedido/services/pedidoService";
import { suggestChangeAmounts } from "@/features/pedido/utils/sugestoesValoresTroco";
import type { EnderecoInput } from "@/features/cliente/services/enderecoService";
import { useRestauranteInfo } from "@/features/cliente/hooks/useRestauranteInfo";

const DELIVERY_FEE = 5;

const PAGAMENTO_LABEL: Record<FormaPagamento, string> = {
    PIX: "Pix",
    CARTAO_CREDITO: "Cartão de crédito",
    CARTAO_DEBITO: "Cartão de débito",
    DINHEIRO: "Dinheiro",
};

type Secao = "endereco" | "pagamento" | null;

function fmtMoney(n: number) {
    return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function RevisaoPage() {
    const navigate = useNavigate();
    const { itens, subtotal, limparCarrinho } = useCarrinho();
    const {
        enderecos,
        loading: carregandoEnderecos,
        adicionar,
    } = useEnderecos();

    const [secaoAberta, setSecaoAberta] = useState<Secao>(null);
    const [enderecoId, setEnderecoId] = useState<string | null>(null);
    const [mostrandoNovoEndereco, setMostrandoNovoEndereco] = useState(false);
    const [salvandoEndereco, setSalvandoEndereco] = useState(false);
    const [erroEndereco, setErroEndereco] = useState<string | null>(null);

    const [formaPagamento, setFormaPagamento] = useState<FormaPagamento | null>(
        null,
    );
    const [valorPagoDinheiro, setValorPagoDinheiro] = useState("");

    const [observacoes, setObservacoes] = useState("");
    const [confirmando, setConfirmando] = useState(false);
    const [erro, setErro] = useState<string | null>(null);

    useEffect(() => {
        if (!enderecoId && enderecos.length > 0) {
            const padrao =
                enderecos.find((e) => e.primary_address) ?? enderecos[0];
            setEnderecoId(padrao.id);
        }
    }, [enderecos, enderecoId]);

    const total = subtotal + DELIVERY_FEE;
    const trocoSugestoes = useMemo(() => suggestChangeAmounts(total), [total]);
    const valorPagoNum = Number(valorPagoDinheiro.replace(",", ".")) || 0;
    const troco =
        formaPagamento === "DINHEIRO" && valorPagoNum > total
            ? valorPagoNum - total
            : 0;
    const enderecoSelecionado = enderecos.find((e) => e.id === enderecoId);

    const { restaurante } = useRestauranteInfo();

    const podeConfirmar =
        !!restaurante &&
        itens.length > 0 &&
        !!enderecoId &&
        !!formaPagamento &&
        (formaPagamento !== "DINHEIRO" || valorPagoNum >= total);

    async function handleConfirmar() {
        if (!podeConfirmar || !enderecoId || !formaPagamento) return;
        setConfirmando(true);
        setErro(null);
        try {
            const pedido = await criarPedido({
                restaurante_id: restaurante!.id,
                itens: itens.map((i) => ({
                    alimento_id: i.id,
                    quantidade: i.qty,
                })),
                endereco_id: enderecoId,
                forma_pagamento: formaPagamento,
                valor_pago_dinheiro:
                    formaPagamento === "DINHEIRO" ? valorPagoNum : undefined,
                observacoes: observacoes || undefined,
            });
            limparCarrinho();
            navigate('/pedido-confirmado', {
                state: { numero: pedido.numero_pedido },
            });
        } catch {
            setErro(
                "Não deu pra confirmar o pedido agora. Tente novamente em instantes.",
            );
        } finally {
            setConfirmando(false);
        }
    }

    async function handleAdicionarEndereco(payload: EnderecoInput) {
        setSalvandoEndereco(true);
        setErroEndereco(null);
        try {
            const novo = await adicionar(payload);
            setEnderecoId(novo.id);
            setMostrandoNovoEndereco(false);
        } catch {
            setErroEndereco(
                "Não foi possível salvar o endereço. Tente novamente.",
            );
        } finally {
            setSalvandoEndereco(false);
        }
    }

    function toggleSecao(secao: Exclude<Secao, null>) {
        setSecaoAberta((atual) => (atual === secao ? null : secao));
    }

    return (
        <div className="px-4 pt-5 pb-56 flex flex-col gap-4">
            {/* Itens */}
            <div
                className="rounded-2xl p-5"
                style={{ border: "1.5px solid #E8D5C4", background: "#fff" }}
            >
                <div className="flex items-center justify-between mb-4">
                    <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide">
                        Sua marmita
                    </p>
                    <button
                        onClick={() => navigate('/cardapio')}
                        className="text-xs font-bold text-[#F97316]"
                    >
                        Alterar
                    </button>
                </div>
                <div className="flex flex-col gap-1.5">
                    {itens.map((i) => (
                        <div
                            key={i.id}
                            className="flex justify-between items-center text-sm"
                        >
                            <span className="text-[#1A0A00] font-medium">
                                {i.name}
                            </span>
                            <span className="text-[#6B5B4E] font-bold">
                                x {i.qty}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Observações */}
            <div
                className="rounded-2xl p-5"
                style={{ border: "1.5px solid #E8D5C4", background: "#fff" }}
            >
                <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide mb-3">
                    Observações
                </p>
                <textarea
                    rows={3}
                    maxLength={300}
                    value={observacoes}
                    onChange={(e) => setObservacoes(e.target.value)}
                    placeholder="Sem cebola, pouco sal, molho separado... (opcional)"
                    className="w-full px-4 py-3.5 rounded-xl text-sm resize-none"
                    style={{
                        border: "1.5px solid #E8D5C4",
                        background: "#FFF8EF",
                    }}
                />
            </div>

            {/* Endereço — seção expansível */}
            <div
                className="rounded-2xl overflow-hidden"
                style={{ border: "1.5px solid #E8D5C4", background: "#fff" }}
            >
                <button
                    onClick={() => toggleSecao("endereco")}
                    className="w-full flex items-center justify-between p-5"
                >
                    <div className="flex items-start gap-3 text-left">
                        <MapPin
                            size={16}
                            className="text-[#6B5B4E] mt-0.5 shrink-0"
                        />
                        <div>
                            <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide mb-1">
                                Entrega
                            </p>
                            <p className="font-semibold text-[#1A0A00] text-sm">
                                {enderecoSelecionado
                                    ? `${enderecoSelecionado.street}, ${enderecoSelecionado.number}`
                                    : "Selecionar endereço"}
                            </p>
                        </div>
                    </div>
                    <ChevronDown
                        size={18}
                        className={`text-[#6B5B4E] transition-transform ${secaoAberta === "endereco" ? "rotate-180" : ""}`}
                    />
                </button>

                {secaoAberta === "endereco" && (
                    <div className="px-5 pb-5 flex flex-col gap-2">
                        {carregandoEnderecos && (
                            <p className="text-sm text-[#6B5B4E]">
                                Carregando endereços...
                            </p>
                        )}
                        {enderecos.map((e) => (
                            <label
                                key={e.id}
                                className="flex items-center gap-3 p-3 rounded-xl cursor-pointer"
                                style={{
                                    border: `1.5px solid ${enderecoId === e.id ? "#F97316" : "#E8D5C4"}`,
                                }}
                            >
                                <input
                                    type="radio"
                                    name="endereco"
                                    checked={enderecoId === e.id}
                                    onChange={() => setEnderecoId(e.id)}
                                />
                                <span className="text-sm text-[#1A0A00]">
                                    {e.street}, {e.number} — {e.neighborhood}
                                </span>
                            </label>
                        ))}

                        {!mostrandoNovoEndereco ? (
                            <button
                                onClick={() => setMostrandoNovoEndereco(true)}
                                className="flex items-center gap-2 text-sm font-bold text-[#F97316] mt-1"
                            >
                                <Plus size={16} /> Adicionar novo endereço
                            </button>
                        ) : (
                            <EnderecoForm
                                title="Novo endereço"
                                submitLabel="Salvar endereço"
                                submitting={salvandoEndereco}
                                errorMessage={erroEndereco}
                                onSubmit={handleAdicionarEndereco}
                                onCancel={() => {
                                    setMostrandoNovoEndereco(false);
                                    setErroEndereco(null);
                                }}
                            />
                        )}
                    </div>
                )}
            </div>

            {/* Pagamento — seção expansível */}
            <div
                className="rounded-2xl overflow-hidden"
                style={{ border: "1.5px solid #E8D5C4", background: "#fff" }}
            >
                <button
                    onClick={() => toggleSecao("pagamento")}
                    className="w-full flex items-center justify-between p-5"
                >
                    <div className="flex items-center gap-3">
                        <CreditCard
                            size={16}
                            className="text-[#6B5B4E] shrink-0"
                        />
                        <div className="text-left">
                            <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide mb-1">
                                Pagamento
                            </p>
                            <p className="font-semibold text-[#1A0A00] text-sm">
                                {formaPagamento
                                    ? PAGAMENTO_LABEL[formaPagamento]
                                    : "Selecionar forma de pagamento"}
                            </p>
                        </div>
                    </div>
                    <ChevronDown
                        size={18}
                        className={`text-[#6B5B4E] transition-transform ${secaoAberta === "pagamento" ? "rotate-180" : ""}`}
                    />
                </button>

                {secaoAberta === "pagamento" && (
                    <div className="px-5 pb-5 flex flex-col gap-2">
                        <p className="text-xs text-[#B0967E] mb-1">
                            Pagamento realizado direto com o entregador.
                        </p>

                        {(["PIX", "CARTAO_CREDITO", "DINHEIRO"] as const).map(
                            (opcao) => (
                                <label
                                    key={opcao}
                                    className="flex items-center gap-3 p-3 rounded-xl cursor-pointer"
                                    style={{
                                        border: `1.5px solid ${(opcao === "CARTAO_CREDITO" ? formaPagamento === "CARTAO_CREDITO" || formaPagamento === "CARTAO_DEBITO" : formaPagamento === opcao) ? "#F97316" : "#E8D5C4"}`,
                                    }}
                                >
                                    <input
                                        type="radio"
                                        name="pagamento"
                                        checked={
                                            opcao === "CARTAO_CREDITO"
                                                ? formaPagamento ===
                                                        "CARTAO_CREDITO" ||
                                                    formaPagamento ===
                                                        "CARTAO_DEBITO"
                                                : formaPagamento === opcao
                                        }
                                        onChange={() =>
                                            setFormaPagamento(opcao)
                                        }
                                    />
                                    <span className="text-sm text-[#1A0A00]">
                                        {opcao === "CARTAO_CREDITO"
                                            ? "Cartão"
                                            : PAGAMENTO_LABEL[opcao]}
                                    </span>
                                </label>
                            ),
                        )}

                        {(formaPagamento === "CARTAO_CREDITO" ||
                            formaPagamento === "CARTAO_DEBITO") && (
                            <div className="flex gap-2 ml-8">
                                <button
                                    onClick={() =>
                                        setFormaPagamento("CARTAO_CREDITO")
                                    }
                                    className="px-3 py-1.5 rounded-lg text-xs font-bold"
                                    style={{
                                        background:
                                            formaPagamento === "CARTAO_CREDITO"
                                                ? "#1A0A00"
                                                : "#F5EDE3",
                                        color:
                                            formaPagamento === "CARTAO_CREDITO"
                                                ? "#fff"
                                                : "#6B5B4E",
                                    }}
                                >
                                    Crédito
                                </button>
                                <button
                                    onClick={() =>
                                        setFormaPagamento("CARTAO_DEBITO")
                                    }
                                    className="px-3 py-1.5 rounded-lg text-xs font-bold"
                                    style={{
                                        background:
                                            formaPagamento === "CARTAO_DEBITO"
                                                ? "#1A0A00"
                                                : "#F5EDE3",
                                        color:
                                            formaPagamento === "CARTAO_DEBITO"
                                                ? "#fff"
                                                : "#6B5B4E",
                                    }}
                                >
                                    Débito
                                </button>
                            </div>
                        )}

                        {formaPagamento === "DINHEIRO" && (
                            <div
                                className="mt-2 p-3 rounded-xl"
                                style={{
                                    background: "#FFF8EF",
                                    border: "1.5px solid #E8D5C4",
                                }}
                            >
                                <p className="text-xs font-semibold text-[#6B5B4E] mb-2">
                                    Vou pagar com quanto?
                                </p>
                                <input
                                    type="text"
                                    inputMode="decimal"
                                    value={valorPagoDinheiro}
                                    onChange={(e) =>
                                        setValorPagoDinheiro(e.target.value)
                                    }
                                    placeholder={fmtMoney(total)}
                                    className="w-full px-3 py-2 rounded-lg text-sm mb-2"
                                    style={{ border: "1.5px solid #E8D5C4" }}
                                />
                                <div className="flex gap-2 mb-2">
                                    {trocoSugestoes.map((v) => (
                                        <button
                                            key={v}
                                            onClick={() =>
                                                setValorPagoDinheiro(String(v))
                                            }
                                            className="px-2.5 py-1 rounded-lg text-xs font-bold"
                                            style={{
                                                background: "#F5EDE3",
                                                color: "#6B5B4E",
                                            }}
                                        >
                                            {fmtMoney(v)}
                                        </button>
                                    ))}
                                </div>
                                {valorPagoNum > 0 && (
                                    <p className="text-sm text-[#6B5B4E]">
                                        {troco > 0 ? (
                                            <>
                                                Troco:{" "}
                                                <strong className="text-[#1A0A00]">
                                                    {fmtMoney(troco)}
                                                </strong>
                                            </>
                                        ) : (
                                            "Valor exato — sem troco"
                                        )}
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Totais + confirmar */}
            <div
                className="fixed bottom-0 left-0 right-0 z-30 px-4 py-4"
                style={{
                    background: "rgba(255,248,239,0.97)",
                    backdropFilter: "blur(12px)",
                    borderTop: "1.5px solid #E8D5C4",
                }}
            >
                <div className="max-w-lg mx-auto">
                    <div className="flex justify-between font-bold text-[#1A0A00] text-lg mb-3">
                        <span>Total</span>
                        <span style={{ color: "#F97316" }}>
                            {fmtMoney(total)}
                        </span>
                    </div>
                    {erro && (
                        <p className="text-sm text-red-600 mb-2">{erro}</p>
                    )}
                    <button
                        onClick={handleConfirmar}
                        disabled={!podeConfirmar || confirmando}
                        className="w-full py-3.5 rounded-2xl font-bold text-base disabled:opacity-40 disabled:cursor-not-allowed"
                        style={{
                            background:
                                "linear-gradient(135deg,#16A34A,#15803D)",
                            color: "#fff",
                        }}
                    >
                        {confirmando ? "Confirmando..." : "Confirmar pedido"}
                    </button>
                </div>
            </div>
        </div>
    );
}
