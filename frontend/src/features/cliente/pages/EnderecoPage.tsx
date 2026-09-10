import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { MapPin, Plus, Check, Loader2, RefreshCw } from "lucide-react";
import { useEnderecos } from "@/features/cliente/hooks/useEnderecos";
import EnderecoForm from "@/features/cliente/components/EnderecoForm";
import type { EnderecoInput } from "@/features/cliente/services/enderecoService";
import type { CartItem } from "./CardapioPage";

export default function EnderecoPage() {
    const navigate = useNavigate();
    const { state } = useLocation();
    const { cartItems = [] } = (state ?? {}) as { cartItems: CartItem[] };

    const { enderecos, loading, error, recarregar, adicionar, definirPadrao } =
        useEnderecos();
    const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
    const [showForm, setShowForm] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    if (!loading && !selectedId && enderecos.length > 0) {
        setSelectedId(
            enderecos.find((a) => a.primary_address)?.id ?? enderecos[0].id,
        );
    }

    async function handleSaveAddress(payload: EnderecoInput) {
        setSubmitting(true);
        setFormError(null);
        try {
            const novo = await adicionar(payload);
            setSelectedId(novo.id);
            setShowForm(false);
        } catch {
            setFormError(
                "Não foi possível salvar o endereço. Tente novamente.",
            );
        } finally {
            setSubmitting(false);
        }
    }

    async function handleContinue() {
        if (!selectedId) return;
        const addr = enderecos.find((a) => a.id === selectedId);
        if (!addr) return;
        if (!addr.primary_address) {
            try {
                await definirPadrao(addr.id);
            } catch {
                /* não bloqueia o pedido */
            }
        }
        navigate("/pedido/pagamento", { state: { cartItems, address: addr } });
    }

    return (
        <div className="px-4 pt-5 pb-36 flex flex-col gap-4">
            {loading && (
                <div className="flex flex-col items-center justify-center py-16 gap-3 text-[#B0967E]">
                    <Loader2 size={24} className="animate-spin" />
                    <p className="text-sm font-medium">
                        Carregando seus endereços...
                    </p>
                </div>
            )}

            {!loading && error && (
                <div
                    className="rounded-2xl p-6 text-center flex flex-col items-center gap-3"
                    style={{
                        border: "1.5px solid #E8D5C4",
                        background: "#fff",
                    }}
                >
                    <p className="text-sm text-red-500 font-medium">{error}</p>
                    <button
                        onClick={recarregar}
                        className="flex items-center gap-2 text-sm font-bold text-[#F97316]"
                    >
                        <RefreshCw size={14} /> Tentar novamente
                    </button>
                </div>
            )}

            {!loading && !error && enderecos.length === 0 && !showForm && (
                <div
                    className="rounded-2xl p-5 text-center"
                    style={{
                        border: "1.5px solid #E8D5C4",
                        background: "#fff",
                    }}
                >
                    <p className="font-semibold text-[#1A0A00] mb-1">
                        Nenhum endereço cadastrado
                    </p>
                    <p className="text-sm text-[#6B5B4E] mb-4">
                        Adicione um endereço para continuar.
                    </p>
                    <button
                        onClick={() => setShowForm(true)}
                        className="inline-flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-sm"
                        style={{
                            background: "#F97316",
                            color: "#fff",
                            fontFamily: "Fraunces, serif",
                        }}
                    >
                        <Plus size={16} /> Adicionar endereço
                    </button>
                </div>
            )}

            {!loading && !error && enderecos.length > 0 && !showForm && (
                <>
                    <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide">
                        Escolha o endereço de entrega
                    </p>

                    {enderecos.map((addr) => {
                        const isSel = selectedId === addr.id;
                        return (
                            <button
                                key={addr.id}
                                onClick={() => setSelectedId(addr.id)}
                                className="w-full text-left rounded-2xl p-4 flex items-start gap-3 transition-all active:scale-[0.98]"
                                style={{
                                    border: isSel
                                        ? "2px solid #F97316"
                                        : "1.5px solid #E8D5C4",
                                    background: isSel ? "#FFF8EF" : "#fff",
                                    boxShadow: isSel
                                        ? "0 4px 14px rgba(249,115,22,0.12)"
                                        : "0 2px 6px rgba(0,0,0,0.04)",
                                }}
                            >
                                <div
                                    className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 transition-all"
                                    style={{
                                        background: isSel
                                            ? "#F97316"
                                            : "transparent",
                                        border: isSel
                                            ? "none"
                                            : "2px solid #D1C5BB",
                                    }}
                                >
                                    {isSel && (
                                        <Check
                                            size={13}
                                            color="#fff"
                                            strokeWidth={3}
                                        />
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <p className="font-bold text-[#1A0A00] text-sm">
                                            {addr.street}, {addr.number}
                                        </p>
                                        {addr.primary_address && (
                                            <span
                                                className="text-xs font-bold px-2 py-0.5 rounded-full"
                                                style={{
                                                    background: "#DCFCE7",
                                                    color: "#166534",
                                                }}
                                            >
                                                Padrão
                                            </span>
                                        )}
                                    </div>
                                    {addr.complement && (
                                        <p className="text-sm text-[#6B5B4E] mt-0.5">
                                            {addr.complement}
                                        </p>
                                    )}
                                    <p className="text-xs text-[#B0967E] mt-0.5">
                                        {addr.neighborhood}
                                    </p>
                                    {addr.reference_point && (
                                        <p className="text-xs text-[#B0967E] mt-0.5">
                                            Ref.: {addr.reference_point}
                                        </p>
                                    )}
                                </div>
                            </button>
                        );
                    })}

                    <button
                        onClick={() => setShowForm(true)}
                        className="flex items-center gap-2 text-sm font-bold text-[#F97316] py-2"
                    >
                        <Plus size={16} /> Adicionar endereço
                    </button>
                </>
            )}

            {!loading && !error && showForm && (
                <EnderecoForm
                    title="Novo endereço"
                    submitLabel="Salvar endereço"
                    submitting={submitting}
                    errorMessage={formError}
                    onSubmit={handleSaveAddress}
                    onCancel={
                        enderecos.length > 0
                            ? () => {
                                  setShowForm(false);
                                  setFormError(null);
                              }
                            : undefined
                    }
                />
            )}

            {!showForm && !loading && !error && selectedId && (
                <div
                    className="fixed bottom-0 left-0 right-0 z-30 px-4 py-4"
                    style={{
                        background: "rgba(255,248,239,0.97)",
                        backdropFilter: "blur(12px)",
                        borderTop: "1.5px solid #E8D5C4",
                    }}
                >
                    <div className="max-w-lg mx-auto">
                        <div className="flex items-center gap-2 mb-3 text-sm text-[#6B5B4E]">
                            <MapPin
                                size={14}
                                className="shrink-0 text-[#F97316]"
                            />
                            <span className="truncate">
                                {
                                    enderecos.find((a) => a.id === selectedId)
                                        ?.street
                                }
                                ,{" "}
                                {
                                    enderecos.find((a) => a.id === selectedId)
                                        ?.number
                                }
                            </span>
                        </div>
                        <div className="flex gap-3">
                            <button
                                onClick={() => navigate(-1)}
                                className="px-5 py-3.5 rounded-2xl border font-semibold text-[#6B5B4E] text-sm active:scale-95 transition-all"
                                style={{ borderColor: "#E8D5C4" }}
                            >
                                Voltar
                            </button>
                            <button
                                onClick={handleContinue}
                                className="flex-1 py-3.5 rounded-2xl font-bold text-base transition-all active:scale-[0.98]"
                                style={{
                                    fontFamily: "Fraunces, serif",
                                    background:
                                        "linear-gradient(135deg,#F97316,#EA580C)",
                                    color: "#fff",
                                    boxShadow:
                                        "0 4px 16px rgba(249,115,22,0.3)",
                                }}
                            >
                                Continuar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
