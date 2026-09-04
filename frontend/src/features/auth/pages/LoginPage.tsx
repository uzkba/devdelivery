import { useNavigate } from "react-router-dom";

import { useAuth } from "../../../shared/auth/StaffAuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = () => {
    login();
    navigate("/admin", { replace: true });
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#fffaf4] p-6">
      <section className="w-full max-w-md rounded-2xl border border-[#ead8c5] bg-white p-8 shadow-sm">
        <p className="text-xs font-bold tracking-wide text-[#d49b32]">
          DEVDELIVERY
        </p>

        <h1 className="mt-2 font-serif text-3xl font-bold text-[#21170f]">
          Acesso administrativo
        </h1>

        <p className="mt-2 text-sm text-[#806a57]">
          Entre para acessar o painel do restaurante.
        </p>

        <button
          type="button"
          onClick={handleLogin}
          className="mt-6 w-full rounded-xl bg-[#ff7315] px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#e9650d]"
        >
          Entrar
        </button>
      </section>
    </main>
  );
}
