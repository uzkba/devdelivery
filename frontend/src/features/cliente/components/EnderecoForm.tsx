import { useEffect, useRef, useState } from "react";
import { Loader2, LocateFixed } from "lucide-react";
import {
    buscarEnderecoPorCep,
    formatarCep,
} from "@/shared/services/viaCepService";
import type { EnderecoInput } from "../services/enderecoService";

interface FormState extends EnderecoInput {
    cep: string; // só usado pra autofill, nunca é enviado ao backend
}

interface EnderecoFormProps {
    initialValue?: EnderecoInput;
    title: string;
    submitLabel: string;
    submitting: boolean;
    errorMessage?: string | null;
    onSubmit: (payload: EnderecoInput) => void;
    onCancel?: () => void;
}

export default function EnderecoForm({
    initialValue,
    title,
    submitLabel,
    submitting,
    errorMessage,
    onSubmit,
    onCancel,
}: EnderecoFormProps) {
    const [form, setForm] = useState<FormState>({
        cep: "",
        street: "",
        number: "",
        complement: "",
        neighborhood: "",
        reference_point: "",
        latitude: null,
        longitude: null,
        ...(initialValue ?? {}),
    });
    const [cepLoading, setCepLoading] = useState(false);
    const [cepNotFound, setCepNotFound] = useState(false);
    const [locLoading, setLocLoading] = useState(false);
    const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

    function f<K extends keyof FormState>(key: K, val: FormState[K]) {
        setForm((p) => ({ ...p, [key]: val }));
    }

    function handleCepChange(raw: string) {
        setCepNotFound(false);
        f("cep", formatarCep(raw));
    }

    useEffect(() => {
        const digits = form.cep.replace(/\D/g, "");
        if (digits.length !== 8) return;

        clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(async () => {
            setCepLoading(true);
            const result = await buscarEnderecoPorCep(digits);
            setCepLoading(false);
            if (!result) {
                setCepNotFound(true);
                return;
            }
            setForm((p) => ({
                ...p,
                street: result.logradouro || p.street,
                neighborhood: result.bairro || p.neighborhood,
            }));
        }, 500);

        return () => clearTimeout(debounceRef.current);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [form.cep]);

    function capturarLocalizacao() {
        if (!navigator.geolocation) return;
        setLocLoading(true);
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                f("latitude", pos.coords.latitude);
                f("longitude", pos.coords.longitude);
                setLocLoading(false);
            },
            () => setLocLoading(false),
            { enableHighAccuracy: true, timeout: 8000 },
        );
    }

    const canSave = !!form.street && !!form.number && !!form.neighborhood;

    function handleSubmit() {
        const { cep, ...payload } = form;
        onSubmit(payload);
    }

    return (
        <div
            className="rounded-2xl p-5 flex flex-col gap-3.5"
            style={{ border: "1.5px solid #E8D5C4", background: "#fff" }}
        >
            <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide">
                {title}
            </p>

            {errorMessage && (
                <div
                    className="rounded-xl px-3 py-2 text-sm font-medium"
                    style={{ background: "#FEF2F2", color: "#B91C1C" }}
                >
                    {errorMessage}
                </div>
            )}

            <div>
                <label
                    htmlFor="cep"
                    className="block text-sm font-bold text-[#3D1A00] mb-1.5"
                >
                    CEP
                </label>
                <div className="relative">
                    <input
                        id="cep"
                        type="text"
                        value={form.cep}
                        onChange={(e) => handleCepChange(e.target.value)}
                        placeholder="00000-000"
                        inputMode="numeric"
                        maxLength={9}
                        className="w-full px-4 py-3 rounded-xl text-[#1A0A00] font-medium placeholder:text-[#C4A882] focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
                        style={{
                            border: "1.5px solid #E8D5C4",
                            background: "#FFF8EF",
                        }}
                    />
                    {cepLoading && (
                        <Loader2
                            size={16}
                            className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-[#F97316]"
                        />
                    )}
                </div>
                {cepNotFound && (
                    <p className="text-xs text-red-500 mt-1">
                        CEP não encontrado — preencha o endereço manualmente.
                    </p>
                )}
                <p className="text-xs text-[#B0967E] mt-1">
                    Usado só pra preencher rua e bairro automaticamente.
                </p>
            </div>

            {(
                [
                    ["street", "Rua", "Nome da rua"],
                    ["number", "Número", "123"],
                    ["complement", "Complemento", "Apto, bloco... (opcional)"],
                    ["neighborhood", "Bairro", "Nome do bairro"],
                    [
                        "reference_point",
                        "Ponto de referência",
                        "Próximo a... (opcional)",
                    ],
                ] as const
            ).map(([key, label, placeholder]) => (
                <div key={key}>
                    <label
                        htmlFor={key}
                        className="block text-sm font-bold text-[#3D1A00] mb-1.5"
                    >
                        {label}
                    </label>
                    <input
                        id={key}
                        type="text"
                        value={form[key] ?? ""}
                        onChange={(e) => f(key, e.target.value)}
                        placeholder={placeholder}
                        className="w-full px-4 py-3 rounded-xl text-[#1A0A00] font-medium placeholder:text-[#C4A882] focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
                        style={{
                            border: "1.5px solid #E8D5C4",
                            background: "#FFF8EF",
                        }}
                    />
                </div>
            ))}

            <button
                onClick={capturarLocalizacao}
                disabled={locLoading}
                type="button"
                className="flex items-center gap-2 text-xs font-bold text-[#F97316] self-start disabled:opacity-50"
            >
                {locLoading ? (
                    <Loader2 size={13} className="animate-spin" />
                ) : (
                    <LocateFixed size={13} />
                )}
                {form.latitude
                    ? "Localização capturada ✓"
                    : "Usar minha localização atual"}
            </button>

            <div className="flex gap-3 pt-1">
                {onCancel && (
                    <button
                        onClick={onCancel}
                        disabled={submitting}
                        className="flex-1 py-3 rounded-xl border font-semibold text-sm text-[#6B5B4E] transition-all disabled:opacity-50"
                        style={{ borderColor: "#E8D5C4" }}
                    >
                        Cancelar
                    </button>
                )}
                <button
                    onClick={handleSubmit}
                    disabled={!canSave || submitting}
                    className="flex-1 py-3 rounded-xl font-bold text-sm text-white transition-all active:scale-[0.97] flex items-center justify-center gap-2"
                    style={{
                        background:
                            canSave && !submitting ? "#F97316" : "#E8D5C4",
                        color: canSave && !submitting ? "#fff" : "#B0967E",
                    }}
                >
                    {submitting && (
                        <Loader2 size={15} className="animate-spin" />
                    )}
                    {submitting ? "Salvando..." : submitLabel}
                </button>
            </div>
        </div>
    );
}
