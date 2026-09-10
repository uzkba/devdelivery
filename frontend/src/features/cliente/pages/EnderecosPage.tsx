import { useState } from "react";
import {
    MapPin,
    Plus,
    Check,
    Pencil,
    Trash2,
    Loader2,
    RefreshCw,
} from "lucide-react";
import { useEnderecos } from "../hooks/useEnderecos";
import EnderecoForm from "../components/EnderecoForm";
import type { Endereco, EnderecoInput } from "../services/enderecoService";

export default function EnderecosPage() {
    const {
        enderecos,
        loading,
        error,
        recarregar,
        adicionar,
        atualizar,
        remover,
        definirPadrao,
    } = useEnderecos();
    const [showNew, setShowNew] = useState(false);
    const [editing, setEditing] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    const [feedback, setFeedback] = useState<string | null>(null);
    const [busyId, setBusyId] = useState<string | null>(null);

    function showFeedback(msg: string) {
        setFeedback(msg);
        setTimeout(() => setFeedback(null), 3000);
    }

    async function handleCreate(payload: EnderecoInput) {
        setSubmitting(true);
        setFormError(null);
        try {
            await adicionar(payload);
            setShowNew(false);
            showFeedback("Endereço adicionado com sucesso!");
        } catch {
            setFormError(
                "Não foi possível salvar o endereço. Tente novamente.",
            );
        } finally {
            setSubmitting(false);
        }
    }

    async function handleUpdate(id: string, payload: EnderecoInput) {
        setSubmitting(true);
        setFormError(null);
        try {
            await atualizar(id, payload);
            setEditing(null);
            showFeedback("Endereço atualizado com sucesso!");
        } catch {
            setFormError(
                "Não foi possível salvar as alterações. Tente novamente.",
            );
        } finally {
            setSubmitting(false);
        }
    }

    async function handleRemove(id: string) {
        setBusyId(id);
        try {
            await remover(id);
            showFeedback("Endereço removido.");
        } catch {
            showFeedback("Não foi possível remover o endereço.");
        } finally {
            setBusyId(null);
        }
    }

    async function handleSetDefault(id: string) {
        setBusyId(id);
        try {
            await definirPadrao(id);
            showFeedback("Endereço definido como padrão.");
        } catch {
            showFeedback("Não foi possível definir o endereço como padrão.");
        } finally {
            setBusyId(null);
        }
    }

    function toEnderecoInput(a: Endereco): EnderecoInput {
        const {
            street,
            number,
            neighborhood,
            complement,
            reference_point,
            latitude,
            longitude,
        } = a;
        return {
            street,
            number,
            neighborhood,
            complement: complement ?? "",
            reference_point: reference_point ?? "",
            latitude,
            longitude,
        };
    }

    return (
        <div className="px-4 pt-5 pb-12 flex flex-col gap-4">
            {feedback && (
                <div
                    className="rounded-xl px-4 py-3 text-sm font-semibold"
                    style={{ background: "#DCFCE7", color: "#166534" }}
                >
                    {feedback}
                </div>
            )}

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

            {!loading && !error && enderecos.length === 0 && !showNew && (
                <div
                    className="rounded-2xl p-8 text-center flex flex-col items-center gap-4"
                    style={{
                        border: "1.5px solid #E8D5C4",
                        background: "#fff",
                    }}
                >
                    <MapPin size={32} color="#D1C5BB" />
                    <p className="font-semibold text-[#1A0A00]">
                        Nenhum endereço cadastrado
                    </p>
                    <button
                        onClick={() => setShowNew(true)}
                        className="inline-flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-sm text-white"
                        style={{
                            background: "#F97316",
                            fontFamily: "Fraunces, serif",
                        }}
                    >
                        <Plus size={16} /> Adicionar endereço
                    </button>
                </div>
            )}

            {!loading &&
                !error &&
                enderecos.map((addr) =>
                    editing === addr.id ? (
                        <EnderecoForm
                            key={addr.id}
                            title="Editar endereço"
                            submitLabel="Salvar"
                            submitting={submitting}
                            errorMessage={formError}
                            initialValue={toEnderecoInput(addr)}
                            onSubmit={(payload) =>
                                handleUpdate(addr.id, payload)
                            }
                            onCancel={() => {
                                setEditing(null);
                                setFormError(null);
                            }}
                        />
                    ) : (
                        <div
                            key={addr.id}
                            className="rounded-2xl p-4"
                            style={{
                                border: addr.primary_address
                                    ? "2px solid #F97316"
                                    : "1.5px solid #E8D5C4",
                                background: "#fff",
                                boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                            }}
                        >
                            <div className="flex items-start gap-3">
                                <div
                                    className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
                                    style={{
                                        background: addr.primary_address
                                            ? "#FFF1E0"
                                            : "#F5EDE3",
                                    }}
                                >
                                    <MapPin
                                        size={15}
                                        color={
                                            addr.primary_address
                                                ? "#F97316"
                                                : "#6B5B4E"
                                        }
                                    />
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
                                                    background: "#FFF1E0",
                                                    color: "#EA6C0A",
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
                            </div>

                            <div
                                className="flex flex-wrap items-center gap-2 mt-4 pt-3 border-t"
                                style={{ borderColor: "#F5EDE3" }}
                            >
                                {!addr.primary_address && (
                                    <button
                                        onClick={() =>
                                            handleSetDefault(addr.id)
                                        }
                                        disabled={busyId === addr.id}
                                        className="flex items-center gap-1.5 text-xs font-bold text-[#16A34A] hover:opacity-80 transition-opacity disabled:opacity-40"
                                    >
                                        {busyId === addr.id ? (
                                            <Loader2
                                                size={13}
                                                className="animate-spin"
                                            />
                                        ) : (
                                            <Check size={13} />
                                        )}{" "}
                                        Definir como padrão
                                    </button>
                                )}
                                <button
                                    onClick={() => {
                                        setEditing(addr.id);
                                        setShowNew(false);
                                        setFormError(null);
                                    }}
                                    className="flex items-center gap-1.5 text-xs font-bold text-[#6B5B4E] hover:opacity-80 ml-auto transition-opacity"
                                >
                                    <Pencil size={13} /> Editar
                                </button>
                                <button
                                    onClick={() => handleRemove(addr.id)}
                                    disabled={busyId === addr.id}
                                    className="flex items-center gap-1.5 text-xs font-bold text-red-500 hover:opacity-80 transition-opacity disabled:opacity-40"
                                >
                                    {busyId === addr.id ? (
                                        <Loader2
                                            size={13}
                                            className="animate-spin"
                                        />
                                    ) : (
                                        <Trash2 size={13} />
                                    )}{" "}
                                    Excluir
                                </button>
                            </div>
                        </div>
                    ),
                )}

            {!loading && !error && showNew && (
                <EnderecoForm
                    title="Novo endereço"
                    submitLabel="Adicionar"
                    submitting={submitting}
                    errorMessage={formError}
                    onSubmit={handleCreate}
                    onCancel={() => {
                        setShowNew(false);
                        setFormError(null);
                    }}
                />
            )}

            {!loading &&
                !error &&
                !showNew &&
                !editing &&
                enderecos.length > 0 && (
                    <button
                        onClick={() => setShowNew(true)}
                        className="flex items-center gap-2 text-sm font-bold text-[#F97316] py-2"
                    >
                        <Plus size={16} /> Adicionar endereço
                    </button>
                )}
        </div>
    );
}
