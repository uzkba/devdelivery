import { useEffect, useRef, useState } from "react";
import { Loader2, LocateFixed } from "lucide-react";

import {
    buscarEnderecoPorCep,
    formatarCep,
} from "@/shared/services/viaCepService";

import type { EnderecoInput } from "../services/enderecoService";

import { buscarCoordenadasPorEndereco } from "@/features/cliente/services/geocodingService";

interface FormState extends EnderecoInput {
    cep: string;
}

const CIDADE_ENTREGA = "Malta";
const ESTADO_ENTREGA = "PB";

const PRECISAO_MAXIMA_METROS = 100;

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
    const [localizacaoCapturada, setLocalizacaoCapturada] = useState(
        initialValue?.latitude != null && initialValue?.longitude != null,
    );

    const [erroLocalizacao, setErroLocalizacao] = useState<string | null>(null);

    const [geocodificando, setGeocodificando] = useState(false);
    const [erroGeocodificacao, setErroGeocodificacao] = useState<string | null>(
        null,
    );

    const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(
        undefined,
    );

    function f<K extends keyof FormState>(key: K, val: FormState[K]) {
        setForm((p) => ({
            ...p,
            [key]: val,
        }));
    }

    /**
     * Limpa as coordenadas atuais.
     *
     * Isso é importante porque, se o usuário alterar o endereço
     * depois de capturar uma localização, as coordenadas antigas
     * podem deixar de representar o endereço informado.
     */
    function limparLocalizacao() {
        setForm((p) => ({
            ...p,
            latitude: null,
            longitude: null,
        }));

        setLocalizacaoCapturada(false);
    }

    function handleCepChange(raw: string) {
        setCepNotFound(false);
        setErroGeocodificacao(null);

        // O CEP pode alterar rua/bairro automaticamente.
        // Portanto, as coordenadas antigas deixam de ser confiáveis.
        limparLocalizacao();

        f("cep", formatarCep(raw));
    }

    useEffect(() => {
        const digits = form.cep.replace(/\D/g, "");

        if (digits.length !== 8) {
            return;
        }

        clearTimeout(debounceRef.current);

        debounceRef.current = setTimeout(async () => {
            setCepLoading(true);

            const result = await buscarEnderecoPorCep(digits);

            setCepLoading(false);

            if (!result || (!result.logradouro && !result.bairro)) {
                setCepNotFound(true);
                return;
            }

            setForm((p) => ({
                ...p,
                street: result.logradouro || p.street,
                neighborhood: result.bairro || p.neighborhood,

                // O ViaCEP alterou os dados do endereço.
                // As coordenadas serão obtidas novamente no submit.
                latitude: null,
                longitude: null,
            }));

            setLocalizacaoCapturada(false);
        }, 500);

        return () => clearTimeout(debounceRef.current);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [form.cep]);

    function handleAddressFieldChange(
        key:
            | "street"
            | "number"
            | "complement"
            | "neighborhood"
            | "reference_point",
        value: string,
    ) {
        f(key, value);

        // Complemento e ponto de referência não alteram
        // a localização geográfica do endereço.
        if (key !== "complement" && key !== "reference_point") {
            limparLocalizacao();
            setErroGeocodificacao(null);
        }
    }

    function capturarLocalizacao() {
        if (!navigator.geolocation) {
            setErroLocalizacao("Seu navegador não suporta geolocalização.");
            return;
        }

        // Nunca reaproveitar coordenadas antigas.
        limparLocalizacao();

        setErroLocalizacao(null);
        setLocLoading(true);

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const { latitude, longitude, accuracy } = pos.coords;

                if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
                    setLocLoading(false);
                    setErroLocalizacao(
                        "A localização obtida não é válida. Tente novamente.",
                    );
                    return;
                }

                if (
                    Number.isFinite(accuracy) &&
                    accuracy > PRECISAO_MAXIMA_METROS
                ) {
                    setLocLoading(false);
                    setErroLocalizacao(
                        `A localização obtida está pouco precisa (${Math.round(
                            accuracy,
                        )} m). Tente novamente em um local com melhor sinal.`,
                    );
                    return;
                }

                setForm((p) => ({
                    ...p,
                    latitude,
                    longitude,
                }));

                setLocalizacaoCapturada(true);
                setLocLoading(false);
            },
            (erro) => {
                setLocLoading(false);
                setLocalizacaoCapturada(false);

                // Garante que uma localização antiga nunca seja reutilizada.
                limparLocalizacao();

                if (erro.code === erro.PERMISSION_DENIED) {
                    setErroLocalizacao(
                        "Permissão de localização negada. Você pode preencher o endereço manualmente.",
                    );
                } else if (erro.code === erro.TIMEOUT) {
                    setErroLocalizacao(
                        "Não conseguimos obter sua localização a tempo. Tente novamente.",
                    );
                } else if (erro.code === erro.POSITION_UNAVAILABLE) {
                    setErroLocalizacao(
                        "Não conseguimos determinar sua localização. Você pode preencher o endereço manualmente.",
                    );
                } else {
                    setErroLocalizacao(
                        "Não conseguimos obter sua localização agora. Você pode preencher o endereço manualmente.",
                    );
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0,
            },
        );
    }

    const canSave = !!form.street && !!form.number && !!form.neighborhood;

    async function handleSubmit() {
        const { cep, ...payload } = form;

        setErroGeocodificacao(null);

        /*
         * Caso 1:
         * O usuário capturou a localização atual.
         *
         * Nesse caso, usamos diretamente as coordenadas
         * fornecidas pelo navegador.
         */
        if (payload.latitude != null && payload.longitude != null) {
            onSubmit(payload);
            return;
        }

        /*
         * Caso 2:
         * O usuário não capturou a localização.
         *
         * Então precisamos transformar o endereço digitado
         * em latitude/longitude através do geocoding.
         */
        setGeocodificando(true);

        const coordenadas = await buscarCoordenadasPorEndereco({
            street: `${payload.street}, ${payload.number}`,
            city: CIDADE_ENTREGA,
            state: ESTADO_ENTREGA,
            neighborhood: payload.neighborhood,
            postalCode: cep,
        });

        setGeocodificando(false);

        if (!coordenadas) {
            setErroGeocodificacao(
                "Não conseguimos localizar esse endereço. Confira rua, número, bairro e CEP.",
            );
            return;
        }

        /*
         * Endereço manual localizado com sucesso.
         */
        onSubmit({
            ...payload,
            latitude: coordenadas.latitude,
            longitude: coordenadas.longitude,
        });
    }

    return (
        <div
            className="rounded-2xl p-5 flex flex-col gap-3.5"
            style={{
                border: "1.5px solid #E8D5C4",
                background: "#fff",
            }}
        >
            <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide">
                {title}
            </p>

            {(errorMessage || erroGeocodificacao) && (
                <div
                    className="rounded-xl px-3 py-2 text-sm font-medium"
                    style={{
                        background: "#FEF2F2",
                        color: "#B91C1C",
                    }}
                >
                    {erroGeocodificacao ?? errorMessage}
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
                        Não encontramos rua e bairro cadastrados pra esse CEP —
                        preencha manualmente.
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
                        onChange={(e) =>
                            handleAddressFieldChange(key, e.target.value)
                        }
                        placeholder={placeholder}
                        className="w-full px-4 py-3 rounded-xl text-[#1A0A00] font-medium placeholder:text-[#C4A882] focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
                        style={{
                            border: "1.5px solid #E8D5C4",
                            background: "#FFF8EF",
                        }}
                    />
                </div>
            ))}

            <div className="flex flex-col gap-1">
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

                    {locLoading
                        ? "Obtendo localização..."
                        : localizacaoCapturada
                          ? "Localização capturada ✓"
                          : "Usar minha localização atual"}
                </button>

                {erroLocalizacao && (
                    <p className="text-xs text-red-500">{erroLocalizacao}</p>
                )}

                {localizacaoCapturada && !erroLocalizacao && (
                    <p className="text-xs text-green-600">
                        Usaremos sua localização atual para calcular a entrega.
                    </p>
                )}

                {!localizacaoCapturada && !erroLocalizacao && (
                    <p className="text-xs text-[#B0967E]">
                        Se preferir, basta preencher o endereço. Nós
                        localizaremos automaticamente.
                    </p>
                )}
            </div>

            <div className="flex gap-3 pt-1">
                {onCancel && (
                    <button
                        onClick={onCancel}
                        disabled={submitting || geocodificando}
                        className="flex-1 py-3 rounded-xl border font-semibold text-sm text-[#6B5B4E] transition-all disabled:opacity-50"
                        style={{
                            borderColor: "#E8D5C4",
                        }}
                    >
                        Cancelar
                    </button>
                )}

                <button
                    onClick={handleSubmit}
                    disabled={!canSave || submitting || geocodificando}
                    className="flex-1 py-3 rounded-xl font-bold text-sm text-white transition-all active:scale-[0.97] flex items-center justify-center gap-2"
                    style={{
                        background:
                            canSave && !submitting ? "#F97316" : "#E8D5C4",
                        color: canSave && !submitting ? "#fff" : "#B0967E",
                    }}
                >
                    {(submitting || geocodificando) && (
                        <Loader2 size={15} className="animate-spin" />
                    )}

                    {geocodificando
                        ? "Localizando endereço..."
                        : submitting
                            ? "Salvando..."
                            : submitLabel}
                </button>
            </div>
        </div>
    );
}
