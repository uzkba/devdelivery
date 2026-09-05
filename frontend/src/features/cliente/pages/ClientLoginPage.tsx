import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { useClienteAuth } from "../../../shared/auth/ClienteAuthContext";
import { loginCliente } from "../services/clienteAuthService";

export default function ClientLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useClienteAuth();

  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const from = (location.state as { from?: string })?.from ?? "/";

  function formatPhone(raw: string) {
    const digits = raw.replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 2) return digits;
    if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
  }

  const phoneDigits = phone.replace(/\D/g, "");
  const canSubmit = phoneDigits.length >= 10 && password.length > 0 && !loading;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;

    setError(null);
    setLoading(true);

    try {
      const { access_token } = await loginCliente({
        phone: phoneDigits,
        password,
      });
      login(access_token, phone);
      navigate(from, { replace: true });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        if (err.response?.status === 401) {
          setError("Telefone ou senha inválidos.");
        } else if (err.response?.status === 403) {
          setError("Cliente inativo. Entre em contato com o restaurante.");
        } else {
          setError("Não foi possível conectar. Tente novamente.");
        }
      } else {
        setError("Erro inesperado. Tente novamente.");
      }
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
            Entrar
          </h1>
          <p className="text-sm text-[#6B5B4E] mt-2">
            Digite seu telefone e senha para continuar.
          </p>
        </div>

        {error && (
          <div
            className="mb-4 px-4 py-3 rounded-xl text-sm font-medium text-center"
            style={{
              background: "#FEF2F2",
              border: "1px solid #FCA5A5",
              color: "#B91C1C",
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="phone"
              className="block text-sm font-bold text-[#3D1A00] mb-2"
            >
              Telefone
            </label>
            <input
              id="phone"
              type="tel"
              inputMode="numeric"
              autoComplete="tel"
              value={phone}
              autoFocus
              onChange={(e) => setPhone(formatPhone(e.target.value))}
              placeholder="(84) 99999-9999"
              className="w-full px-4 py-4 rounded-xl text-[#1A0A00] text-lg font-bold placeholder:text-[#C4A882] placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
              style={{ border: "2px solid #E8D5C4", background: "#FFF8EF" }}
            />
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
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Sua senha"
                className="w-full px-4 py-4 pr-16 rounded-xl text-[#1A0A00] text-lg font-bold placeholder:text-[#C4A882] placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
                style={{ border: "2px solid #E8D5C4", background: "#FFF8EF" }}
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
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full py-4 rounded-2xl font-bold text-base transition-all active:scale-[0.98] mt-1"
            style={{
              fontFamily: "Fraunces, serif",
              background: canSubmit
                ? "linear-gradient(135deg,#F97316,#EA580C)"
                : "#E8D5C4",
              color: canSubmit ? "#fff" : "#B0967E",
              boxShadow: canSubmit ? "0 4px 16px rgba(249,115,22,0.3)" : "none",
            }}
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
