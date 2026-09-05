// features/auth/pages/StaffLoginPage.tsx
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../../../shared/auth/StaffAuthContext";
import { loginAdmin } from "../services/authService";

export default function StaffLoginPage() {
    const [login, setLogin] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const { login: setSession } = useAuth();
    const navigate = useNavigate();

    async function handleSubmit(event: FormEvent) {
        event.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            const { access_token } = await loginAdmin({ login, password });
            setSession(access_token);
            navigate("/admin", { replace: true });
        } catch (err) {
            if (axios.isAxiosError(err)) {
                if (err.response?.status === 401) {
                    setError("Login ou senha inválidos.");
                } else if (err.response?.status === 403) {
                    setError("Usuário inativo. Contate o administrador.");
                } else {
                    setError("Não foi possível conectar. Tente novamente.");
                }
            } else {
                setError("Erro inesperado. Tente novamente.");
            }
        } finally {
            setIsLoading(false);
        }
    }

    const canSubmit = login.trim().length > 0 && password.length > 0 && !isLoading;

    return (
        <div
            className="min-h-screen flex flex-col items-center justify-center px-5 py-10"
            style={{ background: "#FFF8EF" }}
        >
            <div className="w-full max-w-sm">
                {/* Brand */}
                <div className="mb-8 sm:mb-10">
                    <p className="text-xs font-bold text-[#B0967E] uppercase tracking-widest mb-2">
                        DevDelivery · Área do restaurante
                    </p>
                    <h1
                        className="text-2xl sm:text-3xl font-bold text-[#1A0A00]"
                        style={{ fontFamily: "Fraunces, serif" }}
                    >
                        Marmitaria Sabor & Arte
                    </h1>
                    <p className="text-[#6B5B4E] text-sm mt-2">
                        Entre com seu usuário e senha para continuar.
                    </p>
                </div>

                {/* Erro */}
                {error && (
                    <div
                        className="mb-5 px-4 py-3 rounded-xl text-sm font-medium"
                        style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", color: "#B91C1C" }}
                    >
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="flex flex-col gap-4 mb-6">
                    <div>
                        <label
                            htmlFor="login"
                            className="block text-xs font-bold text-[#6B5B4E] uppercase tracking-wide mb-1.5"
                        >
                            Usuário
                        </label>
                        <input
                            id="login"
                            type="text"
                            inputMode="email"
                            autoComplete="username"
                            value={login}
                            onChange={(e) => setLogin(e.target.value)}
                            required
                            className="w-full px-5 py-4 rounded-2xl text-base text-[#1A0A00] bg-white transition-all outline-none"
                            style={{ border: "1.5px solid #E8D5C4" }}
                            onFocus={(e) => (e.currentTarget.style.borderColor = "#F97316")}
                            onBlur={(e) => (e.currentTarget.style.borderColor = "#E8D5C4")}
                        />
                    </div>

                    <div>
                        <label
                            htmlFor="password"
                            className="block text-xs font-bold text-[#6B5B4E] uppercase tracking-wide mb-1.5"
                        >
                            Senha
                        </label>
                        <div className="relative">
                            <input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                autoComplete="current-password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                className="w-full px-5 py-4 pr-12 rounded-2xl text-base text-[#1A0A00] bg-white transition-all outline-none"
                                style={{ border: "1.5px solid #E8D5C4" }}
                                onFocus={(e) => (e.currentTarget.style.borderColor = "#F97316")}
                                onBlur={(e) => (e.currentTarget.style.borderColor = "#E8D5C4")}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword((v) => !v)}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-[#B0967E] text-sm font-semibold"
                                tabIndex={-1}
                            >
                                {showPassword ? "Ocultar" : "Ver"}
                            </button>
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={!canSubmit}
                        className="w-full py-4 rounded-2xl font-bold text-lg transition-all active:scale-[0.98] mt-2"
                        style={{
                            fontFamily: "Fraunces, serif",
                            background: canSubmit
                                ? "linear-gradient(135deg, #F97316 0%, #EA580C 100%)"
                                : "#E8D5C4",
                            color: canSubmit ? "#fff" : "#B0967E",
                            boxShadow: canSubmit ? "0 6px 20px rgba(249,115,22,0.3)" : "none",
                            cursor: canSubmit ? "pointer" : "not-allowed",
                        }}
                    >
                        {isLoading ? "Entrando..." : "Entrar"}
                    </button>
                </form>

                <div className="text-center">
                    <a
                      href="/"
                      className="text-sm text-[#6B5B4E] hover:text-[#F97316] transition-colors underline"
                    >
                        Ir para a área do cliente
                    </a>
                </div>
            </div>
        </div>
    );
}