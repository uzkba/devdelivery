import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useClienteAuth } from "../../../shared/auth/ClienteAuthContext";
import { loginCliente, registrarCliente } from "../services/clienteAuthService";

const clienteRegisterSchema = z
    .object({
        name: z.string().trim().min(3, "Informe seu nome completo"),
        phone: z
            .string()
            .refine((value) => value.replace(/\D/g, "").length >= 10, {
                message: "Informe um telefone válido",
            }),
        password: z.string().min(8, "A senha deve ter pelo menos 8 caracteres"),
        confirmPassword: z.string(),
    })
    .refine((data) => data.password === data.confirmPassword, {
        message: "As senhas não coincidem",
        path: ["confirmPassword"],
    });

type ClienteRegisterFormData = z.infer<typeof clienteRegisterSchema>;

function formatPhone(raw: string) {
    const digits = raw.replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 2) return digits;
    if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

export default function ClientRegisterPage() {
    const navigate = useNavigate();
    const { login } = useClienteAuth();

    const [serverError, setServerError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const {
        control,
        register,
        handleSubmit,
        formState: { errors, isValid },
    } = useForm<ClienteRegisterFormData>({
        resolver: zodResolver(clienteRegisterSchema),
        mode: "onChange",
        defaultValues: {
            name: "",
            phone: "",
            password: "",
            confirmPassword: "",
        },
    });

    async function onSubmit(data: ClienteRegisterFormData) {
        setServerError(null);
        setLoading(true);

        const phoneDigits = data.phone.replace(/\D/g, "");

        try {
            await registrarCliente({
                name: data.name.trim(),
                phone: phoneDigits,
                password: data.password,
            });
        } catch (err) {
            setLoading(false);
            if (axios.isAxiosError(err)) {
                if (err.response?.status === 409) {
                    setServerError(
                        "Esse telefone já está cadastrado. Faça login ou use outro número.",
                    );
                } else if (err.response?.status === 422) {
                    setServerError(
                        "Verifique os dados informados e tente novamente.",
                    );
                } else {
                    setServerError(
                        "Não foi possível concluir o cadastro. Tente novamente.",
                    );
                }
            } else {
                setServerError("Erro inesperado. Tente novamente.");
            }
            return;
        }

        try {
            const { access_token } = await loginCliente({
                phone: phoneDigits,
                password: data.password,
            });
            login(access_token, data.phone);
            navigate("/", { replace: true });
        } catch {
            // Cadastro concluído, mas o login automático falhou — manda pro login manual.
            navigate("/cliente/login", { replace: true, state: { from: "/" } });
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-[80vh] px-5 py-8">
            <div className="w-full max-w-sm">
                <div className="text-center mb-8">
                    <p className="text-xs font-bold text-[#B0967E] uppercase tracking-widest mb-1">
                        Marmitaria Sabor & Arte
                    </p>
                    <h1
                        className="text-2xl sm:text-3xl font-bold text-[#1A0A00]"
                        style={{ fontFamily: "Fraunces, serif" }}
                    >
                        Crie sua conta
                    </h1>
                    <p className="text-sm text-[#6B5B4E] mt-2">
                        Cadastre seus dados para fazer pedidos.
                    </p>
                </div>

                {serverError && (
                    <div
                        className="mb-4 px-4 py-3 rounded-xl text-sm font-medium text-center"
                        style={{
                            background: "#FEF2F2",
                            border: "1px solid #FCA5A5",
                            color: "#B91C1C",
                        }}
                    >
                        {serverError}
                    </div>
                )}

                <form
                    onSubmit={handleSubmit(onSubmit)}
                    className="flex flex-col gap-4"
                >
                    <div>
                        <label
                            htmlFor="name"
                            className="block text-sm font-bold text-[#3D1A00] mb-2"
                        >
                            Nome completo
                        </label>
                        <input
                            id="name"
                            type="text"
                            autoComplete="name"
                            autoFocus
                            placeholder="Como podemos chamar você?"
                            {...register("name")}
                            className="w-full px-4 py-4 rounded-xl text-[#1A0A00] text-lg font-bold placeholder:text-[#C4A882] placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
                            style={{
                                border: "2px solid #E8D5C4",
                                background: "#FFF8EF",
                            }}
                        />
                        {errors.name && (
                            <p className="text-xs font-semibold text-[#B91C1C] mt-1.5">
                                {errors.name.message}
                            </p>
                        )}
                    </div>

                    <div>
                        <label
                            htmlFor="phone"
                            className="block text-sm font-bold text-[#3D1A00] mb-2"
                        >
                            Telefone
                        </label>
                        <Controller
                            name="phone"
                            control={control}
                            render={({ field }) => (
                                <input
                                    id="phone"
                                    type="tel"
                                    inputMode="numeric"
                                    autoComplete="tel"
                                    placeholder="(84) 99999-9999"
                                    value={field.value}
                                    onChange={(event) =>
                                        field.onChange(
                                            formatPhone(event.target.value),
                                        )
                                    }
                                    className="w-full px-4 py-4 rounded-xl text-[#1A0A00] text-lg font-bold placeholder:text-[#C4A882] placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
                                    style={{
                                        border: "2px solid #E8D5C4",
                                        background: "#FFF8EF",
                                    }}
                                />
                            )}
                        />
                        {errors.phone && (
                            <p className="text-xs font-semibold text-[#B91C1C] mt-1.5">
                                {errors.phone.message}
                            </p>
                        )}
                    </div>

                    <div>
                        <label
                            htmlFor="password"
                            className="block text-sm font-bold text-[#3D1A00] mb-2"
                        >
                            Senha
                        </label>
                        <div className="relative">
                            <input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                autoComplete="new-password"
                                placeholder="Crie uma senha"
                                {...register("password")}
                                className="w-full px-4 py-4 pr-16 rounded-xl text-[#1A0A00] text-lg font-bold placeholder:text-[#C4A882] placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
                                style={{
                                    border: "2px solid #E8D5C4",
                                    background: "#FFF8EF",
                                }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword((v) => !v)}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-sm font-bold text-[#B0967E]"
                                tabIndex={-1}
                            >
                                {showPassword ? "Ocultar" : "Ver"}
                            </button>
                        </div>
                        {errors.password && (
                            <p className="text-xs font-semibold text-[#B91C1C] mt-1.5">
                                {errors.password.message}
                            </p>
                        )}
                    </div>

                    <div>
                        <label
                            htmlFor="confirmPassword"
                            className="block text-sm font-bold text-[#3D1A00] mb-2"
                        >
                            Confirmar senha
                        </label>
                        <div className="relative">
                            <input
                                id="confirmPassword"
                                type={showConfirmPassword ? "text" : "password"}
                                autoComplete="new-password"
                                placeholder="Repita a senha"
                                {...register("confirmPassword")}
                                className="w-full px-4 py-4 pr-16 rounded-xl text-[#1A0A00] text-lg font-bold placeholder:text-[#C4A882] placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
                                style={{
                                    border: "2px solid #E8D5C4",
                                    background: "#FFF8EF",
                                }}
                            />
                            <button
                                type="button"
                                onClick={() =>
                                    setShowConfirmPassword((v) => !v)
                                }
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-sm font-bold text-[#B0967E]"
                                tabIndex={-1}
                            >
                                {showConfirmPassword ? "Ocultar" : "Ver"}
                            </button>
                        </div>
                        {errors.confirmPassword && (
                            <p className="text-xs font-semibold text-[#B91C1C] mt-1.5">
                                {errors.confirmPassword.message}
                            </p>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={!isValid || loading}
                        className="w-full py-4 rounded-2xl font-bold text-base transition-all active:scale-[0.98] mt-1"
                        style={{
                            fontFamily: "Fraunces, serif",
                            background:
                                isValid && !loading
                                    ? "linear-gradient(135deg,#F97316,#EA580C)"
                                    : "#E8D5C4",
                            color: isValid && !loading ? "#fff" : "#B0967E",
                            boxShadow:
                                isValid && !loading
                                    ? "0 4px 16px rgba(249,115,22,0.3)"
                                    : "none",
                        }}
                    >
                        {loading ? "Criando conta..." : "Criar minha conta"}
                    </button>
                </form>

                <p className="text-center text-xs text-[#B0967E] px-4 mt-6">
                    Já possui uma conta?{" "}
                    <button
                        type="button"
                        onClick={() => navigate("/cliente/login")}
                        className="font-bold text-[#F97316]"
                    >
                        Entrar
                    </button>
                </p>
            </div>
        </div>
    );
}
